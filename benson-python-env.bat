@echo off
chcp 65001 >nul
@title 自制启动器 by Benson
set HF_HOME=%~dp0python_embeded\.cache
set HF_ENDPOINT=https://hf-mirror.com
set HF_HUB_OFFLINE=1
set "PATH=%~dp0python_embeded\Scripts;%~dp0python_embeded\;%PATH%"