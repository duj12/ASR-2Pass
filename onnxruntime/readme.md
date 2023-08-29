# 核心代码构建

```shell
build=build  # the build dir

# Build onnxruntime
  if [ ! -d ffmpeg-N-111383-g20b8688092-linux64-gpl-shared ]; then
    bash third_party/download_ffmpeg.sh
  fi
  if [ ! -d onnxruntime-linux-x64-1.14.0 ]; then 
    bash third_party/download_onnxruntime.sh
  fi

  # we build the server under "build" dir.
  cmake -DONNXRUNTIME_DIR=`pwd`/onnxruntime-linux-x64-1.14.0 \
    -DFFMPEG_DIR=`pwd`/ffmpeg-N-111383-g20b8688092-linux64-gpl-shared \
    -B $build
  cmake --build $build

```