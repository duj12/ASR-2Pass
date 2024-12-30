# workdir is always websocket
build=build  # the build dir

# Build websocket service, with onnxruntime
echo "================1st time run, we need to build the server, which may take a while."
apt-get update && apt-get install -y libopenblas-dev libssl-dev cmake build-essential

if [ ! -d ffmpeg-N-111383-g20b8688092-linux64-gpl-shared ]; then
  bash ../onnxruntime/third_party/download_ffmpeg.sh
fi
if [ ! -d onnxruntime-linux-x64-1.14.0 ]; then
  bash ../onnxruntime/third_party/download_onnxruntime.sh
fi

echo "================build begin..."

# we build the server under "build" dir.
cmake -DONNXRUNTIME_DIR=`pwd`/onnxruntime-linux-x64-1.14.0 \
  -DFFMPEG_DIR=`pwd`/ffmpeg-N-111383-g20b8688092-linux64-gpl-shared \
  -B $build
cmake --build $build


echo "================build finished!"