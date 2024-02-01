#!/usr/bin/env bash

set -e
set -u
set -o pipefail

stage=1
stop_stage=3
batch_size=32
language=zh
gpu_inference=true    # whether to perform gpu decoding
model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
gpuid_list="0,1,2,3,4,5,6,7"    # set gpus, e.g., gpuid_list="0,1"
njob=32    # the number of jobs for CPU decoding, if gpu_inference=false, use CPU decoding, please set njob

. utils/parse_options.sh || exit 1;

data_dir=$1
filter_dir=$2
output_dir="$data_dir/result"

if ${language} == "zh"; then
    model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
elif ${language} == "en"; then
    model="damo/speech_paraformer-large-vad-punc_asr_nat-en-16k-common-vocab10020"
else
    echo "language = $language, not support yet."
    exit 1
fi

if ${gpu_inference} == "true"; then
    nj=$(echo $gpuid_list | awk -F "," '{print NF}')
else
    nj=$njob
    batch_size=1
    gpuid_list=""
    for JOB in $(seq ${nj}); do
        gpuid_list=$gpuid_list"-1,"
    done
fi

mkdir -p $output_dir/split
split_scps=""
for JOB in $(seq ${nj}); do
    split_scps="$split_scps $output_dir/split/wav.$JOB.scp"
done
perl utils/split_scp.pl ${data_dir}/wav.scp ${split_scps}

if [ $stage -le 1 ] && [ $stop_stage -ge 1 ];then
    echo "Decoding ..."
    gpuid_list_array=(${gpuid_list//,/ })
    for JOB in $(seq ${nj}); do
        {
        id=$((JOB-1))
        gpuid=${gpuid_list_array[$id]}
        mkdir -p ${output_dir}/output.$JOB
        python utils/infer_paraformer.py \
            --model ${model} \
            --audio_in ${output_dir}/split/wav.$JOB.scp \
            --output_dir ${output_dir}/output.$JOB \
            --batch_size ${batch_size} \
            --gpuid ${gpuid}
        }&
    done
    wait

    mkdir -p ${output_dir}/1best_recog
    for f in token score text; do
        if [ -f "${output_dir}/output.1/1best_recog/${f}" ]; then
          for i in $(seq "${nj}"); do
              cat "${output_dir}/output.${i}/1best_recog/${f}"
          done | sort -k1 >"${output_dir}/1best_recog/${f}"
        fi
    done
fi

if [ $stage -le 2 ] && [ $stop_stage -ge 2 ];then
    if [ -f ${data_dir}/text_whiper ] ;then
      mv ${data_dir}/text_whiper ${data_dir}/text
    fi
    echo "SpeechIO TIOBE textnorm"
    echo "$0 --> Normalizing REF text ..."
    python3 ./utils/textnorm_zh.py \
        --has_key --to_lower \
        ${data_dir}/text \
        ${output_dir}/1best_recog/ref.txt

    echo "$0 --> computing WER/CER and alignment ..."

    python3 ./utils/compute-wer.py --char=1 --v=1 \
        ${output_dir}/1best_recog/ref.txt \
        ${output_dir}/1best_recog/text > \
        ${output_dir}/1best_recog/wer.txt
    awk '/utt:/ { utt=$2 } /WER:/ { print utt, $2 }' \
        ${output_dir}/1best_recog/wer.txt > \
        ${data_dir}/utt2wer

fi

if [ $stage -le 3 ] && [ $stop_stage -ge 3 ];then
    echo "Filter utt whose WER <= 5% ..."
    mkdir -p ${filter_dir}
    cat ${data_dir}/utt2wer | awk '{if($2<=5) print $0}' > ${filter_dir}/utt2wer
    # use the recognized text as text pseudo label. 避免Whisper的正则文本和实际发音不一致。
    if [ ! -f ${data_dir}/text_whiper ] ;then
      mv ${data_dir}/text ${data_dir}/text_whiper
    fi
    python3 ./utils/remove_space_between_chinese.py ${output_dir}/1best_recog/text ${data_dir}/text 1
    for file_name in wav.scp text; do
      perl utils/filter_scp.pl  ${filter_dir}/utt2wer ${data_dir}/$file_name > ${filter_dir}/$file_name
    done
    if [ -f ${data_dir}/wav2dur ]; then
      perl utils/filter_scp.pl  ${filter_dir}/utt2wer ${data_dir}/wav2dur > ${filter_dir}/wav2dur
      dur_ori=`cat ${data_dir}/wav2dur | awk -v total=0.0 '{total+=$2 } END{print total/3600}'`
      dur=`cat ${filter_dir}/wav2dur | awk -v total=0.0 '{total+=$2 } END{print total/3600}'`
      echo "Total duration $dur_ori hours, WER<=5% duration $dur hours."
    fi
    if [ -f ${data_dir}/utt2spk ]; then
      perl utils/filter_scp.pl  ${filter_dir}/utt2wer ${data_dir}/utt2spk > ${filter_dir}/utt2spk
      perl utils/utt2spk_to_spk2utt.pl ${filter_dir}/utt2spk > ${filter_dir}/spk2utt
    fi

fi
