#!/usr/bin/env bash

set -e
set -u
set -o pipefail

stage=3
stop_stage=3
model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"

#for subset in test_aishell test_net test_meeting test_conv test_libriclean test_giga test_talcs test_htrs462 test_sjtcs test_yl test_yg; do
for subset in data_mp4; do

data_dir="$subset"
output_dir="$subset/result"
batch_size=32
gpu_inference=true    # whether to perform gpu decoding
gpuid_list="0,1,2,3,4,5,6,7"    # set gpus, e.g., gpuid_list="0,1"
njob=32    # the number of jobs for CPU decoding, if gpu_inference=false, use CPU decoding, please set njob
checkpoint_dir=
checkpoint_name="valid.acc.ave.pb"

. utils/parse_options.sh || exit 1;

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

if [ -n "${checkpoint_dir}" ]; then
  python utils/prepare_checkpoint.py ${model} ${checkpoint_dir} ${checkpoint_name}
  model=${checkpoint_dir}/${model}
fi

if [ $stage -le 1 ] && [ $stop_stage -ge 1 ];then
    echo "Decoding ..."
    gpuid_list_array=(${gpuid_list//,/ })
    for JOB in $(seq ${nj}); do
        {
        id=$((JOB-1))
        gpuid=${gpuid_list_array[$id]}
        mkdir -p ${output_dir}/output.$JOB
        python infer.py \
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
    echo "SpeechIO TIOBE textnorm"
    echo "$0 --> Normalizing REF text ..."
    ./utils/textnorm_zh.py \
        --has_key --to_lower \
        ${data_dir}/text \
        ${output_dir}/1best_recog/ref.txt

#    echo "$0 --> Normalizing HYP text ..."
#    ./utils/textnorm_zh.py \
#        --has_key --to_lower \
#        ${output_dir}/1best_recog/text.proc \
#        ${output_dir}/1best_recog/rec.txt

#    grep -v $'\t$' ${output_dir}/1best_recog/rec.txt > ${output_dir}/1best_recog/rec_non_empty.txt

    echo "$0 --> computing WER/CER and alignment ..."
#    ./utils/error_rate_zh \
#        --tokenizer char \
#        --ref ${output_dir}/1best_recog/ref.txt \
#        --hyp ${output_dir}/1best_recog/rec_non_empty.txt \
#        ${output_dir}/1best_recog/DETAILS.txt | tee ${output_dir}/1best_recog/RESULTS.txt
#     rm -rf ${output_dir}/1best_recog/rec.txt ${output_dir}/1best_recog/rec_non_empty.txt
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
    filter_dir=${data_dir}/acc95
    mkdir -p ${filter_dir}
    cat ${data_dir}/utt2wer | awk '{if($2<=5) print $0}' > ${filter_dir}/utt2wer
    # use the recognized text as text pseudo label. 避免Whisper的正则文本和实际发音不一致。
    if [ ! -f ${data_dir}/text_whiper ] ;then
      mv ${data_dir}/text ${data_dir}/text_whiper
    fi
    python3 ./utils/remove_space_between_chinese.py ${output_dir}/1best_recog/text ${data_dir}/text 1
    for file_name in wav.scp text; do
      utils/filter_scp.pl  ${filter_dir}/utt2wer ${data_dir}/$file_name > ${filter_dir}/$file_name
    done
    if [ -f ${data_dir}/wav2dur ]; then
      utils/filter_scp.pl  ${filter_dir}/utt2wer ${data_dir}/wav2dur > ${filter_dir}/wav2dur
      dur_ori=`cat ${data_dir}/wav2dur | awk -v total=0.0 '{total+=$2 } END{print total/3600}'`
      dur=`cat ${filter_dir}/wav2dur | awk -v total=0.0 '{total+=$2 } END{print total/3600}'`
      echo "Total duration $dur_ori hours, WER<=5% duration $dur hours."
    fi

fi

#if [ $stage -le 3 ] && [ $stop_stage -ge 3 ];then
#    echo "Computing WER ..."
#    cp ${output_dir}/1best_recog/text ${output_dir}/1best_recog/text.proc
#    cp ${data_dir}/text ${output_dir}/1best_recog/text.ref
#    python utils/compute_wer.py ${output_dir}/1best_recog/text.ref ${output_dir}/1best_recog/text.proc ${output_dir}/1best_recog/text.cer
#    tail -n 3 ${output_dir}/1best_recog/text.cer
#fi


done