#!/usr/bin/env python3

import re
from preprocess import (
    remove_space_between_mandarin,
    remove_redundant_whitespaces,
)


if __name__ == '__main__':
    import sys
    input = sys.argv[1]
    output = sys.argv[2]
    has_name = 1
    if len(sys.argv) > 3:
        has_name = int(sys.argv[3])
    fout = open(output, 'w', encoding='utf-8')
    with open(input, 'r', encoding='utf-8') as fin:
        for line in fin:
            if has_name:
                line = line.strip().split(' ')
                name = line[0]
                text = ' '.join(line[1:])
                new_text = remove_space_between_mandarin(text)
                new_text = remove_redundant_whitespaces(new_text)
                fout.write(name + '\t' + new_text + '\n')
            else:
                text = line.strip()
                new_text = remove_space_between_mandarin(text)
                new_text = remove_redundant_whitespaces(new_text)
                fout.write(new_text + '\n')


    fout.close()