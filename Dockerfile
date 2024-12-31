# 基础镜像
FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y \
        git \
        subversion \
        supervisor \
        netcat-openbsd \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 创建目录
RUN mkdir -p /opt/asr-2pass

# 拷贝当前目录到镜像中
COPY . /opt/asr-2pass

# 切换工作目录
WORKDIR /opt/asr-2pass/websocket

# （可选）如果需要提前编译，可在这里添加编译命令
# RUN bash ./run_build.sh

# 为日志文件预先创建目录或文件
RUN touch asr.log asr_zh.log asr_en.log

# 拷贝 supervisor 配置文件到系统目录
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 暴露端口（如需要）
EXPOSE 10096 10097 10098

# 启动 supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
