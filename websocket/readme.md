# websocket服务构建
```shell
build=build  # the build dir

# Build websocket service, with onnxruntime
if [ ! -f $build/bin/funasr-wss-server-2pass ]; then 
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

```

# 服务端参数配置
```text
--download-model-dir 模型下载地址，在以下模型路径无法获取的时候，从modelscope下载
--model-dir  非流式识别ASR模型路径
--online-model-dir  流式识别ASR模型路径
--quantize  True为量化ASR模型，False为非量化ASR模型，默认是True
--vad-dir  VAD模型路径
--vad-quant   True为量化VAD模型，False为非量化VAD模型，默认是True
--punc-dir  标点模型路径
--punc-quant   True为量化PUNC模型，False为非量化PUNC模型，默认是True
--itn-model-dir 文本反正则模型的路径
--port  服务端监听的端口号，默认为 10095
--decoder-thread-num  服务端启动的推理线程数，默认为 8，可配置为核数，或者核数的2倍。
--io-thread-num  服务端启动的IO线程数，默认为 1，可以配置为核数的1/4。
--certfile  ssl的证书文件，默认为：../../../ssl_key/server.crt，如需关闭，设置为""
--keyfile   ssl的密钥文件，默认为：../../../ssl_key/server.key，如需关闭，设置为""

```