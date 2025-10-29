# 核心代码构建

```shell
build=build  # the build dir

# we build the server under "build" dir.
cmake -DONNXRUNTIME_DIR=`pwd`/../websocket/onnxruntime-linux-x64-1.14.0 \
  -DFFMPEG_DIR=`pwd`/../websocket/ffmpeg-N-111383-g20b8688092-linux64-gpl-shared \
  -B $build
cmake --build $build

```