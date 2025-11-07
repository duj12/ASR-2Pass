#!/usr/bin/env python3

from preprocess import (
    insert_space_between_mandarin,
    remove_redundant_whitespaces,
)
def is_Chinese(word):
    for ch in word:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

def process_oov(word_set, text_w_space):
    text_list = text_w_space.split(' ')
    new_text_list = []
    for word in text_list:
        if word in word_set:
            new_text_list.append(word)
        else:
            if is_Chinese(word):
                print(f"{word} is OOV, we will not add it into LM.")
            else:
                print(f"{word} is OOV, we split it into chars.")
                new_text_list += [c for c in word]
    return ' '.join(new_text_list)


if __name__ == '__main__':
    import sys
    input = sys.argv[1]
    if input=="-":
        fin=sys.stdin
    else:
        fin = open(input, 'r', encoding='utf-8')
    output = sys.argv[2]
    if output=='-':
        fout = sys.stdout
    else:
        fout = open(output, 'w', encoding='utf-8')
    user_dict = sys.argv[3]
    word_set = set()
    # with open(user_dict, 'r') as f_dict:
    #     for line in f_dict:
    #         word = line.strip()
    #         word_set.add(word)
    has_name = 0
    if len(sys.argv) > 4:
        has_name = int(sys.argv[4])

    for line in fin:
        if has_name:
            line = line.strip().split(' ')
            name = line[0]
            text = ' '.join(line[1:])
            new_text = insert_space_between_mandarin(text)
            new_text = remove_redundant_whitespaces(new_text)
            #new_text = process_oov(word_set, new_text)
            fout.write(name+' '+new_text+'\n')
        else:
            text = line.strip()
            new_text = insert_space_between_mandarin(text)
            new_text = remove_redundant_whitespaces(new_text)
            #new_text = process_oov(word_set, new_text)
            fout.write(new_text + '\n')

    fin.close()
    fout.close()