@echo off
chcp 65001 >nul
@title 自制启动器 by Benson
set HF_HOME=%~dp0python_embeded\.cache
set HF_ENDPOINT=https://hf-mirror.com
set HF_HUB_OFFLINE=1
set "PATH=%~dp0..\python_embeded\Scripts;%~dp0..\python_embeded\;%PATH%"
python process_excel.py "..\BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\TableBundles" "..\BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\TableJson" GL  Extract

pause

python process_excel.py "..\BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\TableBundles" "..\BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\TableJson"  GL  Repack

pause
