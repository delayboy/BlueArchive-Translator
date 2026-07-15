import os
import shutil
import json
from dotenv import load_dotenv
from lib.console import notice
from lib.dumper import IL2CppDumper, compile_python
from utils.regions import Server
from utils.config import Config
from utils.util import FileUtils
from argparse import ArgumentParser

def parse_args():
    p = ArgumentParser(description="维护更新")
    p.add_argument("server", type=str, choices=["CN", "GL", "JP", "JPPC"], help="服务器区域")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    Config.server = args.server

    env_file = f"other/BA_{Config.server}.env"
    load_dotenv(env_file)
    
    local_version = os.getenv("GameVersion")
    cached_server_url = os.getenv("ServerInfoDataUrl")
    cached_platform_id = os.getenv("PlatformID")
    cached_channel_id = os.getenv("ChannelID")
    local_latest_version = os.getenv("LatestVersion")

    server = Server()
    apk_url, version = server.get_apk_url()
    
    major = local_version != version
    major_pc = False

    # GameVersion大版本更新
    if major:
        notice(f"检测到GameVersion大版本更新: {local_version} -> {version}")
        with open("MAJOR_UPDATE", "w") as f:
            f.write("true")

        server.main(apk_url, version)
    else:
        notice(f"GameVersion大版本一致 ({version})，尝试增量检查。")

    if Config.server == "JPPC":
        latest_ver, file_path, res_ver = server.get_game_launcher_config(version)
        zip_url = server.get_zip_config_url(version, latest_ver, file_path)
        major_pc = local_latest_version != latest_ver
        # LatestVersion大版本更新
        if major_pc:
            notice(f"检测到LatestVersion大版本更新: {local_latest_version} -> {latest_ver}")
            server.download_launcher_assets(res_ver, zip_url, ["resources.assets", "resources.assets.resS"], "Temp/assets/bin/Data")
        else:
            notice(f"LatestVersion大版本一致 ({latest_ver})，尝试增量检查。")

    if Config.server == "GL":
        server_url, platform_id, channel_id = server.get_server_url(version)
    else:
        if major or major_pc:
            server_url, platform_id, channel_id = server.get_server_url(version)
        else:
            server_url, platform_id, channel_id = cached_server_url, cached_platform_id, cached_channel_id

    # 获取 Addressable 等详细信息
    addressable_url, res_v, tab_v, med_v, pat_v = server.get_addressable_catalog_url(
        server_url, platform_id, channel_id, version
    )

    # 写入环境变量
    new_env_content = [
        f"ServerInfoDataUrl={server_url}\n",
        f"AddressableCatalogUrl={addressable_url}\n",
        f"GameVersion={version}\n"
    ]

    # 追加 CN 特有字段
    if Config.server == "CN":
        new_env_content.extend([
            f"PlatformID={platform_id}\n",
            f"ChannelID={channel_id}\n",
            f"ResourceVersion={res_v}\n",
            f"TableVersion={tab_v}\n",
            f"MediaVersion={med_v}\n",
            f"PatchVersion={pat_v}\n"
        ])
    
    # 追加 JPPC 特有字段
    if Config.server == "JPPC":
        new_env_content.extend([
            f"LatestVersion={latest_ver}\n",
            f"FilePath={file_path}\n",
            f"ResourceVersion={res_ver}\n",
            f"ZipConfigUrl={zip_url}\n"
        ])

    # 检查并更新 env 文件
    with open(env_file, "r", encoding="utf-8") as f:
        old_lines = f.readlines()
    if old_lines != new_env_content:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_env_content)
        with open("UPDATE_FOUND", "w") as f:
            f.write("true")
        notice(f"{env_file} 配置同步完成。")
    else:
        notice(f"{env_file} 配置无更新。")

    # 后续 Dumper 逻辑（非 JPPC 且是大版本时运行）
    if major and Config.server != "JPPC":
        dumper = IL2CppDumper(install_dir="tools")

        metadata_path = os.path.abspath(FileUtils.find_files("Temp", [r"global-metadata\.dat"], True, True)[0])
        il2cpp_path = os.path.abspath(FileUtils.find_files("Temp", [r"libil2cpp\.so"], True, True)[0])
        dumper.dump_il2cpp(Config.server, il2cpp_path, metadata_path, os.path.abspath("Dumps/dump.cs"))

        notice("成功生成dump.cs。")
        compile_python(os.path.join(os.path.abspath("Dumps"), "dump.cs"), "FlatData")
        notice("成功生成FlatData库。")
        shutil.rmtree("Temp")
