#!/use/bin/env python
import os
import sys
import shutil

scp=sys.argv[1]

with open(scp, "r") as fin:
    for line in fin:
        line = line.strip().split("\t")
        name, path = line[0], line[1]
        if not os.path.exists(path):
            print(f"{path} not exists, jump.")
            continue
        if ' ' in path:
            new_path = path.replace(" ", "-", -1)
            temp = new_path.split('/')
            new_file = temp[-1]
            new_dir = '/'.join(temp[:-1])
            if not os.path.exists(new_dir):
                os.mkdir(new_dir)
            new_path = os.path.join(new_dir, new_file)
            print(f"move {path} to {new_path}.")
            shutil.move(path, new_path)
        
            
            
