#!/usr/bin/env bash

gpu_ids=0,1,2,3,4,5,6,7
lang=zh    # support zh, en, now.
other_format=flv
stage=0
stop_stage=4

. ./utils/parse_options.sh  ||  exit 1;

ROOT="$(cd "$(dirname "$0")" && pwd)"

audio_dir=$1                               # 原始音频wav/视频mp4路径
output_dir=$2                              # 切分转写筛选后的数据路径
mkdir -p $output_dir
echo "# 转写的音频绝对路径为：$audio_dir"
echo "# 最终的保存音频路径为：$output_dir"

result_dir=$output_dir/whisper_transcript   # 第一遍转写结果路径
segment_dir=$output_dir/whisper_segment     # 切分后音频保存路径
data_dir=$output_dir/data                   # 切分音频kaldi格式数据路径
data_acc95_dir=$data_dir/delins2             # 筛选后kaldi格式数据路径

# convert other format to wav
if [ $stage -le -1 ] && [ ${stop_stage} -ge -1 ]; then
  echo "# 第-1步，转换其他音频的格式，需要指定音频格式: other_format=$other_format"

  find  $audio_dir  -type f \( -name "*.$other_format" \) | awk -F"/"  -v name="" \
    -v root=$audio_dir '{name=$0; gsub(root,"",name); gsub("/","_",name); print name"\t"$0 }' | sort > $output_dir/$other_format.scp

  bash $ROOT/clients/audio/convert2wav.sh $output_dir/$other_format.scp

fi


# prepare wav.scp, find all wav and mp4 files  \( -name "*.wav" -o -name "*.mp4" \)
if [ $stage -le 0 ] && [ ${stop_stage} -ge 0 ]; then
  echo "# 第0.0步, 将转写文件调整格式列到wav.scp文件中"
  find  $audio_dir  -type f  | awk -F"/"  -v name="" \
    -v root=$audio_dir '{name=$0; gsub(root,"",name); gsub("/","_",name); print name"\t"$0 }' > $output_dir/wav.scp
#  echo "# 第0.1步, 去除音频路径中带有的空格，将空格替换成-, 文件名限定在15个字以内"
#  python3 $ROOT/clients/audio/rm_space_in_path.py $output_dir/wav.scp
#  echo "# 第0.2步, 重新把全部转写文件路径列入到wav.scp中"
#  find  $audio_dir  -type f | awk -F"/" -v name="" \
#    -v root=$audio_dir '{name=$0; gsub(root,"",name); gsub("/","_",name);  print name"\t"$0 }' > $output_dir/wav.scp

fi

# whisper transcribe, get segment timestamp and text
# use whisperX, large-v3 model, batch=32 consume ~ 13GB GPU-RAM
if [ $stage -le 1 ] && [ ${stop_stage} -ge 1 ]; then
  echo "# 第1步，使用WhisperX large-v3模型转写。"
  python3 $ROOT/utils/run_whisperX.py  \
      -i  $output_dir/wav.scp \
      -o  $result_dir \
      -g  $gpu_ids  \
      -b  32        \
      -l  $lang

fi

# segment the audio/video with whisper segments
if [ $stage -le 2 ] && [ ${stop_stage} -ge 2 ]; then
  echo "# 第2步，根据转写得到的时间戳对音视频进行切分，得到切分后的wav。"
  python3 $ROOT/utils/segment_whisper_tsv.py  \
    -i  $output_dir/wav.scp \
    -t  $result_dir  \
    -o  $segment_dir  \
    -n  48

fi

# prepare wav.scp, text... find all segments.
if [ $stage -le 3 ] && [ ${stop_stage} -ge 3 ]; then
  mkdir -p $data_dir
  echo "# 第3步，准备转写所需的kaldi格式数据，至少包含wav.scp和text，过滤掉[0.5, 40]s之外的音频段"
  find  $segment_dir  -type f  -name "*.wav" | awk -F"/"  -v name="" \
     '{name=$NF; gsub(".wav","",name); print name"\t"$0 }' | sort > $data_dir/wav.scp
  # cat  $segment_dir/*/transcription.txt | sort > $data_dir/text
  find $segment_dir -name "transcription.txt" -print0 | xargs -0 cat > $data_dir/text
  find  $segment_dir  -type f  -name "*.wav" | awk -F"/"  -v name="" \
     '{name=$NF; gsub(".wav","",name); print name"\t"$(NF-1) }' | sort > $data_dir/utt2spk
  bash $ROOT/utils/wav_to_duration.sh --nj 48 $data_dir/wav.scp  $data_dir/wav2dur

  mkdir -p $data_dir/backup
  mv $data_dir/*  $data_dir/backup
  # 将时长超过40s的音频都过滤掉，是whisper转写结果有问题的音频拼起来时长会比较长。
  cat ${data_dir}/backup/wav2dur | awk '{if($2<=40 && $2>=0.5) print $0}' > ${data_dir}/wav2dur
  for f in wav.scp text utt2spk; do
    perl $ROOT/utils/filter_scp.pl ${data_dir}/wav2dur ${data_dir}/backup/$f > ${data_dir}/$f
  done
  perl $ROOT/utils/utt2spk_to_spk2utt.pl  $data_dir/utt2spk > $data_dir/spk2utt

fi

if [ $stage -le 4 ] && [ ${stop_stage} -ge 4 ]; then
  mkdir -p $data_acc95_dir
  echo "# 第4步，使用Paraformer模型进行转写，并计算CER，筛选出插入错误+删除错误小于2，且CER<=30%的数据"
  bash $ROOT/utils/infer_paraformer.sh  \
      --stage 1  --stop_stage 3  \
      --language  $lang     \
      --gpuid_list $gpu_ids \
      --batch_size 16  \
      $data_dir $data_acc95_dir

fi
