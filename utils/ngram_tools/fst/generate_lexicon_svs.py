#!/usr/bin/env python3
# encoding: utf-8

import sys
import json
import re

# input
# sys.argv[1]: lm dict, with all words in the corpus
# sys.argv[2]: token unit file
# sys.argv[3]: bpe model file
# output
# sys.argv[4]: lexicon file for corpus.dict, map raw words to token units
# sys.argv[5]: units file output, assign each unit an integer id
# sys.argv[6]: units json file output, add <blank> token at the beginning  

def contain_oov(units):
    for unit in units:
        if unit not in unit_table:
            return True
    return False

# step 1: load unit table
unit_table = []
with open(sys.argv[2], 'r', encoding='utf8') as fin:
    unit_table = json.load(fin)
    if unit_table[0] == "<unk>":
        unit_table[0] = "<blank>"  # replace <unk> with <blank> for id==0
print(f"unit size: {len(unit_table)}")

# step 2: load sentence piece model
import sentencepiece as spm
sp = spm.SentencePieceProcessor()
sp.Load(sys.argv[3])

# convert the unit table to a output format, units.txt and units.json    
with open(sys.argv[5], 'w', encoding='utf8') as fout:
    for idx, unit in enumerate(unit_table):
        fout.write(f"{unit} {idx}\n")
with open(sys.argv[6], 'w', encoding='utf-8') as fout:
    json.dump(unit_table, fout, ensure_ascii=False, indent=4)


lexicon_table = set()
with open(sys.argv[1], 'r', encoding='utf8') as fin, \
        open(sys.argv[4], 'w', encoding='utf8') as fout:
    for line in fin:
        word = line.split()[0]
        if word == 'SIL':  # `sil` might be a valid piece in bpemodel
            continue
        elif word == '<SPOKEN_NOISE>':
            continue
        elif word == "<s>" or word == "</s>" or word=="<eps>":
            continue
        elif word == '<unk>' or word == '<blank>':
            fout.write('{}\t{}\n'.format(word, '<blank>'))
            lexicon_table.add(word)
        else:
            # each word only has one pronunciation for e2e system
            if word in lexicon_table:
                continue
            if re.search(r"[A-Za-z0-9]", word) and not re.search(r"[\u4e00-\u9fff]", word):
                pieces = sp.EncodeAsPieces("▁"+word)  # for English words, add ▁ at the beginning
                # print ('English word {}, pieces {}'.format(word, pieces))
            else:
                pieces = sp.EncodeAsPieces(word)
            if contain_oov(pieces):
                print(
                    'Ignoring words {}, which contains oov unit, piece {}'.format(
                        ''.join(word).strip('▁'), pieces)
                )
                # continue
            chars = ' '.join(
                [p if p in unit_table else '<blank>' for p in pieces])  # replace oov with <blank>
            
            fout.write('{}\t{}\n'.format(word, chars))
            lexicon_table.add(word)

print(f"lexicon size: {len(lexicon_table)}")