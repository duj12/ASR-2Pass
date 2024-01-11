# !/usr/bin/env python3
# encoding: utf-8

import os 
import json
import logging
from multiprocessing import Process
from moviepy.editor import *


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# file_handler = logging.FileHandler('app.log')
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)


thread_num = 48
timestamp_shift = 0   # 单位ms 经验值，片段结尾时间需要减去此值
segment_merge_nums = 5   # whisper的转写结果是分段的，每段大约2s, 此值将多个小段合并拼成最后切分的一段音频。
wav_scp="/data/audios/wav.scp"
transcript_path="/data/audios/whisper_transcript"
segment_save_path="/data/audios/whisper_segments"


def process_scp(start_idx, num_files):
    total_duration=0.0
    segments_duration=0.0
    
    f_scp = open(wav_scp, 'r', encoding='utf-8')
    wavs = f_scp.readlines()
    
    wavs = wavs[start_idx: start_idx+num_files]
    
    for wav in wavs:
        wav_splits = wav.strip().split()
        wav_path = wav_splits[1] if len(wav_splits) > 1 else wav_splits[0]
        wav_name = os.path.basename(wav_path)
        wav_name = os.path.splitext(wav_name)[0]
        
        # 保存路径            
        spker_id = os.path.splitext(wav_name)[0]
        spker_dir = f"{segment_save_path}/{spker_id}"
        if not os.path.exists(spker_dir):
            os.makedirs(spker_dir)
        text_file_path = f"{spker_dir}/transcription.txt"
        if os.path.exists(text_file_path):
            continue  # 已经切分过，跳过。
              
        transcription = f"{transcript_path}/{wav_name}.tsv"
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
                logger.warning(f"wav_path:{wav_path}, transcription:{wav_name}.tsv is empty, continue.")
                continue

        # 打开音频文件
        video = VideoFileClip(wav_path)
        audio = video.audio
        total_duration += audio.duration

        # 初始化切分段落列表
        paragraphs = []
        # 初始化切分音频片段列表
        audio_segments = []

        # 初始化当前音频片段的起始时间和标记
        start_time = None  
        segment_end_time = 0.0
        current_segment_text = ""

        # 遍历 JSON 数据
        for i, line in enumerate(data):
            paragraph = line.strip().split('\t')
            if len(paragraph) !=3: # 没有转写内容
                logger.warning(f"transcription:{wav_name}.tsv TSV format is not 'start\tend\ttext', check it.")
                continue
            segment_start_time = float(paragraph[0])
            if start_time == None:  #  设置第一段时间起始点
                start_time = segment_start_time
            segment_end_time = float(paragraph[1]) - timestamp_shift
            text = paragraph[2]
            current_segment_text += text + " "         
            
            if (i+1)%segment_merge_nums==0 and start_time < segment_end_time and start_time/1000.0<audio.duration:
                audio_segment = audio.subclip(start_time / 1000.0, segment_end_time / 1000.0)
                segments_duration += (segment_end_time-start_time)/1000.0
                audio_segments.append(audio_segment)
                paragraphs.append(current_segment_text)
                start_time = segment_end_time  # 更新起始时间为当前句末尾
                current_segment_text = ""  # 清空累计文本

        # 保存最后一个音频片段，因为总段数不是5的倍数，因此最后一段还没被保存 
        if (i+1)%segment_merge_nums!=0 and start_time is not None  \
          and start_time < segment_end_time and start_time/1000.0<audio.duration:
            audio_segment = audio.subclip(start_time / 1000.0, segment_end_time / 1000.0)
            segments_duration += (segment_end_time-start_time)/1000.0
            audio_segments.append(audio_segment)    
            paragraphs.append(current_segment_text)
            start_time = segment_end_time  # 更新起始时间为当前句末尾
            current_segment_text = ""  # 清空累计文本

        # 保存切分的音频片段
        if not len(audio_segments) == len(paragraphs):
            logger.error(f"{wav_name}.tsv: audio segment and text length not equal.")
            continue
        
        if len(paragraphs) == 0:
            continue
        
        with open(text_file_path, 'w', encoding='utf-8') as fout:
            for i, segment in enumerate(audio_segments):
                new_uttid = f"{spker_id}_{i:04d}"
                segment_filename = f'{spker_dir}/{new_uttid}.wav'
                try:
                    fout.write(f"{new_uttid}\t{paragraphs[i]}\n")
                    fout.flush()
                    segment.write_audiofile(segment_filename, codec='pcm_s16le', fps=24000)
                except Exception as e:
                    logger.error(f"Audio write error: {e}") 
                    continue
                else:
                    pass

        # 关闭音频文件
        audio.close()
        video.close()
        
    logger.info(f"Total long audio {total_duration} seconds; Total segments {segments_duration} seconds.")
        

if __name__ == "__main__":    
    f_scp = open(wav_scp)
    wavs = f_scp.readlines()
    total_len = len(wavs)
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
        p = Process(target=process_scp, args=(chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for i in process_list:
        p.join()
        