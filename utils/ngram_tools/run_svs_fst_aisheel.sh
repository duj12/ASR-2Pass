chmod +x fst/*
[ -f path.sh ] && . ./path.sh
stage=$1 
stop_stage=$2

if [ $stage -le 0 ] && [ $stop_stage -ge 0 ] ; then
    echo "Stage 0: Prepare LM data and train LM, use Aishell corpus as example"
    # download train corpus and lexicon
    wget https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/requirements/lm.tar.gz
    tar -zxvf lm.tar.gz
    # train lm, make sure that srilm is installed
    bash fst/train_lms.sh
fi


if [ $stage -le 1 ] && [ $stop_stage -ge 1 ] ; then
    echo "Stage 1: Generate lexicon for SenseVoiceSmall model"
    # generate lexicon, use sensevoice's token and sentencepiece model
    wget https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/tokens.json -O lm/tokens.json
    wget https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/chn_jpn_yue_eng_ko_spectok.bpe.model -O lm/chn_jpn_yue_eng_ko_spectok.bpe.model
    python3 fst/generate_lexicon_svs.py lm/corpus.dict lm/tokens.json  lm/chn_jpn_yue_eng_ko_spectok.bpe.model lm/lexicon.out lm/units.txt lm/units.json
fi

if [ $stage -le 2 ] && [ $stop_stage -ge 2 ] ; then
    echo "Stage 2: Compile FSTs and make decoding graph for SenseVoiceSmall model, use compact-CTC as topology"
    # Compile the lexicon and token FSTs
    fst/compile_dict_token.sh  lm lm/tmp lm/lang

    # Compile the language-model FST and the final decoding graph TLG.fst
    fst/make_decode_graph.sh lm lm/lang || exit 1;

    # Collect resource files required for decoding
    fst/collect_resource_file.sh lm lm/resource
    cp lm/lexicon.out lm/resource/lexicon.txt
    cp lm/units.json lm/resource/units.json
    
fi
