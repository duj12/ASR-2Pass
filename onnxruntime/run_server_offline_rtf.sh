# workdir is always websocket
build=build  # the build dir

# Build websocket service, with onnxruntime
if [ ! -f $build/bin/funasr-onnx-offline-rtf ]; then 
  echo "1st time run, we need to build the server, which may take a while(especially when fetch from git)."

  if [ -d ../websocket/ffmpeg-N-111383-g20b8688092-linux64-gpl-shared ] && [ -d ../websocket/onnxruntime-linux-x64-1.14.0 ]; then 
    # we build the server under "build" dir.
    cmake -DONNXRUNTIME_DIR=`pwd`/../websocket/onnxruntime-linux-x64-1.14.0 \
      -DFFMPEG_DIR=`pwd`/../websocket/ffmpeg-N-111383-g20b8688092-linux64-gpl-shared \
      -B $build
    cmake --build $build
  else 
    if [ ! -d ffmpeg-N-111383-g20b8688092-linux64-gpl-shared ] ; then
      bash ../onnxruntime/third_party/download_ffmpeg.sh
    fi
    if [ ! -d onnxruntime-linux-x64-1.14.0 ]; then 
      bash ../onnxruntime/third_party/download_onnxruntime.sh
    fi

    # we build the server under "build" dir.
    cmake -DONNXRUNTIME_DIR=`pwd`/onnxruntime-linux-x64-1.14.0 \
      -DFFMPEG_DIR=`pwd`/ffmpeg-N-111383-g20b8688092-linux64-gpl-shared \
      -B $build
    cmake --build $build

  fi 
fi


# now the hotword model and timestamp model is two different model
# you can choose the following 3 model to use which you want, by comment the others.
model_dir="../websocket/models/damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-onnx"            # offline base model
#model_dir="../websocket/models/damo/speech_paraformer-large-contextual_asr_nat-zh-cn-16k-common-vocab8404-onnx" # hotword model
#model_dir="../websocket/models/damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx"   # timestamp model
online_model_dir="../websocket/models/damo/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8404-online-onnx"
vad_dir="../websocket/models/damo/speech_fsmn_vad_zh-cn-16k-common-onnx"
punc_dir="../websocket/models/damo/punc_ct-transformer_zh-cn-common-vocab272727-onnx"
itn_dir="../websocket/models/damo/fst_itn_zh"
decoder_thread_num=1
onnx_thread_num=1

wav_path=../clients/audio/xmov.wav
asr_mode=2pass
quantize=true

. ../websocket/parse_options.sh || exit 1;

# Since this model is not released by damo, we choose to download it here
if [ ! -d $itn_dir ]; then 
  git clone https://www.modelscope.cn/thuduj12/fst_itn_zh.git $itn_dir
fi

$build/bin/funasr-onnx-offline-rtf  \
  --model-dir ${model_dir} \
  --quantize $quantize  \
  --vad-dir ${vad_dir} \
  --vad-quant true  \
  --punc-dir ${punc_dir} \
  --punc-quant true   \
  --thread-num ${decoder_thread_num} \
  --wav-path  ${wav_path} 

