#!/usr/bin/env python3
# encoding: utf-8

import os
import shutil
import sys
from multiprocessing import Process

wav_scp = sys.argv[1]  # "/data/audios/wav.scp"
output_wav_root = sys.argv[2]  # "/data/megastore/SHARE/TTS/VoiceClone2/"
thread_num = sys.argv[3]

def process_scp(start_idx, chunk_size, queue):
    f_scp = open(wav_scp, 'r', encoding='utf-8')
    wavs = f_scp.readlines()
    wavs = wavs[start_idx: start_idx+chunk_size]
    for wav in wavs:
        try:
            wav_splits = wav.strip().split()
            wav_path = wav_splits[1] if len(wav_splits) > 1 else wav_splits[0]
            if not os.path.exists(wav_path):
                continue
            wav_path_list = wav_path.split('/')[-2]
            if len(wav_path_list) < 2:
                print(f"wav_path: {wav_path} may not include speaker name.")
                continue
            speaker_name = wav_path.split('/')[-2]
            output_dir = os.path.join(output_wav_root, speaker_name)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                shutil.copy(wav_path, output_dir)
        except Exception as e:
            print(e)


if __name__ == "__main__":    
    f_scp = open(wav_scp)
    wavs = f_scp.readlines()
    total_len = len(wavs)
    print(f"Total wavs: {total_len}, Thread nums: {thread_num}")
    
    if total_len >= thread_num:
        chunk_size = int(total_len / thread_num)
        remain_wavs = total_len - chunk_size * thread_num
    else:
        chunk_size = 1
        remain_wavs = 0

    process_list = []
    chunk_begin = 0
    duration_list = []

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
