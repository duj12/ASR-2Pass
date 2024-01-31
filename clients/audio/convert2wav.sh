#!/bin/bash
# convert flv to wav
scp=$1
nj=64

scp_dir=$(dirname $scp)
split_dir=$scp_dir/split${nj}

mkdir -p $split_dir
split_scps=""
for n in $(seq ${nj}); do
  split_scps="${split_scps} $split_dir/wav.${n}.scp"
done
perl utils/split_scp.pl ${scp} ${split_scps}


for n in $(seq ${nj}); do
{
  for x in `awk '{print $2}' $split_dir/wav.${n}.scp ` ; do
    echo $x ; 
    name=$(basename $x)
    name=`echo $name | awk -F "." '{print $1}'`;
    path=$(dirname $x);
    ffmpeg -i $x -ac 1 -ar 24000 -acodec pcm_s16le $path/$name.wav;
    # convert and segment
    # ffmpeg -i "$x" -ac 1 -ar 24000 -acodec pcm_s16le -f segment \
    # -segment_time 3600 - | ffmpeg -i - -ac 1 -ar 24000 -acodec pcm_s16le "$path/${name}_%02d.wav"

  done

} &
done
wait