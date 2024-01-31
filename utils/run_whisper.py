#!/usr/bin/env python3
# encoding: utf-8

import whisper
import os 
import torch
import logging
import argparse
from tqdm import tqdm
from multiprocessing import Process
from whisper.utils import get_writer
torch.set_num_threads(4)

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

# global
output_format = "tsv"
prompt = '以下是普通话的句子'


def process_scp(args, gpu_id, start_idx, chunk_num):
    device = torch.device('cuda:{}'.format(gpu_id))
    model = whisper.load_model("large-v3", device=device)
    writer = get_writer(output_format, args.output_dir)
    
    with open(args.wav_scp, 'r', encoding='utf-8') as fin:
        for i, line in enumerate(tqdm(fin)):
            if not i in range(start_idx, start_idx+chunk_num):
                continue

            line = line.strip().split()
            if not len(line) == 2:
                logger.warning(f"line: {line} not in kaldi format.")
                continue
            utt, wav = line[0], line[1]
            if not os.path.exists(wav):
                logger.warning(f"wav path: {wav} not exist.")
                continue
            result = model.transcribe(
                wav, language=args.language, verbose=True, initial_prompt=prompt)
            # we save the transcript result with utt name
            writer(result, utt, {})

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--wav_scp', type=str, required=True,
                   help='the absolute path of test file.')
    p.add_argument('-o', '--output_dir', type=str, required=False,
                   default=None, help='path to save the generated audios.')
    p.add_argument('-g', '--gpu_ids', type=str, required=False, default='0')
    p.add_argument('-n', '--num_thread', type=str, required=False, default='1')
    p.add_argument('-l', '--language', type=str, required=True, default='zh')

    args = p.parse_args()

    gpus = args.gpu_ids
    os.environ['CUDA_VISIBLE_DEVICES'] = gpus
    gpu_list = gpus.split(',')
    gpu_num = len(gpu_list)
    lang = args.language
    thread_per_gpu = int(args.num_thread)  # 1 thread ~ 11G GPU_memory
    thread_num = gpu_num * thread_per_gpu  # threads

    wav_scp = args.wav_scp
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    f_scp = open(wav_scp)
    total_len = 0
    for line in f_scp:
        total_len += 1

    thread_num = min(thread_num, total_len)
    logger.info(f"Total wavs: {total_len}. gpus: {gpus}, num threads: {thread_num}.")
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
        gpu_id = i % gpu_num   
        p = Process(target=process_scp, args=(
            args, gpu_id, chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for i in process_list:
        p.join()