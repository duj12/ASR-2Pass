# !/usr/bin/env python3
# encoding: utf-8

import os 
import argparse
import logging
import subprocess
import json
from io import BytesIO
from tqdm import tqdm
from multiprocessing import Process
from pydub import AudioSegment


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
# file_handler = logging.FileHandler('app.log')
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)

target_sample_rate = 24000
segment_format = 'flac'

def get_file_duration(file_path):
    ffprobe_cmd = f'ffprobe -v error -show_entries ' \
                  f'format=duration -of json "{file_path}"'
    result = subprocess.run(
        ffprobe_cmd, capture_output=True, text=True, shell=True)
    output = result.stdout
    data = json.loads(output)
    duration = float(data['format']['duration'])
    return duration

def segment_and_convert(
        input_file, output_file, start_time, end_time,
        sample_rate=target_sample_rate, channels=1, sample_width=16):
    ffmpeg_cmd = f'ffmpeg -y -i "{input_file}" -ss {start_time} ' \
                 f'-to {end_time} -ar {sample_rate} -ac {channels} ' \
                 f'-sample_fmt s16 "{output_file}"'
    subprocess.call(ffmpeg_cmd, shell=True)
    print(f"Segment and convert finished: {output_file}")

def load_audio_file(file_path, format='wav'):  # 解决大文件读取
    cmd = ['ffmpeg', '-i', f'{file_path}',
                     '-vn', '-ac', '1',
                     '-sample_fmt', 's16',
                     '-ar', f'{target_sample_rate}',
                     '-f', f'{format}', '-']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    audio_data, _ = process.communicate()
    audio_buffer = BytesIO(audio_data)  # 转换为可寻址的缓冲
    audio = AudioSegment.from_file(audio_buffer, format=f"{format}", mmap=True)
    return audio


def process_scp(args, start_idx, chunk_num):
    total_duration = 0.0
    segments_duration = 0.0
    transcript_path = args.transcript_path
    segment_save_path = args.segment_path

    f_scp = open(args.wav_scp, 'r', encoding='utf-8')
    for i, line in enumerate(tqdm(f_scp)):
        if not i in range(start_idx, start_idx + chunk_num):
            continue

        line = line.strip().split("\t")
        if not len(line) == 2:
            logger.warning(f"line: {line} not in kaldi format.")
            continue
        utt, wav = line[0], line[1]
        if not os.path.exists(wav):
            logger.warning(f"wav path: {wav} not exist.")
            continue

        utt_name = os.path.splitext(utt)[0]   # 文件名作为ID
        transcription = f"{transcript_path}/{utt_name}.tsv"
        if not os.path.exists(transcription):
            logging.warning(f"{transcription} not exist, continue.")
            continue

        # 读取 tsv 文件
        with open(transcription) as tsv_file:
            data = tsv_file.readlines()
            if len(data) < 1:
                continue
            data = data[1:]  # 跳过第一行标题
            if len(data) == 0:
                logger.warning(
                    f"wav_path:{wav}, transcription:"
                    f"{utt_name}.tsv is empty, continue.")
                continue

        speaker_diarization = {}
        for line in data:
            line = line.strip().split("\t")
            if len(line) != 4:
                continue
            start, end, text, spk = line[0], line[1], line[2], line[3]
            if spk not in speaker_diarization:
                speaker_diarization[spk] = []
            speaker_diarization[spk].append([start,end,text])

        for speaker in speaker_diarization.keys():
            # 保存路径, 以文件名-说话人序号，作为说话人ID
            spker_id = f"{utt_name}-{speaker}"
            spker_dir = f"{segment_save_path}/{spker_id}"
            # 处理可能存在.号导致的文件夹创建失败。
            spker_dir = spker_dir.replace(".", "-", -1)
            text_file_path = f"{spker_dir}/transcription.txt"
            if os.path.exists(text_file_path):
                logging.warning(f"{text_file_path} already exists, pass.")
                continue  # 已经切分过，跳过。

        try:
            # 读取长音频
            # audio = AudioSegment.from_file(wav)
            audio = load_audio_file(wav)
        except Exception as e:
            logger.error(f"Loading wav {wav} error, {e}")
            continue
        else:
            # audio = audio.set_frame_rate(target_sample_rate)
            current_duration = float(get_file_duration(wav))
            total_duration += current_duration

        for speaker in speaker_diarization.keys():
            try:
                # 保存路径, 以文件名-说话人序号，作为说话人ID
                spker_id = f"{utt_name}-{speaker}"
                spker_dir = f"{segment_save_path}/{spker_id}"
                # 处理可能存在.号导致的文件夹创建失败。
                spker_dir = spker_dir.replace(".", "-", -1)
                if not os.path.exists(spker_dir):
                    os.makedirs(spker_dir, exist_ok=True)
                text_file_path = f"{spker_dir}/transcription.txt"
                if os.path.exists(text_file_path):
                    logging.warning(f"{text_file_path} already exists, pass.")
                    continue  # 已经切分过，跳过。
                    # pass

                fout = open(text_file_path, 'w', encoding='utf-8')
                segment_idx = 0
                data = speaker_diarization[speaker]
                for i, paragraph in enumerate(data):
                    if len(paragraph) < 3:  # 没有转写内容
                        logger.warning(
                            f"transcription:{utt_name}.tsv "
                            f"format is not 'start\tend\ttext', check it.")
                        continue
                    segment_start_time = float(paragraph[0])
                    segment_end_time = float(paragraph[1])
                    segment_text = paragraph[2]

                    segments_duration += (segment_end_time-segment_start_time) / 1000.0
                    new_uttid = f"{spker_id}_{segment_idx:04d}"
                    segment_filename = f'{spker_dir}/{new_uttid}.{segment_format}'
                    fout.write(f"{new_uttid}\t{segment_text}\n")
                    fout.flush()
                    segment_idx += 1
                    audio_segment = audio[segment_start_time:segment_end_time]
                    audio_segment.export(segment_filename, format=segment_format,
                                         parameters=["-ar", f"{target_sample_rate}", "-ac", "1"])

                fout.close()

            except Exception as e:
                logger.error(f"Audio Segment Error: {e}")
                continue
            else:
                pass

        del audio

    f_scp.close()
    logger.info(f"Total long audio {total_duration} seconds; "
                f"Total segments {segments_duration} seconds.")

        

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--wav_scp', type=str, required=True,
                   help='the absolute path of test file.')
    p.add_argument('-t', '--transcript_path', type=str, required=True,
                   help='the absolute path of transcription file.')
    p.add_argument('-o', '--segment_path', type=str, required=False,
                   default=None, help='path to save the segmented audios.')
    p.add_argument('-n', '--num_thread', type=str, required=False, default='1')

    args = p.parse_args()
    thread_num = int(args.num_thread)
    f_scp = open(args.wav_scp)
    total_len = 0
    for line in f_scp:
        total_len += 1

    thread_num = min(thread_num, total_len)
    logger.info(f"Total wavs: {total_len}, Thread nums: {thread_num}")
    if total_len >= thread_num:
        chunk_size = int(total_len / thread_num)
        remain_wavs = total_len - chunk_size * thread_num
    else:
        chunk_size = 1
        remain_wavs = 0

    process_list = []
    chunk_begin = 0
    for i in range(thread_num):
        now_chunk_size = chunk_size
        if remain_wavs > 0:
            now_chunk_size = chunk_size + 1
            remain_wavs = remain_wavs - 1
        # process i handle wavs at chunk_begin and size of now_chunk_size
        p = Process(target=process_scp, args=(
            args, chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for i in process_list:
        p.join()
        