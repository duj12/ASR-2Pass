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
mkdir -p ${filter_dir}
output_dir="$data_dir/result"

if [ ${language} == "zh" ]; then
    model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
elif [ ${language} == "en" ]; then
    model="iic/speech_paraformer_asr-en-16k-vocab4199-1B-pytorch"
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
    if [ ! -f ${output_dir}/1best_recog/ref.txt ] ; then
      if [ ${language} == "zh" ]; then
        echo "$0 --> Normalizing REF text ..."
        python3 ./utils/textnorm_zh.py \
          --has_key --to_lower \
          ${data_dir}/text \
          ${output_dir}/1best_recog/ref.txt
      else
        cp ${data_dir}/text ${output_dir}/1best_recog/ref.txt
      fi
    fi
    echo "$0 --> computing WER/CER and alignment ..."

#    python3 ./utils/compute-wer.py --char=1 --v=1 \
#        ${output_dir}/1best_recog/ref.txt \
#        ${output_dir}/1best_recog/text > \
#        ${output_dir}/1best_recog/wer.txt
    bash ./utils/mp_compute_wer.sh  \
        ${output_dir}/1best_recog/ref.txt \
        ${output_dir}/1best_recog/text \
        ${output_dir}/1best_recog/wer.txt

fi

if [ $stage -le 3 ] && [ $stop_stage -ge 3 ];then
    echo "Filter utt whose WER <= 30% ..."
    awk '/utt:/ { utt=$2 } /WER:/ { print utt, $2 }' \
        ${output_dir}/1best_recog/wer.txt > \
        ${data_dir}/utt2wer
    mkdir -p ${filter_dir}
    cat ${data_dir}/utt2wer | awk '{if($2<=30) print $0}' > ${filter_dir}/utt2wer
    # WER 的结果只能反应两个识别模型的一致性，不能很好地反映音频质量。
    # 可以直接通过插入和删除的数量(不超过2个字/词)去筛选数据。替换错误往往是同音字。
    echo "Filter utt whose Deletion and Insertion Error less than 2 ..."
    awk -F '[= ]' '/utt:/ { utt=$2 } /WER:/ { del=$11; ins=$13; print(utt"\t"del+ins) }' \
        ${output_dir}/1best_recog/wer.txt > \
        ${data_dir}/utt2delins
    cat ${data_dir}/utt2delins | awk '{if($2<=2) print $0}' > ${filter_dir}/utt2delins0

    # 因为Whisper对英文语音指定解码中文时会自动翻译结果，导致WER结果可能出现S很大，D+I很小的情况， 这里直接限制WER本身不要超过一定数值。
    echo "Filter utt whose D+I <=2 and WER<=30%. "
    perl utils/filter_scp.pl  ${filter_dir}/utt2delins0 ${filter_dir}/utt2wer > ${filter_dir}/utt2delins

    # use the recognized text as text pseudo label. 避免Whisper的正则文本和实际发音不一致。
    if [ ! -f ${data_dir}/text_whiper ] ;then
      mv ${data_dir}/text ${data_dir}/text_whiper
    fi
    python3 ./utils/remove_space_between_chinese.py ${output_dir}/1best_recog/text ${data_dir}/text 1
    for file_name in wav.scp text; do
      perl utils/filter_scp.pl  ${filter_dir}/utt2delins ${data_dir}/$file_name > ${filter_dir}/$file_name
    done
    if [ -f ${data_dir}/wav2dur ]; then
      perl utils/filter_scp.pl  ${filter_dir}/utt2delins ${data_dir}/wav2dur > ${filter_dir}/wav2dur
      dur_ori=`cat ${data_dir}/wav2dur | awk -v total=0.0 '{total+=$2 } END{print total/3600}'`
      dur=`cat ${filter_dir}/wav2dur | awk -v total=0.0 '{total+=$2 } END{print total/3600}'`
      echo "Total duration $dur_ori hours, WER<=5% duration $dur hours."
    fi
    if [ -f ${data_dir}/utt2spk ]; then
      perl utils/filter_scp.pl  ${filter_dir}/utt2delins ${data_dir}/utt2spk > ${filter_dir}/utt2spk
      perl utils/utt2spk_to_spk2utt.pl ${filter_dir}/utt2spk > ${filter_dir}/spk2utt
    fi

    # 对文本筛完的数据，计算DNSMOS值
    python utils/dnsmos_local.py -i $filter_dir/wav.scp -o $filter_dir/utt2mos


fi
