@echo off
chcp 65001 >nul
@title 自制启动器 by Benson
set HF_HOME=%~dp0python_embeded\.cache
set HF_ENDPOINT=https://hf-mirror.com
set HF_HUB_OFFLINE=1
set "PATH=%~dp0..\python_embeded\Scripts;%~dp0..\python_embeded\;%~dp0..\python_embeded\Library\bin;%PATH%"

pyinstaller --onefile --uac-admin --add-data "%~dp0..\BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\windows\prologdepengroup-assets-_mx-uis-_mxcommon-_mxprolog-2026-03-13_assets_all_842690403.bundle;bundled_assets" BlueArchiveCnPatcher.py
pause