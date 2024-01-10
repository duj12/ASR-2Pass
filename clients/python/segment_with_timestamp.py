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


thread_num = 1
timestamp_shift = 1200   # 单位ms 经验值，片段结尾时间需要减去此值
wav_scp="/data/audios/wav.scp0"
transcript_path="/data/audios/timestamp_json"
segment_save_path="/data/audios/segments"


def process_scp(start_idx, num_files):
    f_scp = open(wav_scp, 'r', encoding='utf-8')
    wavs = f_scp.readlines()
    
    wavs = wavs[start_idx: start_idx+num_files]
    
    for wav in wavs:
        wav_splits = wav.strip().split()
 
        wav_name = wav_splits[0] if len(wav_splits) > 1 else "demo"
        wav_path = wav_splits[1] if len(wav_splits) > 1 else wav_splits[0]
        if not len(wav_path.strip())>0:
            continue
       
        transcription = f"{transcript_path}/{wav_name}.asr.txt"
        if not os.path.exists(transcription):
            logging.warning(f"{transcription} not exist, continue.")
            continue
        # 读取 JSON 文件
        with open(transcription) as json_file:
            data = json.load(json_file)

        # 打开音频文件
        video = VideoFileClip(wav_path)
        audio = video.audio

        # 初始化切分段落列表
        paragraphs = []
        # 初始化切分音频片段列表
        audio_segments = []

        # 初始化当前音频片段的起始时间和标记
        start_time = 0.0  
        segment_end_time = 0.0
        punc = "。"
        current_segment_text = ""

        # 遍历 JSON 数据
        for paragraph in data:
            segment_start_time = float(paragraph['start'])
            if start_time == 0.0:  #  设置第一段时间起始点
                start_time = segment_start_time
            segment_end_time = float(paragraph['end']) - timestamp_shift
            text = paragraph['text_seg']
            punc = paragraph['punc']
            
            current_segment_text += text + " " + punc
            
            
            if punc == '。' and start_time < segment_end_time and start_time/1000.0<audio.duration:
                audio_segment = audio.subclip(start_time / 1000.0, segment_end_time / 1000.0)
                audio_segments.append(audio_segment)
                paragraphs.append(current_segment_text)
                start_time = segment_end_time  # 更新起始时间为当前句末尾
                current_segment_text = ""  # 清空累计文本

        # 保存最后一个音频片段，因为句尾不是句号，因此最后一段还没被保存 
        if punc != "。" and start_time < segment_end_time and start_time/1000.0<audio.duration:
            audio_segment = audio.subclip(start_time / 1000.0, segment_end_time / 1000.0)
            audio_segments.append(audio_segment)    
            paragraphs.append(current_segment_text)
            start_time = segment_end_time  # 更新起始时间为当前句末尾
            current_segment_text = ""  # 清空累计文本

        # 保存切分的音频片段
        assert len(audio_segments) == len(paragraphs), f"{wav_path}.ast.txt: audio segment and text length not equal."
        spker_id = os.path.splitext(wav_name)[0]
        spker_dir = f"{segment_save_path}/{spker_id}"
        if not os.path.exists(spker_dir):
            os.makedirs(spker_dir)
        text_file_path = f"{spker_dir}/transcription.txt"
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
        

if __name__ == "__main__":
    f_scp = open(wav_scp)
    wavs = f_scp.readlines()
    for wav in wavs:
        wav_splits = wav.strip().split()
        wav_name = wav_splits[0] if len(wav_splits) > 1 else "demo"
        wav_path = wav_splits[1] if len(wav_splits) > 1 else wav_splits[0]
        audio_type = os.path.splitext(wav_path)[-1].lower()

    total_len = len(wavs)
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