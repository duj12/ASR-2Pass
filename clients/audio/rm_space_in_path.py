#!/use/bin/env python
import os
import sys
import shutil

scp=sys.argv[1]

with open(scp, "r") as fin:
    for line in fin:
        line = line.strip().split("\t")
        if not len(line) == 2:
            continue
        name, path = line[0], line[1]
        # if not os.path.exists(path):
        #     print(f"{path} not exists, jump.")
        #     continue
        if ' ' in path:
            new_path = path.replace(" ", "-", -1)

            temp = new_path.split('/')
            new_file = temp[-1]
            new_dir = '/'.join(temp[:-1])
            format = os.path.splitext(new_file)[1]
            name = os.path.splitext(new_file)[0]
            name = name.replace(".", "-", -1)  # 文件名中不要有.，避免后面以文件名创建文件夹不成功

            if len(name) > 15:
                name = name[:15]
            new_file = f"{name}{format}"

            if not os.path.exists(new_dir):
                os.makedirs(new_dir, exist_ok=True)
            new_path = os.path.join(new_dir, new_file)
            print(f"move {path} to {new_path}.")
            shutil.move(path, new_path)
        
            
            
