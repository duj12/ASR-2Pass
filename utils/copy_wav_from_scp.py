#!/usr/bin/env python3
# encoding: utf-8

import os
import shutil
import argparse
from multiprocessing import Process

def process_scp(args, start_idx, chunk_size):
    wav_scp = args.wav_scp
    output_wav_root = os.path.join(args.output_dir, "wav")
    os.makedirs(output_wav_root, exist_ok=True)

    f_scp = open(wav_scp, 'r', encoding='utf-8')
    for i, line in enumerate(f_scp):
        if not i in range(start_idx, start_idx+chunk_size):
            continue
        try:
            line = line.strip().split()
            if len(line) != 2:
                print(f"line {line} is not in kaldi format. check it.")
            utt_name, wav_path = line[0], line[1]
            wav_name = os.path.basename(wav_path)
            if not os.path.exists(wav_path):
                print(f"wav_path: {wav_path} not exist.")
                continue
            wav_path_list = wav_path.split('/')
            if len(wav_path_list) < 2:
                print(f"wav_path: {wav_path} may not include speaker name.")
                continue
            speaker_name = wav_path_list[-2]
            output_dir = os.path.join(output_wav_root, speaker_name)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, wav_name)
            if not os.path.exists(output_path):
                shutil.copy(wav_path, output_path)
        except Exception as e:
            print(e)
    f_scp.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--wav_scp', type=str, required=True,
                   help='the absolute path of test file.')
    p.add_argument('-o', '--output_dir', type=str, required=False,
                   default=None, help='path to save the generated audios.')
    p.add_argument('-n', '--num_thread', type=str, required=False, default='1')
    args = p.parse_args()

    thread_num = int(args.num_thread)
    f_scp = open(args.wav_scp)
    total_len = 0
    for line in f_scp:
        total_len += 1
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
        p = Process(target=process_scp, args=(args, chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for i in process_list:
        p.join()       
