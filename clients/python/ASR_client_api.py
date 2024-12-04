import os
import asyncio
import numpy
import librosa
import websockets
import ssl
import json
import argparse
import logging
logging.basicConfig(level=logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host",
                        type=str,
                        default="192.168.88.101",
                        required=False,
                        help="host ip, localhost, 0.0.0.0")
    parser.add_argument("--port",
                        type=int,
                        default=31826,
                        required=False,
                        help="grpc server port")
    parser.add_argument("--chunk_size",
                        type=str,
                        default="5, 10, 5",
                        help="chunk")
    parser.add_argument("--chunk_interval",
                        type=int,
                        default=10,
                        help="chunk")
    parser.add_argument("--hotword",
                        type=str,
                        default="",
                        help="hotword, *.txt(one hotword perline) or hotwords seperate by space (could be: 语音识别 热词)")
    parser.add_argument("--audio_in",
                        type=str,
                        default="../audio/test.mp4",
                        help="input audio, could be path, or 1d-numpy of samples")
    parser.add_argument("--audio_sr",
                        type=int,
                        default=24000,
                        help="if the audio_in is ndarray, you must give the audio_sr")
    parser.add_argument("--send_without_sleep",
                        action="store_true",
                        default=True,
                        help="if audio_in is set, send_without_sleep")
    parser.add_argument("--thread_num",
                        type=int,
                        default=1,
                        help="thread_num")
    parser.add_argument("--words_max_print",
                        type=int,
                        default=10000,
                        help="chunk")
    parser.add_argument("--output_dir",
                        type=str,
                        default=None,
                        help="output_dir")
    parser.add_argument("--ssl",
                        type=int,
                        default=0,
                        help="1 for ssl connect, 0 for no ssl")
    parser.add_argument("--use_itn",
                        type=int,
                        default=0,
                        help="1 for using itn, 0 for not itn")
    parser.add_argument("--vad_tail_sil",
                        type=int,
                        default=800,
                        help="tail silence length for VAD, if silence time exceed this value, VAD will cut. in ms")
    parser.add_argument("--vad_max_len",
                        type=int,
                        default=60000,
                        help="max duration of a audio clip cut by VAD, in ms")
    parser.add_argument("--mode",
                        type=str,
                        default="offline",
                        help="offline, online, 2pass")

    args = parser.parse_args()
    args.chunk_size = [int(x) for x in args.chunk_size.split(",")]
    return args


class ASR_Client:
    def __init__(self, host, port, mode='offline', ssl_enabled=False):
        if ssl_enabled:
            ssl_context = ssl.SSLContext()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = f"wss://{host}:{port}"
        else:
            uri = f"ws://{host}:{port}"
            ssl_context = None

        self.websocket = None
        self.asr_mode=mode
        self.asr_result = ""
        self.uri = uri
        self.ssl_context = ssl_context

    async def connect(self):
        print("Connecting to", self.uri)
        self.websocket = await websockets.connect(
            self.uri, subprotocols=["binary"],
            ping_interval=None, ssl=self.ssl_context)

    async def send_message(self, args):
        if self.websocket:
            if os.path.isfile(args.audio_in):
                import ffmpeg
                try:
                    # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
                    audio_bytes, _ = (
                        ffmpeg.input(args.audio_in, threads=0)
                            .output("-", format="s16le", acodec="pcm_s16le",
                                    ac=1, ar=16000)
                            .run(cmd=["ffmpeg", "-nostdin"],
                                 capture_stdout=True, capture_stderr=True)
                    )
                except ffmpeg.Error as e:
                    audio_bytes = []
                    logging.error(
                        f"Failed to load audio {args.audio_in}: {e.stderr.decode()}")

            elif isinstance(args.audio_in, numpy.ndarray):
                audio = librosa.resample(
                    args.audio_in, args.audio_sr, 16000)
                audio = (audio * 32768).astype(numpy.int16) # convert into int 16
                audio_bytes = audio.tobytes()

            else:
                raise NotImplementedError(f"{args.audio_in} format not support.")

            stride = int(60 * args.chunk_size[
                1] / args.chunk_interval / 1000 * 16000 * 2)
            chunk_num = (len(audio_bytes) - 1) // stride + 1

            formatted_words = []
            if args.hotword.endswith(".txt"):
                with open(args.hotword) as fin:
                    for line in fin:
                        line = line.strip()
                        formatted_words.append(line)
                hotwords = ' '.join(formatted_words)
            else:
                hotwords = args.hotword

            itn = bool(args.use_itn)
            message = json.dumps(
                {"mode": args.mode, "chunk_size": args.chunk_size,
                 "chunk_interval": args.chunk_interval,
                 "wav_name": "temp", "is_speaking": True,
                 "hotwords": hotwords, "itn": itn,
                 "vad_tail_sil": args.vad_tail_sil,
                 "vad_max_len": args.vad_max_len, })

            # send first time
            await self.websocket.send(message)

            if len(audio_bytes) == 0:
                message = json.dumps({"is_speaking": False})
                await self.websocket.send(message)
            else:
                for i in range(chunk_num):
                    beg = i * stride
                    data = audio_bytes[beg:beg + stride]
                    message = data
                    await self.websocket.send(message)
                    if i == chunk_num - 1:
                        is_speaking = False
                        message = json.dumps({"is_speaking": is_speaking})
                        # last chunk.
                        await self.websocket.send(message)
        else:
            print("WebSocket connection is not established.")

    async def receive_message(self):
        if self.websocket:
            while True:
                message = await self.websocket.recv()
                text, is_final = await self.parse_message(message)
                self.asr_result += text
                if is_final or self.asr_mode=="offline":
                    break
        else:
            print("WebSocket connection is not established.")

    async def parse_message(self, message):
        meg = json.loads(message)
        mode = meg.get("mode", "null")
        if "offline" in mode:
            text = meg["text"]
        else:  # 流式识别临时结果
            text = ""
        is_final = meg.get("is_final", False)
        return text, is_final

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

async def main():
    args = parse_args()
    client = ASR_Client(args.host, args.port, args.mode)
    await client.connect()

    # Send messages
    await client.send_message(args)

    # Process messages received
    await client.receive_message()

    logging.info(f"ASR result： {client.asr_result}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())