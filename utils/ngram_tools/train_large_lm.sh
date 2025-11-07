#!/bin/bash
stage=1
stop_stage=3

tmp_fifofile="/tmp/$$.fifo"
mkfifo $tmp_fifofile   # 新建一个FIFO类型的文件
exec 6<>$tmp_fifofile  # 将FD6指向FIFO类型
rm $tmp_fifofile  #删也可以，

thread_num=16  # 定义最大线程数

# To be run from one directory above this script.
. ./path.sh

text=$1  # text file paths, split the large corpus to sub-text files.
lexicon=$2  # lexicon: split each word to bpe units.
order=$3
prune=$4
dir=$5
mkdir -p $dir
countdir=$dir/counts
if [ ! -d $countdir ]; then
	mkdir $countdir
fi


if [ $# -ge 6 ]; then
thread_num=$6
echo "thread_num: $thread_num"
fi

tmp_path=tmp
if [ $# -ge 7 ]; then
tmp_path=$7
echo "the discount dir is $tmp_path"
fi

#根据线程总数量设置令牌个数
#事实上就是在fd6中放置了$thread_num个回车符
for ((i=0;i<${thread_num};i++));do
    echo
done >&6


for f in "$text" "$lexicon"; do
  [ ! -f $x ] && echo "$0: No such file $f" && exit 1;
done

# Check SRILM tools
if ! which ngram-count > /dev/null; then
    echo "srilm tools are not found, please download it and install it from: "
    echo "http://www.speech.sri.com/projects/srilm/download.html"
    echo "Then add the tools to your PATH"
    exit 1
fi

if [ ${stage} -le 1 ] && [ ${stop_stage} -ge 1 ]; then
#2：对每个文本统计词频，将统计的词频结果存放在counts目录下
echo "Get word counts frequency of each file in ${text}"

##其中filepath.txt为切分文件的全路径，可以用命令实现：ls $(echo $PWD)/* > filepath.txt
 ## make-batch-counts $text $thread_num cat $dir/counts -order $order

#上面make-batch-counts执行时，是将多个文件同时读取之后，统计成一个词频文件，并不是多个文件并行生成多个词频
# 下面使用多线程实现并行

for text_path in `cat $text` ; do
  read -u6
  {
    name=`basename $text_path`
    newfile=$countdir/$name.ngrams.gz

# avoid including $datafiles on command line to avoid length limit
cat <<EOF >&2
counting in $newfile sources $text_path
EOF

    cat $text_path | \
      ngram-count -text - \
        -tag $newfile \
        -sort \
        -write-order 0 \
        -write $newfile \
        -order $order

    echo >&6 # 当进程结束以后，再向FD6中加上一个回车符，即补上了read -u6减去的那个
  } &
done
wait

fi

if [ ${stage} -le 2 ] && [ ${stop_stage} -ge 2 ]; then
#3：合并counts文本并压缩, 生成.ngram.gz后缀的文件
echo "Merging the word frequency counts."
local/merge-batch-counts-threads $dir/counts
fi

if [ ${stage} -le 3 ] && [ ${stop_stage} -ge 3 ]; then
#4：训练语言模型
echo "Making BIG LM, with order=${order}, prune=${prune}, vocab=${lexicon}"

root_path=`pwd`
mkdir -p $tmp_path
cd $tmp_path   # change to $tmp_path, in case there will be some discount files.
$root_path/local/make-big-lm -read $root_path/$dir/counts/*.ngrams.gz \
    -order $order -limit-vocab -vocab $root_path/$lexicon -unk -map-unk "<UNK>" \
    -kndiscount  -interpolate -prune $prune -lm $root_path/$dir/lm.arpa
cd $root_path
#用法同ngram-counts， 关于平滑算法
# 比较大的语料，一般用 -kndiscount -interpolate
# 比较小的语料，一般用 -wbdiscount
fi


exec 6>&- # 关闭FD6
