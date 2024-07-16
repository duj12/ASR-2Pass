#!/usr/bin/env python3
# coding=utf-8

import sys, argparse, codecs, string, re, logging
from multiprocessing import Process, Queue

from tn.chinese.normalizer import Normalizer
normalizer = Normalizer()
logger = logging.getLogger(__name__)

CHINESE_DIGIS = u'零一二三四五六七八九'
BIG_CHINESE_DIGIS_SIMPLIFIED = u'零壹贰叁肆伍陆柒捌玖'
BIG_CHINESE_DIGIS_TRADITIONAL = u'零壹貳參肆伍陸柒捌玖'
SMALLER_BIG_CHINESE_UNITS_SIMPLIFIED = u'十百千万'
SMALLER_BIG_CHINESE_UNITS_TRADITIONAL = u'拾佰仟萬'
LARGER_CHINESE_NUMERING_UNITS_SIMPLIFIED = u'亿兆京垓秭穰沟涧正载'
LARGER_CHINESE_NUMERING_UNITS_TRADITIONAL = u'億兆京垓秭穰溝澗正載'
SMALLER_CHINESE_NUMERING_UNITS_SIMPLIFIED = u'十百千万'
SMALLER_CHINESE_NUMERING_UNITS_TRADITIONAL = u'拾佰仟萬'

ZERO_ALT = u'〇'
ONE_ALT = u'幺'
TWO_ALTS = [u'两', u'兩']

POSITIVE = [u'正', u'正']
NEGATIVE = [u'负', u'負']
POINT = [u'点', u'點']
# PLUS = [u'加', u'加']
# SIL = [u'杠', u'槓']

FILLER_CHARS = ['呃', '啊']
ER_WHITELIST = '(儿女|儿子|儿孙|女儿|儿媳|妻儿|' \
             '胎儿|婴儿|新生儿|婴幼儿|幼儿|少儿|小儿|儿歌|儿童|儿科|托儿所|孤儿|' \
             '儿戏|儿化|台儿庄|鹿儿岛|正儿八经|吊儿郎当|生儿育女|托儿带女|养儿防老|痴儿呆女|' \
             '佳儿佳妇|儿怜兽扰|儿无常父|儿不嫌母丑|儿行千里母担忧|儿大不由爷|苏乞儿)'

# 中文数字系统类型
NUMBERING_TYPES = ['low', 'mid', 'high']

CURRENCY_NAMES = '(人民币|美元|日元|英镑|欧元|马克|法郎|加拿大元|澳元|港币|先令|芬兰马克|爱尔兰镑|' \
                 '里拉|荷兰盾|埃斯库多|比塞塔|印尼盾|林吉特|新西兰元|比索|卢布|新加坡元|韩元|泰铢)'
CURRENCY_UNITS = '((亿|千万|百万|万|千|百)|(亿|千万|百万|万|千|百|)元|(亿|千万|百万|万|千|百|)块|角|毛|分)'
COM_QUANTIFIERS = '(匹|张|座|回|场|尾|条|个|首|阙|阵|网|炮|顶|丘|棵|只|支|袭|辆|挑|担|颗|壳|窠|曲|墙|群|腔|' \
                  '砣|座|客|贯|扎|捆|刀|令|打|手|罗|坡|山|岭|江|溪|钟|队|单|双|对|出|口|头|脚|板|跳|枝|件|贴|' \
                  '针|线|管|名|位|身|堂|课|本|页|家|户|层|丝|毫|厘|分|钱|两|斤|担|铢|石|钧|锱|忽|(千|毫|微)克|' \
                  '毫|厘|分|寸|尺|丈|里|寻|常|铺|程|(千|分|厘|毫|微)米|撮|勺|合|升|斗|石|盘|碗|碟|叠|桶|笼|盆|' \
                  '盒|杯|钟|斛|锅|簋|篮|盘|桶|罐|瓶|壶|卮|盏|箩|箱|煲|啖|袋|钵|年|月|日|季|刻|时|周|天|秒|分|旬|' \
                  '纪|岁|世|更|夜|春|夏|秋|冬|代|伏|辈|丸|泡|粒|颗|幢|堆|条|根|支|道|面|片|张|颗|块)'

# punctuation information are based on Zhon project (https://github.com/tsroten/zhon.git)
CHINESE_PUNC_STOP = '！？｡。'
CHINESE_PUNC_NON_STOP = '＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏'
CHINESE_PUNC_LIST = CHINESE_PUNC_STOP + CHINESE_PUNC_NON_STOP


def remove_erhua(text, er_whitelist):
    """
    去除儿化音词中的儿:
    他女儿在那边儿 -> 他女儿在那边
    """

    er_pattern = re.compile(er_whitelist)
    new_str=''
    while re.search('儿',text):
        a = re.search('儿',text).span()
        remove_er_flag = 0

        if er_pattern.search(text):
            b = er_pattern.search(text).span()
            if b[0] <= a[0]:
                remove_er_flag = 1

        if remove_er_flag == 0 :
            new_str = new_str + text[0:a[0]]
            text = text[a[1]:]
        else:
            new_str = new_str + text[0:b[1]]
            text = text[b[1]:]

    text = new_str + text
    return text


def process_lines(thread_id, lines, args, result_queue):
    results = []
    for i, line in enumerate(lines):
        key = ''
        text = ''
        try:
            if args.has_key:
                cols = line.split(maxsplit=1)
                if len(cols) <= 0:
                    continue
                key = cols[0]
                if len(cols) == 2:
                    text = cols[1].strip()
                else:
                    text = ''
            else:
                text = line.strip()

            # cases
            if args.to_upper and args.to_lower:
                sys.stderr.write('text norm: to_upper OR to_lower?')
                exit(1)
            if args.to_upper:
                text = text.upper()
            if args.to_lower:
                text = text.lower()

            # Filler chars removal
            if args.remove_fillers:
                for ch in FILLER_CHARS:
                    text = text.replace(ch, '')

            if args.remove_erhua:
                text = remove_erhua(text, ER_WHITELIST)

            # NSW(Non-Standard-Word) normalization
            text = normalizer.normalize(text)

            # Punctuations removal
            old_chars = CHINESE_PUNC_LIST + string.punctuation # includes all CN and EN punctuations
            new_chars = ' ' * len(old_chars)
            del_chars = ''
            text = text.translate(str.maketrans(old_chars, new_chars, del_chars))

            if args.has_key:
                results.append(key + '\t' + text + '\n')
            else:
                results.append(text + '\n')

        except Exception as e:
            logger.error(f"ITN error: {e}")
            results.append(line)

        if (i+1) % args.log_interval == 0:
            logger.info(f"thread {thread_id} processed {i+1}/{len(lines)}")

    result_queue.put(results)


def main(args):
    result_queue = Queue()

    with codecs.open(args.ifile, 'r', 'utf8') as ifile:
        lines = ifile.readlines()
        total_len = len(lines)
        logger.info(f"total_lines: {total_len}")

        thread_num = args.num_workers
        logger.info(f"num_workers: {thread_num}")

        if total_len >= thread_num:
            chunk_size = int(total_len / thread_num)
            remain_wavs = total_len - chunk_size * thread_num
        else:
            chunk_size = 1
            remain_wavs = 0

        processes = []
        chunk_begin = 0
        for i in range(thread_num):
            now_chunk_size = chunk_size
            if remain_wavs > 0:
                now_chunk_size = chunk_size + 1
                remain_wavs = remain_wavs - 1
            chunks = lines[chunk_begin: chunk_begin + now_chunk_size]
            logger.info(f"thread {i}, chunk size {len(chunks)}")
            p = Process(target=process_lines,
                        args=(i, chunks, args, result_queue))
            chunk_begin = chunk_begin + now_chunk_size
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        all_results = []
        while not result_queue.empty():
            all_results.extend(result_queue.get())

        with codecs.open(args.ofile, 'w+', 'utf8') as ofile:
            for result in all_results:
                ofile.write(result)

if __name__ == '__main__':

    p = argparse.ArgumentParser()
    p.add_argument('ifile', help='input filename, assume utf-8 encoding')
    p.add_argument('ofile', help='output filename')
    p.add_argument('--to_upper', action='store_true', help='convert to upper case')
    p.add_argument('--to_lower', action='store_true', help='convert to lower case')
    p.add_argument('--has_key', action='store_true', help="input text has Kaldi's key as first field.")
    p.add_argument('--remove_fillers', type=bool, default=False, help='remove filler chars such as "呃, 啊"')
    p.add_argument('--remove_erhua', type=bool, default=False, help='remove erhua chars such as "这儿"')
    p.add_argument('--log_interval', type=int, default=10000, help='log interval in number of processed lines')
    p.add_argument('--num_workers', type=int, default=64, help='the number of jobs.')
    args = p.parse_args()

    main(args)
