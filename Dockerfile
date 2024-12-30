ARG SVN_LOCAL_PATH

# 使用 ubuntu 作为基础镜像
FROM ubuntu:22.04

# 更新包索引并安装依赖：git 和 subversion
RUN apt update && apt install -y git subversion && apt install -y tini

# 克隆 git 仓库
RUN mkdir -p /opt/asr-2pass

COPY . /opt/asr-2pass

COPY $SVN_LOCAL_PATH /opt/asr-2pass/websocket/

# 切换到 websocket 目录
WORKDIR /opt/asr-2pass/websocket

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD bash -c "\
  nohup bash ./run_server_2pass.sh --port 10096 > asr.log 2>&1 & \
  nohup bash ./run_server_offline.sh --port 10097 > asr_zh.log 2>&1 & \
  nohup bash ./run_server_offline_en.sh --port 10098 > asr_en.log 2>&1 & \
  tail -f asr.log"
