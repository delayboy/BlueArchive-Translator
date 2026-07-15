import os
import shutil
import base64
import json
import re
from lib.encryption import create_key, convert_string
from lib.downloader import FileDownloader
from lib.console import notice
from utils.config import Config
from utils.util import ZipUtils, FileUtils, AsarUtils, CommandUtils
from xtractor.bundle import BundleExtractor

class Server:
    def main(self, apk_url, version):
        if Config.server != "JPPC":
            downloader_name = f"BlueArchive_{Config.server}_Downdloader.apk"
            Temp_name = f"Temp_{Config.server}_Downloader"
            if os.path.exists(downloader_name):
                notice(f"检测到本地已存在 {downloader_name}，跳过下载。")
            else:
                notice("开始下载APK文件。")
            FileDownloader(url=apk_url, headers={"User-Agent": "Androidkb"}, verbose=True).save_file(downloader_name)
            if Config.server == "CN":
                ZipUtils.extract_zip(zip_path=downloader_name, dest_dir="Temp")
            else:
                ZipUtils.extract_zip(zip_path=downloader_name, dest_dir=Temp_name)
                apk_files = FileUtils.find_files(Temp_name, [r".*\.apk$"], sequential_match=False)
                print(f"找到的文件: {apk_files}") 

                for apk in apk_files:
                    ZipUtils.extract_zip(zip_path=apk, dest_dir="Temp")
                shutil.rmtree(Temp_name)
            os.remove(downloader_name)
        else:
            exe_name = "BlueArchive.exe"
            temp_exe_dir = f"Temp_{Config.server}"
            FileDownloader(url=apk_url, verbose=True).save_file(exe_name)
            CommandUtils.run_command("7z", "x", exe_name, f"-o{temp_exe_dir}", "-y")
            asar_path = os.path.abspath(os.path.join(temp_exe_dir, "$PLUGINSDIR", "resources", "app.asar"))
            AsarUtils.extract_asar(asar_path=asar_path, dest_dir="BA-PC-SRC")
            shutil.rmtree(temp_exe_dir)
            os.remove(exe_name)

    def get_apk_url(self):
        if Config.server != "JPPC":
            server_id = {
                "JP": 124755,
                "GL": 139059,
                "CN": 151329
            }
            game_id = server_id.get(Config.server)
            url = f"https://api.3839app.com/cdn/android/gameintro-home-1546-id-{game_id}-packag--level-2.htm"
            response = FileDownloader(url=url).get_response()

            downinfo = response.json().get("result", {}).get("data", {}).get("downinfo", {})
            
            apk_url = downinfo.get("apkurl")
            version = downinfo.get("version")
        else:
            html = FileDownloader("https://bluearchive.jp/").get_response().text
            app_js = re.search(r'https://webusstatic\.yo-star\.com/bluearchive_jp_web/js/app\.[0-9a-f]+\.js', html).group(0)
            js_content = FileDownloader(app_js).get_response().text

            match = re.search(r'(https://[^\s"\'()]+BlueArchive_JP_Gamelauncher-([0-9.]+)-setup\.exe)', js_content)
            apk_url = match.group(1)
            version = match.group(2)
        return apk_url, version

    def get_game_main_config(self, files_path) -> str:
        extractor = BundleExtractor(install_dir="tools", EXTRACT_DIR="Extracted")
        config_data = {}

        if Config.server == "GL":
            return config_data

        url_objs = extractor.search_unity_pack(
            os.path.join(files_path, "assets", "bin", "Data"), 
            data_type=["TextAsset"], 
            data_name=["GameMainConfig"], 
            condition_connect=True
        )

        if url_objs:
            raw_script = url_objs[0].read().m_Script
            # GL服的没有进行研究，故此这里不写
            if Config.server == "JP" or Config.server == "JPPC":
                ciphers = {
                    "ServerInfoDataUrl": "X04YXBFqd3ZpTg9cKmpvdmpOElwnamB2eE4cXDZqc3ZgTg==",
                    "DefaultConnectionGroup": "tSrfb7xhQRKEKtZvrmFjEp4q1G+0YUUSkirOb7NhTxKfKv1vqGFPEoQqym8=",
                    "SkipTutorial": "8AOaQvLC5wj3A4RC78L4CNEDmEL6wvsI",
                    "Language": "wL4EWsDv8QX5vgRaye/zBQ==",
                }
            elif Config.server == "CN":
                ciphers = {
                    "ServerInfoDataUrl": "X04YXBFqd3ZpTg9cKmpvdmpOElwnamB2eE4cXDZqc3ZgTg==",
                    "SkipTutorial": "8AOaQvLC5wj3A4RC78L4CNEDmEL6wvsI",
                    "ServerName": "ioIcSFNXEmG8ggtIb1cFYbSCHEg=",
                    "VersionCode": "nYFvU65AaVWigWVTskBZVaSBblO5QA==",
                    "PlatformID": "wBgDdzgJJFH2GAB3Kwk9UdkYK3c=",
                    "ChannelID": "SiMCCCkfsBxnIw8IJB+XHE0j",
                }
            b64_data = base64.b64encode(raw_script).decode("utf-8")
            json_str = convert_string(b64_data, create_key("GameMainConfig"))
            raw_json_obj = json.loads(json_str)
                
            for key, cipher_key in ciphers.items():
                if cipher_key in raw_json_obj:
                    encrypted_value = raw_json_obj[cipher_key]
                    config_data[key] = convert_string(encrypted_value, create_key(key))
        return config_data

    def get_server_url(self, version) -> str:
        if Config.server == "JP"or Config.server == "JPPC":
            config_data = self.get_game_main_config("Temp")
            return config_data.get("ServerInfoDataUrl"), None, None

        elif Config.server == "GL":
            build_number = version.split(".")[-1]    
            body = {
                "market_game_id": "com.nexon.bluearchive",
                "market_code": "playstore",
                "curr_build_version": version,
                "curr_build_number": build_number
            }
            print(f"[*] 正在向服务器请求版本: {version} (Build: {build_number})")
            downloader = FileDownloader("https://api-pub.nexon.com/patch/v1.1/version-check", request_method="post", json=body)        
            resp = downloader.get_response()

            if resp and resp.status_code == 200:
                data = resp.json()
                resource_path = data.get("patch", {}).get("resource_path")
                notice("获取成功。")
                return resource_path, None, None
            else:
                notice("请求失败。")
                return None, None, None

        elif Config.server == "CN":
            config_data = self.get_game_main_config("Temp")
            # server_url = json.loads(config_data.get("ServerInfoDataUrl"))[0]
            # 两个服务器暂时不可使用
            server_url = "https://gs-api.bluearchive-cn.com/api/state"
            platform_id = config_data.get("PlatformID")
            channel_id = config_data.get("ChannelID")
            return server_url, platform_id, channel_id

    def get_addressable_catalog_url(self, server_url: str, platform_id: str = None, channel_id: str = None, version: str = None) -> str:
        if Config.server == "JP"or Config.server == "JPPC":
            downloader = FileDownloader(server_url)

            data = downloader.get_response().json()
            connection_groups = data.get("ConnectionGroups", [])
            override_groups = connection_groups[0].get("OverrideConnectionGroups", [])
            latest_catalog_url = override_groups[-1].get("AddressablesCatalogUrlRoot")

            return latest_catalog_url, None, None, None, None

        elif Config.server == "GL":
            latest_catalog_url = server_url.rsplit("/", 1)[0] if server_url and "/" in server_url else None
            return latest_catalog_url, None, None, None, None

        elif Config.server == "CN":
            headers = {
                "APP-VER": version,
                "PLATFORM-ID": platform_id,
                "CHANNEL-ID": channel_id
            }
            downloader = FileDownloader(server_url, headers=headers)

            data = downloader.get_response().json()
            latest_catalog_url = data.get("AddressablesCatalogUrlRoots")[0]
            resource_version = data.get("ResourceVersion")
            table_version = data.get("TableVersion")
            media_version = data.get("MediaVersion")
            patch_version = data.get("PatchVersion")
            
            return latest_catalog_url, resource_version, table_version, media_version, patch_version

    def get_game_launcher_config(self, version):
        api_headers = {
            "Authorization": json.dumps({
                "head": {
                    "game_tag": "BlueArchive_JP",
                    "time": 1768991129,
                    "version": version
                },
                "sign": "9ea3c5927d09f0e4073ed15ec532bc7e"
            })
        }
        url = "https://api-launcher-jp.yo-star.com/api/launcher/game/config"
        response = FileDownloader(url=url, headers=api_headers).get_response()
        
        if response and response.status_code == 200:
            data = response.json().get("data", {})
            game_latest_version = data.get("game_latest_version")
            game_latest_file_path = data.get("game_latest_file_path")

            file_name = os.path.basename(game_latest_file_path)
            resource_version = os.path.splitext(file_name)[0]
            return game_latest_version, game_latest_file_path, resource_version
        return None, None, None

    def get_zip_config_url(self, version, latest_version, file_path):
        api_headers = {
            "Authorization": json.dumps({
                "head": {
                    "game_tag": "BlueArchive_JP",
                    "time": 1768991129,
                    "version": version
                },
                "sign": "9ea3c5927d09f0e4073ed15ec532bc7e"
            })
        }
        params = {
            "version": latest_version,
            "file_path": file_path
        }
        url = "https://api-launcher-jp.yo-star.com/api/launcher/game/config/json"
        
        response = FileDownloader(
            url=url, 
            headers=api_headers, 
            params=params
        ).get_response()
        
        if response and response.status_code == 200:
            return response.json().get("data", {}).get("url")
        return None

    def download_launcher_assets(self, res_version, zip_config_url, targets, dest_dir):
        """
        下载指定的游戏资源文件。
        
        :param res_version: 资源版本字符串 (如 BlueArchive_JP-1.68.421271-game)
        :param zip_config_url: 配置 JSON 的下载地址
        :param targets: 需要下载的文件名列表 (如 ["resources.assets", "resources.assets.resS"])
        :param dest_dir: 下载到的目标路径 (如 "Temp/assets/bin/Data")
        """
        os.makedirs(dest_dir, exist_ok=True)

        local_json_name = zip_config_url.split("/")[-1]
        downloader = FileDownloader(url=zip_config_url)
        
        if downloader.save_file(local_json_name):
            with open(local_json_name, 'r', encoding='utf-8') as f:
                config_content = json.load(f)
            
            base_download_url = "https://launcher-pkg-ba-jp.yo-star.com"
            
            for file_info in config_content.get("file", []):
                file_path = file_info.get("path", "")
                file_name = os.path.basename(file_path)
                
                if file_name in targets:
                    full_url = f"{base_download_url}/{res_version}{file_path}"
                    local_save_path = os.path.join(dest_dir, file_name)
                    
                    notice(f"正在从 Launcher 下载资源: {file_name}")
                    dl = FileDownloader(url=full_url, enable_progress=True)
                    dl.save_file(local_save_path)
            return True
        return False
