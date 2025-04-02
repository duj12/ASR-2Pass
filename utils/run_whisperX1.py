#!/usr/bin/env python3
# encoding: utf-8

import whisper
import os 
import torch
import logging
import argparse
import zhconv
from tqdm import tqdm
from multiprocessing import Process
from dataclasses import replace
from whisperx.utils import get_writer
import whisperx


torch.set_num_threads(4)
HF_TOKEN = os.environ.get('HF_TOKEN', None)
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
current_path = os.environ.get('PATH', '')
ffmpeg_path = '/home/dujing/ffmpeg-6.0/bin'
if ffmpeg_path not in current_path:
    os.environ['PATH'] = ffmpeg_path + os.pathsep + current_path

ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')
new_path = '/home/dujing/miniconda3/envs/dj_py310/lib/python3.10/site-packages/nvidia/cudnn/lib/'
if new_path not in ld_library_path:
    os.environ['LD_LIBRARY_PATH'] = new_path + os.pathsep + ld_library_path

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
logger.info(f"HF_TOKEN: {HF_TOKEN}")
# global
useful_language = ['zh', 'en']
output_format = "tsv"
MAX_AUDIO_LENGTH = 15  # VAD merge后最长音频段，对应whisper解码最长一段的时长，目前看来好像最终whisper时间戳最长一段还是会接近30s.
MIN_SPEAKERS = 1
MAX_SPEAKERS = 4


def write_result(result: dict, file):
    print("start", "end", "text", "speaker", sep="\t", file=file)
    for segment in result["segments"]:
        if "speaker" not in segment:
            continue
        print(round(1000 * segment["start"]), file=file, end="\t")
        print(round(1000 * segment["end"]), file=file, end="\t")
        text = segment["text"].strip().replace("\t", " ")
        text = zhconv.convert(text, 'zh-cn')
        print(text, file=file, end="\t")
        print(segment["speaker"].strip(), file=file, flush=True)

def process_scp(args, gpu_id, start_idx, chunk_num):
    device = 'cuda'
    gpu_index = int(gpu_id)

    compute_type = "float16"  # change to "int8" if low on GPU mem (may reduce accuracy)

    # model = whisper.load_model("large-v3", device=device)

    model = whisperx.load_model(
        "large-v3", device, device_index=gpu_index,
        compute_type=compute_type,
        asr_options={'initial_prompt': ""})
    logger.info(model.options)

    # writer = {}
    for lang in useful_language:
        os.makedirs(f"{args.output_dir}/{lang}", exist_ok=True)
        # writer[lang] = get_writer(output_format, f"{args.output_dir}/{lang}")

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

            is_transcribed = False
            for lang in useful_language:
                tsv_path = os.path.join(
                    args.output_dir, lang, f"{tsv_name}.{output_format}")
                if os.path.exists(tsv_path):
                    is_transcribed = True
                    logger.warning(f"tsv path: {tsv_path} exits, continue.")
                    break
            if is_transcribed:
                continue

            try:
                audio = whisperx.load_audio(wav)
                if args.language is not None:
                    language = args.language
                else:
                    language = model.detect_language(audio)
                    logger.info(f"language of {wav} is: {language}")
                if language not in useful_language:
                    logger.warning(f"{language} not in useful_language {useful_language}, skip.")
                    continue

                # if language == 'zh':
                #     prompt = '后面的内容，都是普通话的文本。'
                # else:
                #     prompt = ""
                # model.options = replace(model.options, initial_prompt=prompt)  # 这个对象无法写入。。

                result = model.transcribe(
                    audio, batch_size=args.batch_size,
                    language=language, chunk_size=MAX_AUDIO_LENGTH,)

                # 3. Assign speaker labels
                diarize_model = whisperx.DiarizationPipeline(
                    use_auth_token=HF_TOKEN, device=device)

                # add min/max number of speakers if known
                diarize_segments = diarize_model(audio, min_speakers=MIN_SPEAKERS, max_speakers=MAX_SPEAKERS)
                # print(diarize_segments)
                result = whisperx.assign_word_speakers(diarize_segments, result)

            except Exception as e:
                logger.error(f"Whisper Transcribe Error: {e}")
                continue
            else:
                # we save the transcript result with utt name
                # writer[language](result, utt, {})
                result_path = f"{args.output_dir}/{language}/{tsv_name}.{output_format}"

                # print(result["segments"])  # segments are now assigned speaker IDs
                with open(result_path, 'w', encoding='utf-8') as fout:
                    write_result(result, fout)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--wav_scp', type=str, required=True,
                   help='the absolute path of test file.')
    p.add_argument('-o', '--output_dir', type=str, required=False,
                   default=None, help='path to save the generated audios.')
    p.add_argument('-g', '--gpu_ids', type=str, required=False, default='0')
    p.add_argument('-b', '--batch_size', type=int, required=False, default=4)
    p.add_argument('-l', '--language', type=str, required=False, default=None)

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
        p = Process(target=process_scp, args=(
            args, gpu_list[gpu_id], chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for i in process_list:
        p.join()