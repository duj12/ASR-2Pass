#!/usr/bin/bash

ASR2PASS_ROOT="$(cd "$(dirname "$0")" && pwd)"

sudo apt-get update && sudo apt-get install -y libopenblas-dev libssl-dev cmake build-essential

echo "# 第1步, 编译并启动转写服务"
cd $ASR2PASS_ROOT/websocket
build=build  # the build dir
if [ ! -f $build/bin/funasr-wss-server ]; then 
  echo "    第一次启动转写服务，需要编译，需要花费几分钟时间."
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
  echo "   转写服务端编译完毕。"
fi

bash ./run_server_offline.sh --itn-dir none 


