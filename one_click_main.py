import os
import sys
from pathlib import Path
import re
import winreg
import shutil
from datetime import datetime
from PyTools.MyAwesomeTool.MyUtil import run_cmd, compress_folder_with_progress
from assistance_script.resize_exceldb_to_raw import main as resize_main
from assistance_script.convert_tw_to_cn import main as translate_main

INSTALL_ROOT = r"D:\SteamLibrary\steamapps\common\BlueArchive"
PRELOAD_PATH = r"BlueArchive_Data\StreamingAssets\PUB\Resource\Preload"
BUNDLE_NAME = 'prologdepengroup-assets-_mx-uis-_mxcommon-_mxprolog-2026-03-13_assets_all_842690403.bundle'
EXCEL_DB_NAME = 'ExcelDB.db'
PROJECT_ROOT = os.path.abspath(".")

BUNDLE_PATH = os.path.join(PRELOAD_PATH, 'windows', BUNDLE_NAME)
DB_PATH = os.path.join(PRELOAD_PATH, 'TableBundles', EXCEL_DB_NAME)
TRANSLATE_PATH = os.path.join(PROJECT_ROOT, PRELOAD_PATH, 'TableJson')


def init_python_env():
    # 获取当前脚本所在目录
    script_dir = Path(PROJECT_ROOT)
    # 构建要添加的路径
    python_embeded = script_dir / "python_embeded"
    new_paths = [
        str(python_embeded / "Scripts"),
        str(python_embeded),
    ]
    # 获取当前 PATH
    current_path = os.environ.get("PATH", "")
    # 将新路径插入到最前面（优先级最高）
    os.environ["PATH"] = os.pathsep.join(new_paths) + os.pathsep + current_path


def check_if_path_exist_or_copy_from_install_dir(resource_path: str) -> bool:
    pro_path = os.path.join(PROJECT_ROOT, resource_path)
    file_name = os.path.basename(resource_path)
    if os.path.exists(pro_path):
        print(f"资源文件已存在，跳过拷贝:{file_name}")
        return True
    else:
        print(f"资源文件不存在，从安装目录拷贝:{file_name}")
        os.makedirs(os.path.dirname(pro_path), exist_ok=True)
        shutil.copy2(os.path.join(INSTALL_ROOT, resource_path), pro_path)
        return False


if __name__ == '__main__':
    init_python_env()
    if not check_if_path_exist_or_copy_from_install_dir(BUNDLE_PATH):  # 文件不存在则拷贝之后执行patch
        os.chdir(PROJECT_ROOT + "/" + "BlueArchive-Tools-main")
        run_cmd("python swap_font_to_sc.py")
        os.chdir(PROJECT_ROOT)
    if not check_if_path_exist_or_copy_from_install_dir(DB_PATH):
        os.chdir(PROJECT_ROOT + "/" + "BlueArchive-Tools-main")
        db_path = os.path.join(PROJECT_ROOT, DB_PATH)
        db_dir_path = os.path.dirname(db_path)
        shutil.copy2(db_path, db_path.replace("ExcelDB.db", "ExcelDB-raw.db"))
        run_cmd(f"python process_excel.py \"{db_dir_path}\" \"{TRANSLATE_PATH}\" GL  Extract")
        translate_main(TRANSLATE_PATH)
        shutil.rmtree(os.path.join(TRANSLATE_PATH, 'ExcelDB'))
        shutil.copytree(os.path.join(TRANSLATE_PATH, 'translate'), os.path.join(TRANSLATE_PATH, 'ExcelDB'),
                        dirs_exist_ok=True)
        run_cmd(f"python process_excel.py \"{db_dir_path}\" \"{TRANSLATE_PATH}\" GL  Repack")
        resize_main(db_dir_path)
        os.chdir(PROJECT_ROOT)
    today = datetime.now().strftime("%Y-%m-%d")
    zip_folder = os.path.join(PROJECT_ROOT, "BlueArchive_Data")
    white_list = {BUNDLE_PATH.replace("BlueArchive_Data\\", ""), DB_PATH.replace("BlueArchive_Data\\", "")}
    compress_folder_with_progress(zip_folder, f"{today}-蔚蓝档案steam端简中汉化补丁.zip", white_list=white_list)
