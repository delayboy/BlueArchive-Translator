import os
import sys
import argparse
from pathlib import Path
import re
import winreg
import shutil
from datetime import datetime
from PyTools.MyAwesomeTool.MyUtil import run_cmd, compress_folder_with_progress
from assistance_script.resize_exceldb_to_raw import main as resize_main
from assistance_script.convert_tw_to_cn import main as translate_main
import hashlib
import os
from xtractor.table import TableProcess
from lib.encryption import calculate_md5
import json
import ssl
import _ssl
from FlatData import *
import FlatData.dump_wrapper
import FlatData.repack_wrapper
from utils.config import Config

KEY_HEX = "" # 05f508236ff3dc4e5dc7cb6fcea0ede0d90a89753dc5e5d36c30393e9b072f48
PRELOAD_PATH = r"BlueArchive_Data\StreamingAssets\PUB\Resource\Preload"
BUNDLE_NAME = 'prologdepengroup-assets-_mx-uis-_mxcommon-_mxprolog-2026-03-13_assets_all_842690403.bundle'
EXCEL_DB_NAME = 'ExcelDB.db'
PROJECT_ROOT = os.path.abspath(".")

BUNDLE_PATH = os.path.join(PRELOAD_PATH, 'windows', BUNDLE_NAME)
DB_PATH = os.path.join(PRELOAD_PATH, 'TableBundles', EXCEL_DB_NAME)
TRANSLATE_PATH = os.path.join(PROJECT_ROOT, PRELOAD_PATH, 'TableJson')


def get_bundled_resource(rel: str) -> str:
    """onefile 模式下 PyInstaller 把 --add-data 的文件解包到 sys._MEIPASS 临时目录；开发模式回退到脚本所在目录"""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def check_if_file_right_from_install_dir(resource_path: str, md5_json: dict) -> bool:
    pro_path = os.path.join(PROJECT_ROOT, resource_path)
    file_name = os.path.basename(resource_path)
    md5 = calculate_md5(pro_path)
    aim_md5 = ""
    if not os.path.exists(resource_path):
        print(f"资源文件不存在:{file_name},请将本exe程序拷贝到游戏安装目录和BlueArchive.exe放到同一目录下使用")
        return True
    if md5_json.__contains__(resource_path):
        aim_md5 = md5_json[resource_path]
    if md5.__eq__(aim_md5):
        print(f"资源文件已patch，跳过patch:{file_name}")
        return True
    else:
        print(f"资源文件未patch，现在开始执行patch:{file_name}")
        return False


def get_exe_dir() -> str:
    """exe 所在目录（打包后为 exe 自身目录，开发模式为脚本目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def deploy_winmm_dll():
    """db_password 为空时：解压内嵌的 winmm.dll 到 exe 同级目录，并提示自动汉化用法"""
    src = get_bundled_resource('winmm.dll')
    if not os.path.exists(src):
        print("错误: exe 内未找到 winmm.dll 资源, 请重新打包")
        sys.exit(1)
    dst = os.path.join(get_exe_dir(), 'winmm.dll')
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)
    print("=" * 60)
    print("未指定数据库密钥(--db-password), 已进入【自动获取密钥】模式")
    print()
    print(f"已解压 winmm.dll 到本程序所在目录: {dst}")
    print()
    print("使用方法:")
    print("  1. 确认本程序已放在游戏安装目录(和 BlueArchive.exe 同一目录)")
    print("  2. 正常启动游戏(官方启动器/Steam 均可), 无需手动输入密钥")
    print("  3. 游戏启动时 winmm.dll 会自动拦截游戏的数据库密钥,")
    print("     并自动调用本程序完成汉化")
    print("  4. 期间弹出 UAC(用户账户控制) 提示时请点击\"是\"")
    print("  5. 弹出的控制台窗口显示 patch 完成日志后, 即可正常进游戏")
    print()
    print("提示: 若之后游戏更新导致汉化失效, 重新运行本程序一次即可")
    print("=" * 60)
    input("按回车键退出...")
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(description="蔚蓝档案国服汉化补丁工具")
    parser.add_argument(
        '--db-password',
        default=KEY_HEX,
        help="ExcelDB.db 的 SQLCipher 密钥(hex); 不填则解压 winmm.dll, 由游戏启动时自动拦截密钥并回调本程序",
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if not args.db_password:
        deploy_winmm_dll()
    json_dic = {}
    Config.db_password = args.db_password
    pro_bundle_path = get_bundled_resource(os.path.join('bundled_assets', BUNDLE_NAME))
    if not os.path.exists(pro_bundle_path):
        # 开发模式回退：直接用游戏目录里的 bundle（此情况下源和目标是同一个文件）
        pro_bundle_path = os.path.join(PROJECT_ROOT, BUNDLE_PATH)
    if os.path.exists("./file_check.json"):
        with open("./file_check.json", 'r', encoding='utf-8') as f:
            json_dic = json.load(f)
    if os.path.exists(pro_bundle_path):
        json_dic[BUNDLE_PATH] = calculate_md5(pro_bundle_path)
    if not check_if_file_right_from_install_dir(DB_PATH, json_dic):
        db_path = os.path.join(PROJECT_ROOT, DB_PATH)
        db_dir_path = os.path.dirname(db_path)
        shutil.copy2(db_path, db_path.replace("ExcelDB.db", "ExcelDB-raw.db"))
        process = TableProcess(str(db_dir_path), str(TRANSLATE_PATH), "FlatData")
        process.process_table("ExcelDB.db", "Extract", True)
        translate_main(TRANSLATE_PATH)
        shutil.rmtree(os.path.join(TRANSLATE_PATH, 'ExcelDB'))
        shutil.copytree(os.path.join(TRANSLATE_PATH, 'translate'), os.path.join(TRANSLATE_PATH, 'ExcelDB'),
                        dirs_exist_ok=True)
        process.process_table("ExcelDB.db", "Repack", True)
        resize_main(db_dir_path)
        with open("./file_check.json", 'w', encoding='utf-8') as f:
            json_dic[DB_PATH] = calculate_md5(db_path)
            json.dump(json_dic, f, ensure_ascii=False, indent=4)
    if not check_if_file_right_from_install_dir(BUNDLE_PATH, json_dic):
        if os.path.abspath(pro_bundle_path) != os.path.abspath(BUNDLE_PATH):
            shutil.copy2(pro_bundle_path, BUNDLE_PATH)
    if os.path.exists(TRANSLATE_PATH):
        shutil.rmtree(TRANSLATE_PATH)
    # input("程序执行完成，按任意键退出:\n")
