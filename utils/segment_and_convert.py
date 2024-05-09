import os
import subprocess
import string

def is_english_string(s):
    return all(char.isalpha() or char in string.punctuation or char.isspace() for char in s)

def segment_and_convert(
        input_file,  segment_duration,
        sample_rate=24000, channels=1, sample_width=16):
    # Ensure output folder exists
    output_folder = os.path.dirname(input_file)  # 音频所在文件夹，之前确保已经没有空格
    name = os.path.basename(input_file)          # 音频名称
    name = os.path.splitext(name)[0]             # 音频名无后缀
    name = name.replace(" ", "-")                # 如果文件名还有空格就替换
    if is_english_string(name):
        name = name[:20]  # 最长20个英文字符，避免路径太长。
    else:
        name = name[:15]  # 中文名称比较宽，字数卡更短
    output_folder = os.path.join(output_folder, name)
    os.makedirs(output_folder, exist_ok=True)
    # Get total duration of input file
    ffprobe_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{input_file}"'
    total_duration = float(subprocess.check_output(ffprobe_cmd, shell=True).decode().strip())

    # Segment and convert
    current_time = 0
    segment_index = 0
    while current_time < total_duration:
        start_time = current_time
        end_time = min(current_time + segment_duration, total_duration)
        output_file = os.path.join(output_folder, f'{name}_{segment_index:02d}.wav')
        ffmpeg_cmd = f'ffmpeg -y -i "{input_file}" -ss {start_time} ' \
                     f'-to {end_time} -ar {sample_rate} -ac {channels} ' \
                     f'-sample_fmt s16 "{output_file}"'
        subprocess.call(ffmpeg_cmd, shell=True)
        current_time += segment_duration
        segment_index += 1

# Example usage:
import sys
input_file = sys.argv[1]        # 输入音频路径，输出的短音频保存在其所在文件夹下面，以音频名称命名。
segment_duration = float(sys.argv[2])  # in seconds

try:
    segment_and_convert(input_file, segment_duration)
except Exception as e:
    print(f"Segment Audio File Error:{e}, You need to check it.")
else:
    pass
    # os.remove(input_file)
