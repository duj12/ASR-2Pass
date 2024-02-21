import glob
import os
import sys

def merge_transcriptions(folder_path, output_file):
    with open(output_file, 'w') as output:
        file_paths = glob.glob(os.path.join(folder_path, '**/transcription.txt'), recursive=True)
        total_files = len(file_paths)
        print(f"total files: {total_files}")
        for filepath in file_paths:
            print(f"cat file {filepath}")
            with open(filepath, 'r') as f:
                output.write(f.read())
                # output.write('\n')  # 添加换行符以区分不同文件的内容

# 指定文件夹路径和输出文件名
folder_path = sys.argv[1]  # 将此路径替换为实际的文件夹路径
output_file = sys.argv[2]

# 调用函数进行合并操作
merge_transcriptions(folder_path, output_file)