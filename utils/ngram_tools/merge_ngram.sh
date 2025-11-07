#!/bin/bash

. ./path.sh || exit 1;

general_ngram=data/ngram/lm_250G_3gram+YouLing3_3gram_chars/local/lm/lm.arpa

domain_lm_name=ngram/lm_YouLing
domain_ngram=data/$domain_lm_name/local/lm/lm.arpa
domain_text_list=data/youling/train_farYL+nearYL/lm.list

merged_lm_name=ngram/lm_250G_3gram+YouLing_3gram_chars
merged_ngram=data/${merged_lm_name}/local/lm/lm.arpa

dict=data/$domain_lm_name/local/dict/word.vocab
dev_text=data/lm_dev.txt

general_ngram_prune=2e-8
domain_ngram_prune=1e-12
merge_ngram_prune=1e-12

general_order=3
domain_order=3
merged_order=3

merged_dir=`dirname $merged_ngram`
merged_name=`basename $merged_ngram`
mkdir -p $merged_dir

dict_path=`dirname $dict`

stage=3

#生成垂域语言模型
if [ $stage -le -2 ]; then
  if [ ! -f $domain_ngram ] && [ -f $domain_text_list ] ; then
    echo "-2. make a domain ngram. with $domain_text_list, to data/$domain_lm_name"
    ./run_ngram.sh --lm_corpus_paths $domain_text_list --order $domain_order --prune $domain_ngram_prune \
      --chinese_unit chars  --LM_name $domain_lm_name  0  2
    dict_path=data/$domain_lm_name/local/dict
  fi
fi

#对通用语言模型进行裁剪
if [ $stage -le -1 ]; then
  if [ ! -z $general_ngram_prune ]; then
    prune_dir=`dirname $general_ngram`
    prune_name=lm_prune${general_ngram_prune}.arpa
    if [ ! -f $prune_dir/$prune_name ];then
      echo "-1. prune $general_ngram with $general_ngram_prune, to $prune_dir/$prune_name"
      ngram -debug 1 -lm $general_ngram -order $general_order -prune ${general_ngram_prune} -write-lm $prune_dir/$prune_name
    fi
    general_ngram=$prune_dir/$prune_name
  fi
fi

if [ $stage -le 0 ]; then
  echo "0. get the merge factor. "
ngram -debug 2 -order $general_order -lm $general_ngram -ppl $dev_text > $merged_dir/lm1.ppl
ngram -debug 2 -order $domain_order -lm $domain_ngram -ppl $dev_text > $merged_dir/lm2.ppl
compute-best-mix $merged_dir/lm1.ppl $merged_dir/lm2.ppl > $merged_dir/best-mix.ppl
fi

if [ $stage -le 1 ]; then
echo "1. merge the ngrams."
lambda=`tail -n 1 $merged_dir/best-mix.ppl | awk '{print $NF}' | awk -F")" '{print $1}'`
echo "best mix lambda = $lambda"
ngram -debug 1 -order $merged_order -lm $domain_ngram -lambda $lambda -mix-lm $general_ngram \
    -write-lm $merged_ngram -vocab $dict -limit-vocab
fi


if [ $stage -le 2 ]; then
  echo "2. Eval the merged ngram"
if [ ! -z $merge_ngram_prune ] ; then
  echo  "prune the merged ngram with $merge_ngram_prune, to $merged_dir/prune${merge_ngram_prune}_$merged_name "
  ngram -debug 1 -lm $merged_ngram -order $merged_order -prune $merge_ngram_prune \
      -write-lm  $merged_dir/prune${merge_ngram_prune}_$merged_name
  mv $merged_ngram ${merged_ngram}0
  mv $merged_dir/prune${merge_ngram_prune}_$merged_name $merged_ngram
fi

  ngram -debug 2 -order $merged_order -lm $merged_ngram -ppl $dev_text > $merged_dir/lm_merge.ppl

fi

if [ ${stage} -le 3 ] && [ 1 -eq 1 ]; then
  echo
  echo "3. Build decoding TLG, convert arpa to fst"
  echo
  lm_path=data/$merged_lm_name/local/lm   # the dir to store lm.arpa
# some dir needed when compile fst
tmp_path=data/$merged_lm_name/local/tmp
lang_path=data/$merged_lm_name/local/lang
fst_path=data/$merged_lm_name/lang_test
  tools/fst/compile_lexicon_token_fst.sh  $dict_path $tmp_path $lang_path
  tools/fst/make_tlg.sh $lm_path $lang_path $fst_path || exit 1;
fi

echo "over" # 表示脚本运行结束