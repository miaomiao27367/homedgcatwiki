@echo off
chcp 65001 >nul
echo 现在启动本地服务器...
start http://localhost:9080
python server.py

pause