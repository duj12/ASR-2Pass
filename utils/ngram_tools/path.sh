export RUNTIME_ROOT=`pwd`/../../

# we build fst related command here, you may use kaldi/tools/openfst instead
export PATH=$RUNTIME_ROOT/websocket/build/bin:$PWD:$PATH
# SRILM bin path, please modify it to your own SRILM path, it's convenient to install it in kaldi/tools/srilm
KALDI_ROOT=/data/megastore/Projects/DuJing/code/kaldi
export PATH=$KALDI_ROOT/tools/srilm/bin:$KALDI_ROOT/tools/srilm/bin/i686-m64:$PATH

export LC_ALL=C
