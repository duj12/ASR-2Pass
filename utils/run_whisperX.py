#!/usr/bin/env python3
# encoding: utf-8

import whisper
import os 
import torch
import logging
import argparse
from tqdm import tqdm
from multiprocessing import Process
from whisperx.utils import get_writer
import whisperx


torch.set_num_threads(4)

# os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
# current_path = os.environ.get('PATH', '')
# ffmpeg_path = '/home/dujing/ffmpeg-6.0/bin'
# if ffmpeg_path not in current_path:
#     os.environ['PATH'] = ffmpeg_path + os.pathsep + current_path
#
# ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')
# new_path = '/home/dujing/miniconda3/envs/dj_py310/lib/python3.10/site-packages/nvidia/cudnn/lib/'
# if new_path not in ld_library_path:
#     os.environ['LD_LIBRARY_PATH'] = new_path + os.pathsep + ld_library_path

logger = logging.getLogger(__name__)

# global
output_format = "tsv"
MAX_AUDIO_LENGTH = 15  # VAD merge后最长音频段，对应whisper解码最长一段的时长，目前看来好像最终whisper时间戳最长一段还是会接近30s.


def process_scp(args, gpu_id, start_idx, chunk_num):
    device = 'cuda'
    gpu_index = int(gpu_id)
    batch_size = 16  # reduce if low on GPU mem
    compute_type = "float16"  # change to "int8" if low on GPU mem (may reduce accuracy)

    # model = whisper.load_model("large-v3", device=device)
    if args.language == 'zh':
        prompt = '后面的内容，都是普通话的文本。'
    else:
        prompt = ""
    asr_options = {
        "initial_prompt": prompt,
    }
    model = whisperx.load_model(
        "large-v3", device, device_index=gpu_index, language=args.language,
        asr_options=asr_options, compute_type=compute_type)

    writer = get_writer(output_format, args.output_dir)
    
    with open(args.wav_scp, 'r', encoding='utf-8') as fin:
        for i, line in enumerate(tqdm(fin)):
            if not i in range(start_idx, start_idx+chunk_num):
                continue

            line = line.strip().split('\t')
            if not len(line) == 2:
                logger.warning(f"line: {line} not in kaldi format.")
                continue
            utt, wav = line[0], line[1]
            if not os.path.exists(wav):
                logger.warning(f"wav path: {wav} not exist.")
                continue
            tsv_name = os.path.splitext(utt)[0]
            tsv_path = os.path.join(args.output_dir, f"{tsv_name}.tsv")
            if os.path.exists(tsv_path):
                logger.warning(f"tsv path: {tsv_path} exits, continue.")
                continue
            try:
                audio = whisperx.load_audio(wav)
                result = model.transcribe(
                    audio, batch_size=args.batch_size, chunk_size=MAX_AUDIO_LENGTH,)
                # result = model.transcribe(
                #     wav, language=args.language,
                #     verbose=True, initial_prompt=prompt)
                # we save the transcript result with utt name
                writer(result, utt, {})
                # print(result["segments"])
            except Exception as e:
                logger.error(f"Whisper Transcribe Error: {e}")
                continue

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--wav_scp', type=str, required=True,
                   help='the absolute path of test file.')
    p.add_argument('-o', '--output_dir', type=str, required=False,
                   default=None, help='path to save the generated audios.')
    p.add_argument('-g', '--gpu_ids', type=str, required=False, default='0')
    p.add_argument('-b', '--batch_size', type=int, required=False, default=4)
    p.add_argument('-l', '--language', type=str, required=True, default='zh')

    args = p.parse_args()

    gpus = args.gpu_ids
    gpu_list = gpus.split(',')
    gpu_num = len(gpu_list)
    lang = args.language
    thread_num = gpu_num  # threads

    wav_scp = args.wav_scp
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    f_scp = open(wav_scp)
    total_len = 0
    for line in f_scp:
        total_len += 1

    thread_num = min(thread_num, total_len)
    logger.info(f"Total wavs: {total_len}. gpus: {gpus}, "
                f"num threads: {thread_num}.")
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
        gpu_index = gpu_list[gpu_id]
        p = Process(target=process_scp, args=(
            args, gpu_index, chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for i in process_list:
        p.join()