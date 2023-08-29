# 使用方式

## 1. 本地浏览器访问
在浏览器中打开 html/static/asr-2pass-demo.html，输入ASR服务器地址，支持麦克风输入，也支持文件输入

## 2. 其他机器，需要可访问部署服务的服务器ip
启动html5服务
```shell
h5Server.py [-h] [--host HOST] [--port PORT] [--certfile CERTFILE] [--keyfile KEYFILE]             
```
例子如下，需要注意ip地址，如果从其他设备访问需求（例如手机端），需要将ip地址设为真实公网ip 
```shell
cd html5
python h5Server.py --host 0.0.0.0 --port 1337
```
启动后，在浏览器中输入https://127.0.0.1:1337/static/asr-2pass-demo.html 即可访问
