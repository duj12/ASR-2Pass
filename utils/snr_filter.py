import os
import argparse
import subprocess
import soundfile as sf
import numpy as np
from tqdm import tqdm
from multiprocessing import Pool

wadasnr_dir=""
def check_and_configure_wadasnr(wadasnr_path):
    # 参考 https://github.com/coqui-ai/TTS/discussions/1074
    if not os.path.exists(f"{wadasnr_path}/Exe/WADASNR"):
        subprocess.run(["curl", "http://www.cs.cmu.edu/~robust/archive/algorithms/WADA_SNR_IS_2008/WadaSNR.tar.gz", "--output", os.path.join(wadasnr_path, "WadaSNR.tar.gz")])
        subprocess.run(["tar", "-xvf", os.path.join(wadasnr_path, "WadaSNR.tar.gz"), "-C", wadasnr_path])
        subprocess.run(["sudo", "chmod", "+x", os.path.join(wadasnr_path, "Exe/WADASNR")])

        try:
            subprocess.run([os.path.join(wadasnr_path, "Exe/WADASNR")], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            print("WADASNR 无法执行。请检查路径和依赖项。")

        # 验证文件类型
        file_type = subprocess.run(["file", os.path.join(wadasnr_path, "Exe/WADASNR")], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode("utf-8")
        if "LSB executable" in file_type:
            # 安装 gcc-multilib
            subprocess.run(["sudo", "apt-get", "install", "gcc-multilib"])
        else:
            print("WADASNR 不是一个 LSB 可执行文件。检查下载过程或者自己重新编译。")

def compute_file_snr(file_path):
    """ Convert given file to required format with FFMPEG and process with WADA.
        目前看起来，这个方法得到的结果不是很可靠。不如自己使用分帧计算能量的方式计算的结果准确。
    """

    try:
        _, sr = sf.read(file_path)
        if sr != 16000:
            new_file = file_path.replace(".wav", "_tmp.wav")
            new_file = os.path.basename(new_file)
            command = f'ffmpeg -i "{file_path}" -ac 1 -acodec pcm_s16le -y -ar 16000 "{new_file}"'
            os.system(command)
        else:
            new_file = file_path
        command = [f'"{wadasnr_dir}/Exe/WADASNR"', f'-i "{new_file}"', f'-t "{wadasnr_dir}/Exe/Alpha0.400000.txt"', '-ifmt mswav']
        output = subprocess.check_output(" ".join(command), shell=True)
        if new_file != file_path:
            os.system(f'rm "{new_file}"')
        output = float(output.split()[-3].decode("utf-8"))
    except Exception as e:
        print(f"SNR Estimation Error: {e}")
        return 0.0, file_path
    return output, file_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('-d', '--wadasnr_dir', type=str, required=True,
                   help='the path of WADA file.')
    p.add_argument('-i', '--wav_scp', type=str, required=True,
                   help='the absolute path of test file.')
    p.add_argument('-o', '--snr_res', type=str, required=False,
                   default=None, help='path to store snr result, txt.')
    p.add_argument('-n', '--num_thread', type=str, required=False, default='1')

    args = p.parse_args()

    wav_scp = args.wav_scp
    f_scp = open(wav_scp)
    total_len = 0
    wav_files = []
    path2utt = {}
    for line in f_scp:
        line = line.strip().split()
        utt, path = line[0], line[1]
        wav_files.append(path)
        path2utt[path] = utt
        total_len += 1

    print(f" > Number of wav files {len(wav_files)}")

    wadasnr_dir = args.wadasnr_dir
    if not os.path.exists(wadasnr_dir):
        os.makedirs(wadasnr_dir, exist_ok=True)
    check_and_configure_wadasnr(wadasnr_dir)


    NUM_PROC = int(args.num_thread)  # threads
    if NUM_PROC == 1:
        file_snrs = [None] * len(wav_files)
        for idx, wav_file in tqdm(enumerate(wav_files)):
            tup = compute_file_snr(wav_file)
            file_snrs[idx] = tup
    else:
        with Pool(NUM_PROC) as pool:
            file_snrs = list(tqdm(pool.imap(compute_file_snr, wav_files), total=len(wav_files)))
    snrs = [tup[0] for tup in file_snrs]

    error_idxs = np.where(np.isnan(snrs) == True)[0]
    error_files = [wav_files[idx] for idx in error_idxs]

    file_snrs = [i for j, i in enumerate(file_snrs) if j not in error_idxs]
    file_names = [tup[1] for tup in file_snrs]
    snrs = [tup[0] for tup in file_snrs]
    file_idxs = np.argsort(snrs)

    print(f" > Average SNR of the dataset:{np.mean(snrs)}")
    with open(args.snr_res ,'w', encoding='utf-8') as fout:
        for (path, snr) in zip(file_names, snrs):
            utt = path2utt[path]
            fout.write(f"{utt}\t{snr}\n")