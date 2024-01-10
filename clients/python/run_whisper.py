#!/usr/bin/env python3
# encoding: utf-8

import whisper
import os 
import torch
import logging
from multiprocessing import Process
from whisper.utils import get_writer   # 更新的whisper才有，第三方batch版本还没有
torch.set_num_threads(4)

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

gpus = '0,1,2,3,4,5,6,7'
os.environ['CUDA_VISIBLE_DEVICES'] = gpus
gpu_list = gpus.split(',')
gpu_num = len(gpu_list)
thread_per_gpu = 6    #  1 thread ~ 11G GPU_memory
thread_num = gpu_num * thread_per_gpu    #  threads
logger.info(f"gpus: {gpus}, num threads: {thread_num}.")

wav_scp = "/data/audios/wav.scp"
output_format = "tsv"
output_dir = "/data/audios/whisper_transcript"
os.makedirs(output_dir, exist_ok=True)

lang = 'zh'
prompt = '以下是普通话的句子'


def process_scp(gpu_id, start_idx, chunk_num):
    device = torch.device('cuda:{}'.format(gpu_id))
    model = whisper.load_model("large-v3", device=device)
    writer = get_writer(output_format, output_dir)
    
    wavs = []
    with open(wav_scp) as fin:
        for line in fin:
            line=line.strip().split()
            wavs.append(line[1])
            
    cur_chunk = wavs[start_idx: start_idx + chunk_num]

    for wav in cur_chunk:
        if not os.path.exists(wav):
            logger.warning(f"wav path: {wav} not exist.")
            continue
        result = model.transcribe(
            wav, language=lang, verbose=True, initial_prompt=prompt)
        writer(result, wav, {})

if __name__ == "__main__":
    f_scp = open(wav_scp)
    wavs = f_scp.readlines()
    total_len = len(wavs)
    logger.info(f"Total wavs: {total_len}.")
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
        p = Process(target=process_scp, args=(gpu_id, chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for i in process_list:
        p.join()