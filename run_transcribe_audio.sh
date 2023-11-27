#!/usr/bin/bash

ASR2PASS_ROOT="$(cd "$(dirname "$0")" && pwd)"

audio_dir=$1
echo "# 转写的音频绝对路径为：$audio_dir"

if [ "$#" -gt 2 ]; then
  stage="$2"
fi


result_dir=$audio_dir/ASR_result
if [ -d $result_dir ]; then
  echo "# 转写结果路径$result_dir已存在，先删除再重新创建"
  sudo rm -rf $result_dir
fi

echo "# 转写文本保存绝对路径为：$result_dir"
sudo mkdir -p $result_dir

if [ $stage -le 2 ]; then
# step one:
echo "# 第2.0步, 将转写文件调整格式列到wav.scp文件中"
find  $audio_dir  -type f | awk -F"/" -v name="" -v root=$audio_dir '{name=$0; gsub(root,"",name); gsub("/","_",name); print name"\t"$0 }' | sort > wav.scp
echo "# 第2.1步, 去除音频路径中带有的空格，将空格替换成-"
python $ASR2PASS_ROOT/clients/audio/rm_space_in_path.py wav.scp
echo "# 第2.2步, 重新把全部转写文件路径列入到wav.scp中"
find  $audio_dir  -type f | awk -F"/" -v name="" -v root=$audio_dir '{name=$0; gsub(root,"",name); gsub("/","_",name);  print name"\t"$0 }' | sort > wav.scp

total_files=`wc -l wav.scp | awk '{print $1}'`
echo "# 全部待转写文件数量为： $total_files"
fi

if [ $stage -le 3 ]; then 
# step three:
echo "# 第3步, 确保配置有python环境, 开始转写..."
cd $ASR2PASS_ROOT/clients/python
pip install -r requirements_client.txt

cpu_num=$((`python -c "import os; print(os.cpu_count())"`))
thread_num=$((cpu_num / 2))
if ((total_files > thread_num)); then
  thread_num=$thread_num
else
  thread_num=$total_files
fi

python funasr_wss_client.py \
    --host 127.0.0.1 --port 10097 --mode offline \
    --audio_in $ASR2PASS_ROOT/wav.scp \
    --output_dir $result_dir \
    --thread_num $thread_num 

echo
echo "转写结束，可以回到服务端窗口，按Ctrl+C退出服务端，下次需要转写时再重新启动服务端。"
echo "再见。"
fi