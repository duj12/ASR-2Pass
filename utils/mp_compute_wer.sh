inscp=$1
inhyp=$2
outscp=$3

nj=64

data=$(dirname ${inscp})
logdir=${data}/log
mkdir -p ${logdir}

rm -f $logdir/wav_*.slice
rm -f $logdir/wav_*.shape
split --additional-suffix .slice -d -n l/$nj $inscp $logdir/wav_

for slice in `ls $logdir/wav_*.slice`; do
{
    perl utils/filter_scp.pl  $slice  $inhyp > ${slice}.hyp
    python3 utils/compute-wer.py  --char=1 --v=1 \
        $slice  ${slice}.hyp > $slice.wer
} &
done
wait
cat $logdir/*.wer > $outscp