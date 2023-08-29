
## Install the requirements for client
`Tips`: python3.7+ is required

```shell
apt-get install -y ffmpeg #ubuntu
# yum install -y ffmpeg # centos
# brew install ffmpeg # mac
# winget install ffmpeg # wins
pip3 install websockets ffmpeg-python
```

## Usage examples

```shell
# audio
python3 funasr_wss_client.py --host "127.0.0.1" --port 10095 --mode offline --audio_in "../audio/xmov.wav"
# video
python3 funasr_wss_client.py --host "127.0.0.1" --port 10095 --mode offline --audio_in "../audio/test.mp4"
```

## API-reference
```shell
python funasr_wss_client.py \
--host [ip_address] \
--port [port id] \
--audio_in [if set, loadding from wav.scp, else recording from mircrophone] \
--output_dir [if set, write the results to output_dir] \
--mode [`online` for streaming asr, `offline` for non-streaming, `2pass` for unifying streaming and non-streaming asr]
--thread_num [`1` deflaut, how many threads used to send data]
--hotword [hotword, *.txt(one hotword perline) or hotwords seperate by space ]
--ssl [`1` deflaut, where to connect with ssl, if set `0` to close ssl]
```

