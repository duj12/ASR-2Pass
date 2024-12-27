# 使用 ubuntu 作为基础镜像
FROM ubuntu:22.04

# 更新包索引并安装依赖：git 和 subversion
RUN apt update && apt install -y git subversion

# 克隆 git 仓库
RUN git clone https://git.xmov.ai/dujing/asr-2pass.git

# 切换到 websocket 目录
WORKDIR /asr-2pass/websocket

RUN echo $SVN_USERNAME

# 使用 SVN 获取模型
RUN svn checkout --username $SVN_USERNAME --password $SVN_PASSWORD svn://svn-local.xmov.ai/repository/AlgModels/ASR/latest/models

# 启动中文流式服务
RUN nohup bash ./run_server_2pass.sh --port 10096 > asr.log 2>&1 &

# 启动中文离线服务
RUN nohup bash ./run_server_offline.sh --port 10097 > asr_zh.log 2>&1 &

# 启动英文离线服务
RUN nohup bash ./run_server_offline_en.sh --port 10098 > asr_en.log 2>&1 &

# 默认命令启动并保持容器运行
CMD tail -f asr.log
