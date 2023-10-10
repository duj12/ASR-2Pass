#!/bin/bash

# the multithread in wss_client is not stable, 
# so we split the scp first and then use multiple 
# wss_clients to decode simultaneously.
nj=16
host=127.0.0.1
port=10097  # default offline server 
mode=offline
scp=    # total input scp
dir=    # output dir


. ../../websocket/parse_options.sh  || exit 1;

mkdir -p $dir/split${nj}
split_scps=""
for n in $(seq ${nj}); do
  split_scps="${split_scps} ${dir}/split${nj}/wav.${n}.scp"
done
./split_scp.pl ${scp} ${split_scps}

for n in $(seq ${nj}); do
{
  python funasr_wss_client.py \
    --host $host \
    --port $port \
    --mode $mode \
    --audio_in  ${dir}/split${nj}/wav.${n}.scp \
    --output_dir $dir \
    --thread_num 1
} &
done
wait