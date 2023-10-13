#!/bin/bash 
scp=tobe_seg.scp
nj=64

mkdir -p split${nj}
split_scps=""
for n in $(seq ${nj}); do
  split_scps="${split_scps} split${nj}/wav.${n}.scp"
done
../python/split_scp.pl ${scp} ${split_scps}


for n in $(seq ${nj}); do
{
for x in `awk '{print $2}' split${nj}/wav.${n}.scp `; do   
    echo $x;  
    name=`echo $x | awk -F".wav" '{print $1}'`;  
    path=$(dirname $x); 
    echo segment $path; 
    ffmpeg -i $x -f segment  -segment_time 3600 $path/segment_%02d.wav ;
done

} &
done
wait