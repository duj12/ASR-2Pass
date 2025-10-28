# workdir is always websocket
build=build  # the build dir

# Build websocket service, with onnxruntime
if [ ! -f $build/bin/funasr-wss-server ]; then 
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
vad_dir="damo/speech_fsmn_vad_zh-cn-16k-common-onnx"
model_dir="damo/speech_paraformer-large_asr_nat-en-16k-common-vocab10020-onnx"
punc_dir="damo/punc_ct-transformer_cn-en-common-vocab471067-large-onnx"
lm_dir="damo/speech_ngram_lm_zh-cn-ai-wesp-fst"
hotword="$(pwd)/hotwords.txt"

decoder_thread_num=16
io_thread_num=4
port=10098
quantize=true
certfile="../ssl_key/server.crt"
keyfile="../ssl_key/server.key"

. ./parse_options.sh || exit 1;


$build/bin/funasr-wss-server  \
  --download-model-dir ${download_model_dir} \
  --model-dir ${model_dir} \
  --quantize $quantize  \
  --vad-dir ${vad_dir} \
  --punc-dir ${punc_dir} \
  --itn-dir ""  \
  --decoder-thread-num ${decoder_thread_num} \
  --io-thread-num  ${io_thread_num} \
  --port ${port} \
  --certfile  "" \
  --keyfile ""  \
  --lm-dir "${lm_dir}" \
  --hotword "${hotword}" 

