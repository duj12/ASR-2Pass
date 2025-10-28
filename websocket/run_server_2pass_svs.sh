# workdir is always websocket
build=build  # the build dir

# Build websocket service, with onnxruntime
if [ ! -f $build/bin/funasr-wss-server-2pass ]; then
  echo "1st time run, we need to build the server, which may take a while."
  apt-get update && apt-get install -y libopenblas-dev libssl-dev cmake build-essential

  if [ ! -d ffmpeg-N-111383-g20b8688092-linux64-gpl-shared ]; then
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


download_model_dir="models"
# now the hotword model and timestamp model is two different model
# you can choose the following 3 model to use which you want, by comment the others.
# model_dir="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-onnx"            # offline base model
# model_dir="damo/speech_paraformer-large-contextual_asr_nat-zh-cn-16k-common-vocab8404-onnx" # hotword model
# model_dir="damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx"   # timestamp model and hotword
model_dir="iic/SenseVoiceSmall-onnx" 
# the online model is better to use the small one, if you want to use the large, comment the small model line.
# online_model_dir="damo/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8404-online-onnx"        # small online model
online_model_dir="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx"  # large online model
vad_dir="damo/speech_fsmn_vad_zh-cn-16k-common-onnx"
# punc_dir="damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx"                # online punc model
punc_dir="damo/punc_ct-transformer_zh-cn-common-vocab272727-onnx"                             # offline punc model
itn_dir="thuduj12/fst_itn_zh"
lm_dir="damo/speech_ngram_lm_zh-cn-ai-wesp-fst"
hotword="$(pwd)/hotwords.txt"

decoder_thread_num=16
io_thread_num=4
port=10096
quantize=true
certfile="../ssl_key/server.crt"
keyfile="../ssl_key/server.key"

. ./parse_options.sh || exit 1;


$build/bin/funasr-wss-server-2pass  \
  --download-model-dir ${download_model_dir} \
  --model-dir ${model_dir} \
  --online-model-dir ${online_model_dir}  \
  --quantize $quantize  \
  --vad-dir ${vad_dir} \
  --punc-dir ${punc_dir} \
  --itn-dir ${itn_dir}  \
  --decoder-thread-num ${decoder_thread_num} \
  --io-thread-num  ${io_thread_num} \
  --port ${port} \
  --certfile  "" \
  --keyfile ""  \
  --lm-dir "${lm_dir}" \
  --hotword "${hotword}" 

