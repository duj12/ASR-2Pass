#!/usr/bin/env bash

ASR2PASS_ROOT="$(cd "$(dirname "$0")" && pwd)"

audio_dir=$1
echo "# 转写的音频绝对路径为：$audio_dir"

result_dir=$audio_dir/whisper_transcript
segment_dir=$audio_dir/whisper_segment
data_dir=$audio_dir/data
data_acc95_dir=$data_dir/acc95
mkdir -p $data_acc95_dir

gpu_ids=0,1,2,3,4,5,6,7
lang=zh

stage=0
if [ "$#" -ge 2 ]; then
  stage="$2"
fi

. ./utils/parse_options.sh  ||  exit 1;


# prepare wav.scp, find all wav and mp4 files
if [ $stage -le 0 ]; then
echo "# 第0.0步, 将转写文件调整格式列到wav.scp文件中"
find  $audio_dir  -type f \( -name "*.wav" -o -name "*.mp4" \) | awk -F"/"  -v name="" \
  -v root=$audio_dir '{name=$0; gsub(root,"",name); gsub("/","_",name); print name"\t"$0 }' | sort > $audio_dir/wav.scp
echo "# 第0.1步, 去除音频路径中带有的空格，将空格替换成-"
python $ASR2PASS_ROOT/clients/audio/rm_space_in_path.py $audio_dir/wav.scp
echo "# 第0.2步, 重新把全部转写文件路径列入到wav.scp中"
find  $audio_dir  -type f \( -name "*.wav" -o -name "*.mp4" \) | awk -F"/" -v name="" \
  -v root=$audio_dir '{name=$0; gsub(root,"",name); gsub("/","_",name);  print name"\t"$0 }' | sort > $audio_dir/wav.scp

fi

# whisper transcribe, get segment timestamp and text
# the whisper-1.6B model consume 12G GPU-RAM per thread. A100-80G can run 6 threads.
if [ $stage -le 1 ]; then
  echo "# 第1步，使用Whisper-large-v3模型转写。"
  python3 run_whisper.py  \
      -i  $audio_dir/wav.scp \
      -o  $result_dir \
      -g  $gpu_ids  \
      -n  6         \
      -l  $lang

fi

# segment the audio/video with whisper segments
if [ $stage -le 2 ]; then
  echo "# 第2步，根据转写得到的时间戳对音视频进行切分，得到切分后的wav。"
  python3 segment_whisper_tsv.py  \
    -i  $audio_dir/wav.scp \
    -t  $result_dir  \
    -o  $segment_dir  \
    -n  48

fi

# prepare wav.scp, text, find all segments.
if [ $stage -le 3 ]; then
  echo "# 第3步，准备转写所需的kaldi格式数据，包含wav.scp和text"
  find  $segment_dir  -type f  -name "*.wav" | awk -F"/"  -v name="" \
     '{name=$NF; gsub(".wav","",name); print name"\t"$0 }' | sort > $data_dir/wav.scp
  cat  $segment_dir/*/transcription.txt | sort > $data_dir/text

fi

if [ $stage -le 4 ]; then
  echo "# 第4步，使用Paraformer模型进行转写，并计算CER，筛选出CER<=5%的数据"
  bash infer_paraformer.sh  $data_dir

fi



fi
