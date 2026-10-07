@echo off
REM 供 .claude/launch.json 预览使用：在工作目录启动管理台 dev server
cd /d "%~dp0..\03-web-admin"
set PATH=C:\nvm4w\nodejs;%PATH%
call npx vite --host --mode development
