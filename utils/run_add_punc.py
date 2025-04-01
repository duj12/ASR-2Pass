import argparse
import os
import re
import tqdm
from multiprocessing import Process

def init_punc():
    from funasr import AutoModel
    model = AutoModel(model="ct-punc", model_revision="v2.0.4")
    return model

def remove_special_characters(text):
    pattern = r'[$€£¥￥%@#%&…\(\)\*[\]\{\}×÷+=\/\\|`ˊˋˆˇˉₓ⁰¹²³⁴⁵⁶⁷⁸⁹©®™（）“”，。？！、：；【】;:,.?!"]'
    text = text.lower()
    text1 = re.sub(pattern, '', text)
    text2 = re.sub(r'<[a-zA-Z]+>', '', text1)

    return text2

def mp_process_scp(args, thread_num, gpu_id, start_idx, chunk_num):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    predictor = init_punc()

    result = f"{args.mos_res}.{thread_num}"
    print(f"thread id {thread_num}, save result to {result}")
    fout = open(result, 'w', encoding='utf-8')

    with open(args.wav_scp, 'r', encoding='utf-8') as fin:
        for i, line in enumerate(tqdm.tqdm(fin)):
            if not i in range(start_idx, start_idx + chunk_num):
                continue
            try:
                line = line.strip().split(maxsplit=1)
                if not len(line) == 2:
                    print(f"line: {line} not in kaldi format.")
                    continue
                utt, text = line[0], line[1]
                text = remove_special_characters(text)
                text_punc = predictor.generate(input=text)

                fout.write(f"{utt}\t{text_punc[0]['text']}\n")
                fout.flush()
            except Exception as e:
                print(f"Exception: {e}")
                continue

    fout.close()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', "--wav_scp", default='/data/megastore/SHARE/TTS/VoiceClone2/test/test/text',
                        help='wav.scp contain the wav pathes.')
    parser.add_argument('-o', "--mos_res", default="/data/megastore/SHARE/TTS/VoiceClone2/test/test/text_punc",
                        help='path to the mos result')
    parser.add_argument('-g', "--gpu_ids", default='0', help='gpu device ID')
    parser.add_argument('-n', "--num_thread", type=int, default=2, help='num of jobs')
    args = parser.parse_args()

    gpus = args.gpu_ids
    os.environ['CUDA_VISIBLE_DEVICES'] = gpus
    gpu_list = gpus.split(',')
    gpu_num = len(gpu_list)
    thread_num = int(args.num_thread)  # 每张卡的线程数
    thread_num = len(gpu_list) * thread_num

    wav_scp = args.wav_scp
    output_path = args.mos_res

    f_scp = open(wav_scp)
    total_len = 0
    for line in f_scp:
        total_len += 1

    thread_num = min(thread_num, total_len)
    print(f"Total wavs: {total_len}. gpus: {gpus}, "
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
        p = Process(target=mp_process_scp, args=(
            args, i, gpu_list[gpu_id], chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for p in process_list:
        p.join()

    os.system(f"cat {args.mos_res}.* | sort > {args.mos_res}")
    os.system(f"rm {args.mos_res}.* ")