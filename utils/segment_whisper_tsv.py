# !/usr/bin/env python3
# encoding: utf-8

import os 
import argparse
import logging
import subprocess
import json
from tqdm import tqdm
from multiprocessing import Process


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# global
timestamp_shift = 0   # 单位ms 经验值，片段结尾时间需要减去此值
segment_min_second = 10  # 最后保存的音频最短长度s。

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
        sample_rate=24000, channels=1, sample_width=16):
    ffmpeg_cmd = f'ffmpeg -y -i "{input_file}" -ss {start_time} ' \
                 f'-to {end_time} -ar {sample_rate} -ac {channels} ' \
                 f'-sample_fmt s16 "{output_file}"'
    subprocess.call(ffmpeg_cmd, shell=True)
    print(f"Segment and convert finished: {output_file}")

def process_scp(args, start_idx, chunk_num):
    total_duration = 0.0
    segments_duration = 0.0
    transcript_path = args.transcript_path
    segment_save_path = args.segment_path

    f_scp = open(args.wav_scp, 'r', encoding='utf-8')
    for i, line in enumerate(tqdm(f_scp)):
        if not i in range(start_idx, start_idx + chunk_num):
            continue

        line = line.strip().split()
        if not len(line) == 2:
            logger.warning(f"line: {line} not in kaldi format.")
            continue
        utt, wav = line[0], line[1]
        if not os.path.exists(wav):
            logger.warning(f"wav path: {wav} not exist.")
            continue

        spker_id = os.path.splitext(utt)[0]
        transcription = f"{transcript_path}/{spker_id}.tsv"
        if not os.path.exists(transcription):
            logging.warning(f"{transcription} not exist, continue.")
            continue

        # 保存路径
        spker_dir = f"{segment_save_path}/{spker_id}"
        if not os.path.exists(spker_dir):
            os.makedirs(spker_dir)
        text_file_path = f"{spker_dir}/transcription.txt"
        if os.path.exists(text_file_path):
            # continue  # 已经切分过，跳过。
            pass

        fout = open(text_file_path, 'w', encoding='utf-8')

        # 读取 tsv 文件
        with open(transcription) as tsv_file:
            data = tsv_file.readlines()
            if len(data) < 1:
                continue
            data = data[1:]  # 跳过第一行标题
            if len(data) == 0:
                logger.warning(
                    f"wav_path:{wav}, transcription:"
                    f"{spker_id}.tsv is empty, continue.")
                continue

        try:
            current_duration = float(get_file_duration(wav))
            total_duration += current_duration

            # 初始化当前音频片段的起始时间和标记
            start_time = None
            segment_end_time = 0.0
            current_segment_text = ""
            segment_idx = 0
            for i, line in enumerate(data):
                paragraph = line.strip().split('\t')
                if len(paragraph) != 3:  # 没有转写内容
                    logger.warning(
                        f"transcription:{spker_id}.tsv "
                        f"format is not 'start\tend\ttext', check it.")
                    continue
                segment_start_time = float(paragraph[0])
                if start_time == None:  # 设置第一段时间起始点
                    start_time = segment_start_time
                segment_end_time = float(paragraph[1]) - timestamp_shift
                text = paragraph[2]
                current_segment_text += text + " "

                if segment_end_time - start_time >= segment_min_second * 1000 \
                        and start_time < segment_end_time \
                        and start_time / 1000.0 < current_duration:
                    segments_duration += (segment_end_time-start_time) / 1000.0
                    new_uttid = f"{spker_id}_{segment_idx:04d}"
                    segment_filename = f'{spker_dir}/{new_uttid}.wav'
                    fout.write(f"{new_uttid}\t{current_segment_text}\n")
                    fout.flush()
                    segment_and_convert(
                        wav, segment_filename,
                        start_time/1000.0, segment_end_time/1000.0)

                    start_time = segment_end_time  # 更新起始时间为当前句末尾
                    current_segment_text = ""  # 清空累计文本
                    segment_idx += 1

            # 保存最后一个音频片段，因为总段数不是5的倍数，因此最后一段还没被保存
            if current_segment_text != "" and start_time is not None \
                    and start_time < segment_end_time \
                    and start_time / 1000.0 < current_duration:
                segments_duration += (segment_end_time - start_time) / 1000.0
                new_uttid = f"{spker_id}_{segment_idx:04d}"
                segment_filename = f'{spker_dir}/{new_uttid}.wav'
                fout.write(f"{new_uttid}\t{current_segment_text}\n")
                fout.flush()
                segment_and_convert(
                    wav, segment_filename,
                    start_time / 1000.0, segment_end_time / 1000.0)
                start_time = segment_end_time  # 更新起始时间为当前句末尾
                current_segment_text = ""  # 清空累计文本
                segment_idx += 1

        except Exception as e:
            logger.error(f"Audio Segment Error: {e}")
            continue
        else:
            pass

    fout.close()
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
        