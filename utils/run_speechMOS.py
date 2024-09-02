import torch
import argparse
import librosa
import tqdm
import os
import logging
from multiprocessing import Process
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class dataset(torch.utils.data.Dataset):
    def __init__(self, wav_scp, sr=16000):
        self.wav_scp = wav_scp
        self.sr = sr
        self.files = list()

        self.path2utt = {}
        with open(self.wav_scp, 'r') as fid:
            for line in fid:
                line = line.strip().split(maxsplit=1)
                utt, path = line[0], line[1]
                self.files.append(path)
                self.path2utt[path] = utt

    def __len__(self):
        return len(self.files)

    def __getitem__(self, item):
        wav_path = self.files[item]
        wav, sr = librosa.load(wav_path, sr=self.sr)
        if wav.ndim > 1:
            wav = wav.mean(-1)
        assert wav.ndim == 1
        wave = torch.from_numpy(wav).float()
        utt = self.path2utt[wav_path]
        return wave, utt

class collate():
    def __init__(self):
        pass

    def __call__(self, batch):
        batch_size = len(batch)
        max_wav_len = max([x[0].size(0) for x in batch])

        waves_padded = torch.zeros(size=(batch_size, max_wav_len), dtype=torch.float, requires_grad=False)
        wave_lengths = torch.zeros(size=(batch_size,), dtype=torch.long, requires_grad=False)
        utts = list()

        padding_mask = torch.BoolTensor(waves_padded.shape).fill_(True)

        for i, (wave, utt) in enumerate(batch):
            waves_padded[i, :wave.size(0)] = wave
            wave_lengths[i] = wave.size(0)
            utts.append(utt)
            padding_mask[i, wave.size(0):] = False

        return waves_padded, wave_lengths, padding_mask, utts

def batch_process_scp(scp, result):
    predictor = torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong",
                               trust_repo=True)
    predictor = predictor.cuda()

    wav_data = dataset(scp, sr=16000)

    # batchsize = 1 now, the code do not support padding mask
    dataloader = torch.utils.data.DataLoader(
        wav_data, num_workers=4, batch_size=1,
        pin_memory=True, drop_last=False, collate_fn=collate()
    )
    total_iteration = len(dataloader)

    fout = open(result, 'w', encoding='utf-8')

    with torch.no_grad():
        count = 0
        for data in tqdm.tqdm(dataloader):
            count += 1
            # if count % 10 == 0:
            #     print(f'Iter {count} / {total_iteration}')
            waves_padded, wave_lengths, padding_mask, utt_names = data
            waves_padded = waves_padded.cuda()
            padding_mask = padding_mask.cuda()

            scores = predictor(waves_padded, sr=wav_data.sr)
            for u, s in zip(utt_names, scores):
                fout.write(f"{u}\t{s}\n")
                fout.flush()

    fout.close()

def mp_process_scp(args, thread_num, gpu_id, start_idx, chunk_num):
    device = torch.device('cuda:{}'.format(gpu_id))
    predictor = torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong",
                               trust_repo=True)
    predictor = predictor.to(device)

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
                    logger.warning(f"line: {line} not in kaldi format.")
                    continue
                utt, wav_path = line[0], line[1]
                if not os.path.exists(wav_path):
                    logger.warning(f"wav path: {wav_path} not exist.")
                    continue

                wave, sr = librosa.load(wav_path, sr=16000)
                wave = torch.from_numpy(wave).unsqueeze(0).to(device)

                scores = predictor(wave, sr=sr)

                fout.write(f"{utt}\t{scores[0].item():.4f}\n")
                fout.flush()
            except Exception as e:
                logger.error(f"Exception: {e}")
                continue

    fout.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', "--wav_scp", default='.',
                        help='wav.scp contain the wav pathes.')
    parser.add_argument('-o', "--mos_res", default=None, help='path to the mos result')
    parser.add_argument('-g', "--gpu_ids", default='0,1,2,3,4,5,6,7', help='gpu device ID')
    parser.add_argument('-n', "--num_thread", type=int, default=3, help='num of jobs')
    args = parser.parse_args()

    gpus = args.gpu_ids
    os.environ['CUDA_VISIBLE_DEVICES'] = gpus
    gpu_list = gpus.split(',')
    gpu_num = len(gpu_list)
    thread_per_gpu = int(args.num_thread)
    thread_num = gpu_num * thread_per_gpu  # threads

    wav_scp = args.wav_scp
    output_path = args.mos_res

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
        p = Process(target=mp_process_scp, args=(
            args, i, gpu_id, chunk_begin, now_chunk_size))
        chunk_begin = chunk_begin + now_chunk_size
        p.start()
        process_list.append(p)

    for i in process_list:
        p.join()

    os.system(f"cat {args.mos_res}.* | sort > {args.mos_res}")
    os.system(f"rm {args.mos_res}.* ")