#!/bin/bash
# convert flv to wav

for x in `find . -name "*.flv"` ; do 
    echo $x ; 
    path=$(dirname "$(realpath "$x")"); 
    echo $path; 
    file=$(basename $x .flv); 
    echo $file; 
    ffmpeg -i $x -ac 1 -ar 16000 -acodec pcm_s16le $path/$file.wav; 
done