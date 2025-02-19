# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# ./venv/Scripts/Activate.ps1

# 파일 이름을 pytubefix.py로 하면 순환참조 오류 발생

# 필요한 라이브러리 설치:
# pip install pytubefix
# install ffmpeg (https://ffmpeg.org/download.html)
# & copy ./dir
# & rename ffmpeg.exe to _ffmpeg.exe

# 배포를 위한 pyinstaller 명령어:
# pyinstaller --onefile tk_pytubefix_kjh.py
# pyinstaller --onefile --add-binary ".\_ffmpeg.exe;." tk_pytubefix_kjh2.py

# 필요한 라이브러리 임포트
import tkinter as tk
import tkinter.ttk as ttk
from pytubefix import YouTube
import os, re, sys
import subprocess

# 전역 변수 선언
yt = None
title = ""
link = ""
resolution = ""
video_stream = None
audio_stream = None












##########################################################
# 함수 정의
##########################################################
def select_all(event):
    event.widget.select_range(0, 'end')
    event.widget.icursor('end')

def get_approximate_bitrate(bitrates, resolution):
    
    # 입력된 해상도의 숫자 부분만 추출 (예: 1080p -> 1080)
    def extract_resolution_number(res):
        return int(''.join(filter(str.isdigit, res)))
    
    input_res_number = extract_resolution_number(resolution)
    
    # 딕셔너리의 키들을 숫자로 변환
    available_resolutions = {extract_resolution_number(key): key for key in bitrates.keys()}
    
    # 가장 가까운 해상도 찾기
    closest_key = min(available_resolutions, key=lambda x: abs(x - input_res_number))
    
    return bitrates[available_resolutions[closest_key]]

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def sanitize_filename(filename):
    # 유효하지 않은 문자들을 '_으로 치환
    sanitized_filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return sanitized_filename

def update_progress(stream=None, chunk=None, bytes_remaining=None):
    downloaded_size = stream.filesize - bytes_remaining
    progress['value'] = downloaded_size

    if bytes_remaining == 0:
        status_text.set('Download Complete')

    root.update_idletasks()

def check_link_validity():
    global yt, title, link, video_stream, audio_stream

    link = entry_link.get()    
    yt = YouTube(link, on_progress_callback=update_progress)
    title = yt.title
    title_text.set(title)

    # 가능한 모든 비디오 스트림을 가져옴
    video_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc()

    # 오디오 스트림을 가져옴
    audio_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_audio=True).order_by('abr').desc().first()

    # 모든 가능한 해상도를 가져옴
    res = []
    for i in video_stream:
        temp = i.resolution + '_' + i.video_codec
        res += (temp,)
    combo_resolution["value"] = res
    combo_resolution.current(0) # 첫 번째 해상도 선택

def download_link():
    global video_stream, audio_stream, yt
    resolution = combo_resolution.get() # 선택한 해상도 가져옴
    resolution = resolution.split('_')[0] # 해상도만 추출

    # 에러 체크
    if not link:
        status_text.set("Please enter a valid link.")
        return
    if not resolution:
        status_text.set("Please select a resolution.")
        return

    # 파일 이름 생성 및 정리
    audio_filename = sanitize_filename(f'{title}_audio.mp4')
    video_filename = sanitize_filename(f'{title}_video_{resolution}.mp4')
    output_filename = sanitize_filename(f'{title}_{resolution}.mp4')
    mp3_filename = sanitize_filename(f'{title}.mp3')

    # 원하는 해상도의 영상을 선택
    for idx, i in enumerate(video_stream):
        if i.resolution == resolution:
            download_video_stream = video_stream[idx]
            break

#######################################################################

    # 체크 박스의 비디오 & mp3 모두 언체크
    if not mp3_generation_var.get() and not video_generation_var.get():
        status_text.set("Please select either MP3 or Video Generation.")
        return

    # 체크 박스의 비디오 체크 & mp3 언체크
    if os.path.exists(output_filename) and not mp3_generation_var.get():
        status_text.set("video file already exists.")
        return

    # 체크 박스의 비디오 언체크 & mp3 체크
    if not video_generation_var.get() and os.path.exists(mp3_filename):
        status_text.set("mp3 file already exists.")
        return
    
    # 체크 박스의 비디오 체크 & mp3 체크
    if os.path.exists(output_filename) and os.path.exists(mp3_filename):
        status_text.set("file already exists.")
        return

######################################################################

    # 임시 비디오 파일이 이미 존재한다면 스킵
    if os.path.exists(video_filename) or video_generation_var.get() == 0:
        status_text.set("Video file already exists. Skipping download.")
    else:
        # 프로그레스 바 설정
        progress['maximum'] = download_video_stream.filesize
        progress['value'] = 0

        status_text.set("Downloading video...")
        download_video_stream.download(filename=video_filename)

    # 임시 오디오 파일이 이미 존재한다면 스킵
    if os.path.exists(audio_filename):
        status_text.set("Audio file already exists. Skipping download.")
    else:
        # 프로그레스 바 설정
        progress['maximum'] = audio_stream.filesize
        progress['value'] = 0

        status_text.set("Downloading audio...")
        audio_stream.download(filename=audio_filename)
    
    # 비디오와 오디오 병합하기
    # ffmpeg -i video.mp4 -i audio.mp4 output.mp4
    # Intel Quick Sync Video (QSV)
    # ffmpeg -i video.mp4 -i audio.mp3 -c:v h264_qsv output.mp4
    # NVIDIA Cuda
    # ffmpeg -i video.mp4 -i audio.mp4 -c:v h264_nvenc output.mp4
    # AMD AMF
    # ffmpeg -i video.mp4 -i audio.mp4 -c:v h264_amf output.mp4
    # CPU Only
    # ffmpeg -i video.mp4 -i audio.mp3 -c:v libx264 output.mp4

    # 권장 Bitrate:
    # SDR 2160p: 25 Mbps    |   # HDR 2160p: 35 Mbps
    # SDR 1080p: 8 Mbps     |    # HDR 1080p: 12 Mbps
    # SDR 720p: 5 Mbps      |    # HDR 720p: 8 Mbps
    # SDR 480p: 2 Mbps      |    # HDR 480p: 4 Mbps
    # SDR 360p: 1 Mbps      |    # HDR 360p: 2 Mbps
    # SDR 240p: 512 kbps    |    # HDR 240p: 1 Mbps
    # SDR 144p: 256 kbps    |    # HDR 144p: 512 kbps

    sdr_bitrates = {
        '2160p': '25M',
        '1440p': '12M',
        '1080p': '8M',
        '720p': '5M',
        '480p': '2M',
        '360p': '1M',
        '240p': '512k',
        '144p': '256k'
    }
    hdr_bitrates = {
        '2160p': '35M',
        '1440p': '20M',
        '1080p': '12M',
        '720p': '8M',
        '480p': '4M',
        '360p': '2M',
        '240p': '1M',
        '144p': '512k'
    }
    
    ffmpeg_path = resource_path('_ffmpeg.exe') # for py
    ffmpeg_command = [ffmpeg_path,
                      '-i', video_filename,
                      '-i', audio_filename,
                      '-r', '24',
                      '-b:v', get_approximate_bitrate(sdr_bitrates, resolution),
                      '-y']
    mp3_command = [ffmpeg_path,
                   '-i', audio_filename,
                   '-y', mp3_filename]
    
    # check ffmpeg hardware acceleration support
    hardware_acceleration = False
    try:
        result = subprocess.run(['ffmpeg', '-hwaccels'], capture_output=True, text=True, check=True)
        if 'cuda' in result.stdout:
            hardware_acceleration = True
    except subprocess.CalledProcessError as e:
        text_console.config(state=tk.NORMAL)
        text_console.insert(tk.END, f"문제가 발생했습니다.\n{e}\n")
        text_console.see(tk.END)
        text_console.config(state=tk.DISABLED)
        
    # check hardware acceleration support
    if hardware_acceleration:
        ffmpeg_command.extend(['-c:v', 'h264_nvenc'])
    ffmpeg_command.extend(['-preset', 'fast'])
    ffmpeg_command.extend([output_filename])

    status_text.set("Merging video and audio...")

    # run the command
    if video_generation_var.get():
        subprocess.run(ffmpeg_command, check=True)
    if mp3_generation_var.get():
        subprocess.run(mp3_command, check=True)     
    if delete_downloaded_var.get():
        if video_generation_var.get():
            os.remove(video_filename)
            os.remove(audio_filename)
        elif mp3_generation_var.get():
            os.remove(audio_filename)
    status_text.set("Complete merging video and audio...")
    progress["maximum"] = 0
    progress["value"] = 0

def download_button_click():
    try:
        download_link()
    except Exception as e:
        status_text.set(f"문제가 발생했습니다.")
        text_console.config(state=tk.NORMAL)
        text_console.insert(tk.END, f"문제가 발생했습니다.\n{e}\n")
        text_console.see(tk.END)
        text_console.config(state=tk.DISABLED)

def check_button_click():
    link = entry_link.get()
    if not link:
        status_text.set("링크를 입력해주세요.")
        return
    try:
        check_link_validity()
    except Exception as e:
        status_text.set("링크가 잘못되었거나, 서버에 문제가 있습니다.")
        text_console.config(state=tk.NORMAL)
        text_console.insert(tk.END, f"문제가 발생했습니다.\n{e}\n")
        text_console.see(tk.END)
        text_console.config(state=tk.DISABLED)







################################################################
# Window 설정
################################################################

root = tk.Tk()
root.title("유튜브 다운로더")
root.geometry("640x480")

##################################################################
# 위젯 추가
##################################################################

# 레이블 위젯(링크 입력 안내문)
label_link = tk.Label(root, text="Youtube 링크 입력:", font=("Arial", 12))
label_link.grid(row=0, column=0, padx=5, pady=10)

# 엔트리 위젯(링크 입력란)
entry_link = tk.Entry(root, width=45, font=("Arial", 12))
entry_link.insert(0, "input youtube link, right click to paste popup menu")  # 기본값 설정
entry_link.bind("<FocusIn>", select_all)
entry_link.grid(row=0, column=1, padx=0, pady=10)

# Check_button 위젯
button_check = tk.Button(root, text="링크 확인", command=check_button_click)
button_check.grid(row=0, column=2, padx=5, pady=10)



# 엔트리 위젯에 제목 표시
title_text = tk.StringVar()
title_text.set("다운로드할 영상의 제목")
entry_title = tk.Entry(root, textvariable=title_text, width=68,
                       font=("Arial", 12), state='readonly',
                       readonlybackground='lightgray',
                       justify='center')
entry_title.grid(row=1, column=0, columnspan=3, pady=10)

# 분리선 ###########################################################
separator = tk.Frame(root, height=2, bd=2, relief=tk.SUNKEN)
separator.grid(row=2, columnspan=3, sticky="ew")



# 해상도 지정 라벨 위젯(해상도 선택 안내문)
label_resolution = tk.Label(root, text="해상도 선택", font=("Arial", 12))
label_resolution.grid(row=3, column=0, padx=10, pady=10)

# 해상도 지정 콤보박스 위젯(해상도 선택)
combo_resolution = ttk.Combobox(root, values=[""], width=15, font=("Arial", 12))
combo_resolution.current(0)  # 기본값 설정
combo_resolution.grid(row=3, column=1, padx=10, pady=10)

# 버튼 위젯(다운로드 버튼)
button_download  = tk.Button(root, text="다운로드", command=download_button_click)
button_download.grid(row=3, column=2, padx=10, pady=10)



# 체크 박스 위젯 (임시파일 삭제 여부 선택)
delete_downloaded_var = tk.BooleanVar()
delete_downloaded_var.set(True) # 기본값 설정 (체크 상태)
check_delete_downloaded = tk.Checkbutton(root, text="임시파일 삭제", variable=delete_downloaded_var)
check_delete_downloaded.grid(row=4, column=0, padx=10, pady=10) # 체크 박스 배치

# 체크 박스 위젯 (비디오 생성 여부 선택)
video_generation_var = tk.BooleanVar()
video_generation_var.set(True) # 기본값 설정 (체크 상태)
check_video_downloaded = tk.Checkbutton(root, text="비디오 생성", variable=video_generation_var)
check_video_downloaded.grid(row=4, column=1, padx=0, pady=10) # 체크 박스 배치

# 체크 박스 위젯 (MP3 생성 여부 선택)
mp3_generation_var = tk.BooleanVar()
mp3_generation_var.set(False) # 기본값 설정 (체크 해제 상태)
check_mp3_generation = tk.Checkbutton(root, text="MP3 생성", variable=mp3_generation_var)
check_mp3_generation.grid(row=4, column=2, padx=0, pady=10) # 체크 박스 배치



# 분리선 ###########################################################
separator = tk.Frame(root, height=2, bd=2, relief=tk.SUNKEN)
separator.grid(row=5, columnspan=3, sticky="ew")



# 상태 위젯
status_text = tk.StringVar()
status_text.set("상태 표시")
entry_status = tk.Entry(root, textvariable=status_text, width=68,
                        font=("Arial", 12), state='readonly',
                        justify='center', readonlybackground='lightgray',
                        relief='sunken')
entry_status.grid(row=6, column=0, columnspan=3, pady=5)

# 진행률 표시 바 위젯
progress = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=300, mode='determinate')
progress.grid(row=7, column=0, columnspan=3, pady=10)

# Text 위젯
text_console = tk.Text(root, height=15, width=80)
text_console.grid(row=8, column=0, columnspan=3, padx=5, pady=5)
text_console.config(state=tk.DISABLED)

def paste_from_clipboard(event=None):
    try:
        # 클립보드에서 내용 가져오기
        clipboard_content = root.clipboard_get()
        # Entry 위젯에 내용 붙여넣기
        entry_link.delete(0, tk.END)
        entry_link.insert(tk.END, clipboard_content)
    except tk.TclError:
        status_text.set("클립보드가 비어 있습니다.")

def create_popup_menu():
    popup_menu = tk.Menu(entry_link, tearoff=0)
    popup_menu.add_command(label="붙여넣기", command=paste_from_clipboard)

    def show_context_menu(event):
        # 마우스 오른쪽 버튼 클릭 시 팝업 메뉴 표시
        entry_link.focus_set()  # Entry에 포커스 설정
        popup_menu.post(event.x_root, event.y_root)
    
    entry_link.bind("<Button-3>", show_context_menu)  # 우클릭 이벤트 바인딩

# 붙여넣기 우클릭 메뉴 생성 및 바인딩
create_popup_menu()

# 루프 실행
root.mainloop()
