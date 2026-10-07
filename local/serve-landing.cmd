@echo off
REM 供 .claude/launch.json 预览使用：启动落地页服务器
cd /d "%~dp0"
python landing-server.py
