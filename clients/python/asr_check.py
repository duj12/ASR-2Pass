import asyncio
from ASR_client_api import ASR_Client, parse_args
from compute_wer_line import compute_wer_line

import logging
logger = logging.getLogger(__name__)


def determine_lang(text):
    """
    :param text:
    :return: zh表示中文，en表示中英文混合(英文字符比例超过0.5)、纯英文
    """
    text = str(text)
    total = len(text)
    if total == 0:
        return 'zh'

    en_count = sum(1 for c in text if ord(c) < 128)

    if en_count / total > 0.5:
        return 'en'
    else:
        return 'zh'

async def asr_main(asr_args, client, audio_in):
    await client.connect()
    # Send messages
    asr_args.audio_in = audio_in
    await client.send_message(asr_args)
    # Process messages received
    await client.receive_message()
    asr_result = client.asr_result
    await client.clear_cache()
    await client.close()
    return asr_result


class ASR_Checker:
    def __init__(
            self,
            zh_server_host="192.168.88.101",
            zh_server_port="30961",   # 测试环境中asr-2pass中文服务的端口，实际需改为正式环境
            en_server_host="192.168.88.101",
            en_server_port="32205",   # 测试环境中asr-2pass英文服务的端口，实际需改为正式环境
            wer_threshold=0.3
    ):

        self.asr_args = parse_args()
        self.zh_asr_client = ASR_Client(zh_server_host, zh_server_port)
        self.en_asr_client = ASR_Client(en_server_host, en_server_port)
        self.wer_threshold = wer_threshold

    def get_asr_result(self, audio_in, language="zh"):
        if language =='zh':
            asr_result = asyncio.run(asr_main(self.asr_args, self.zh_asr_client, audio_in))
        elif language == 'en':
            asr_result = asyncio.run(asr_main(self.asr_args, self.en_asr_client, audio_in))
        else:
            raise NotImplementedError(f"language {language} is not support by the ASR server.")

        return asr_result

    def check(self, text_in, audio_in):
        '''
        :param text_in: 待检测文本
        :param audio_in:  待检测音频
        :param wer_threshold:  字错误率阈值，如果错误率低于此数值，说明音频和文本内容一致。
        :return:
        '''
        language = determine_lang(text_in)
        asr_result = self.get_asr_result(audio_in, language)

        wer_result = compute_wer_line(text_in, asr_result, verbose=1)
        if wer_result['stats']['wer'] < self.wer_threshold:
            wer_result['result'] = True
        else:
            wer_result['result'] = False
        
        return wer_result


if __name__ == "__main__":
    asr_checker = ASR_Checker()

    result = asr_checker.check("魔珐在业内处于什么样子的一个位置啊", "../audio/xmov.wav")
    print(result, result['result'])
    result = asr_checker.check("but ten years later， when we were designing the first mackinto sh computer， it all came back to me。and we designed it all into the mac。 it was the first computer with beautiful。", "../audio/SteveJobs_10s.wav")
    print(result, result['result'])