import shutil
import json
import re
import os
import zipfile
import base64
from pathlib import Path
from lxml import etree
from utils.util import CommandUtils, ZipUtils, FileUtils
from utils.config import Config
from utils.regions import Server
from lib.downloader import FileDownloader
from distutils.dir_util import copy_tree
from xtractor.bundle import BundleExtractor
from lib.encryption import create_key, convert_string, encrypt_string, xor

class ApkTools:
    def __init__(self, repo="BAJpApkSrc"):
        self.repo = Path(repo)

    def _run_apktool(self, args):
        success, error = CommandUtils.run_command("java", "-jar", str(self.repo / "apktool.jar"), *args)
        if not success:
            raise Exception(f"apktool failed: {error}")
        return success

    def extract(self, apk_path, output_dir):
        out_path = Path(output_dir)
        if out_path.exists():
            shutil.rmtree(out_path)
        print("正在解包……")
        return self._run_apktool(["d", "-f", str(apk_path), "-o", str(out_path)])

    def build(self, input_dir, output_apk):
        print("正在打包……")
        return self._run_apktool(["b", str(input_dir), "-o", str(output_apk)])

    def sign(self, apk_path, out_path):
        success, error = CommandUtils.run_command(
            'java', '-jar', str(self.repo / "apksigner.jar"), 'sign', '--ks', str(self.repo / "beichen.jks"),
            '--ks-pass', 'pass:北辰汉化组a', '--key-pass', 'pass:北辰汉化组a',
            '--out', out_path, '--v1-signing-enabled', 'true',
            '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'true', apk_path
        )
        if not success:
            raise Exception(f"apksigner failed: {error}")
        else:
            print("签名完成。")
        return success

    def modify_manifest(self, output_dir, coexist="", trust_cert=False):
        manifest_path = Path(output_dir) / "AndroidManifest.xml"
        content = manifest_path.read_text(encoding='utf-8')

        if coexist:
            print(f"确认为共存版，包名{coexist}开始修改……")
            host_matches = list(re.finditer(r'(android:host=")([^"]+)(")', content))
            host_values = [m.group(2) for m in host_matches]
            for i, m in enumerate(host_matches):
                content = content.replace(m.group(0), f'{m.group(1)}__HOST_TEMP_{i}__{m.group(3)}')
            
            content = content.replace('com.YostarJP.BlueArchive', coexist)
            patterns = [
                'com.google.android.gms.permission.AD_ID',
                'com.facebook.katana.provider.PlatformProvider',
                'com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE',
                'com.google.android.c2dm.permission.RECEIVE',
                'android.permission.CHANGE_NETWORK_STATE',
                'android.permission.WRITE_SETTINGS'
            ]    
            for p in patterns:
                content = content.replace(p, f'{coexist}_{p}')
            for i, h in enumerate(host_values):
                content = content.replace(f"__HOST_TEMP_{i}__", h)
            print("包名修改完成。")
        print("正在合并apk……")
        root = etree.fromstring(content.encode('utf-8'))
        if trust_cert:
            app_element = root.find(".//application")
            if app_element is not None:
                app_element.set('{http://schemas.android.com/apk/res/android}networkSecurityConfig', '@xml/network_security_config')

        for attr in ['{http://schemas.android.com/apk/res/android}requiredSplitTypes', '{http://schemas.android.com/apk/res/android}splitTypes']:
            if attr in root.attrib:
                del root.attrib[attr]

        ns = {'android': 'http://schemas.android.com/apk/res/android'}
        for meta in root.findall(".//meta-data", namespaces=ns):
            if meta.get('{http://schemas.android.com/apk/res/android}name') == "com.android.vending.splits.required":
                meta.set('{http://schemas.android.com/apk/res/android}name', 'com.android.dynamic.apk.fused.modules')
                meta.set('{http://schemas.android.com/apk/res/android}value', 'UnityDataAssetPack,base')
        
        manifest_path.write_text(etree.tostring(root, encoding='utf-8', pretty_print=True).decode('utf-8'), encoding='utf-8')
        print("apk合并完成。")

    def modify_resources(self, output_dir, modifylogin=""):
        base_path = Path(output_dir)
        for p in base_path.glob("res/values*/strings.xml"):
            try:
                content = p.read_text(encoding='utf-8')
                if '<string name="app_name">ブルアカ</string>' in content:
                    p.write_text(content.replace('<string name="app_name">ブルアカ</string>', '<string name="app_name">蔚蓝档案</string>'), encoding='utf-8')
            except:
                pass
        print("apk名修改完成。")
        if modifylogin:
            print("正在修改yostar登录文本。")
            try:
                res_data = json.loads((self.repo / "resources.json").read_text(encoding='utf-8'))
                ja_path = base_path / "res/values-ja/strings.xml"
                content = ja_path.read_text(encoding='utf-8')
                for item in res_data:
                    content = re.sub(rf'(?s)<string name="{item["name"]}">.*?</string>', f'<string name="{item["name"]}">{item["text"]}</string>', content)
                ja_path.write_text(content, encoding='utf-8')
            except:
                pass
            print("yostar登录文本修改完成。")            
            gt4_path = base_path / "assets" / "gt4.js"
            if gt4_path.exists():
                content = gt4_path.read_text(encoding='utf-8')
                old_str = "lang: config.language? config.language : navigator.appName === 'Netscape' ? navigator.language.toLowerCase() : navigator.userLanguage.toLowerCase()"
                if old_str in content:
                    gt4_path.write_text(content.replace(old_str, f"lang: '{modifylogin}'"), encoding='utf-8')
                    print("gt4登录文本修改完成。")

    def modify_sdk_url(self, main_output_path, sdkurl):
        sdk_config_path = main_output_path / "assets" / "SDKConfigSettings.json"
        sdk_config = json.loads(sdk_config_path.read_text(encoding="utf-8"))
        sdk_config["Regions"]["Jp"]["Sdk_Url"] = sdkurl
        sdk_config_path.write_text(json.dumps(sdk_config, indent=4, ensure_ascii=False), encoding="utf-8")
        print("sdkurl修改完成。")

    def modify_game_main_config(self, main_output_path, gamemainconfig, modified_dir):
        data_folder = str(main_output_path / "assets" / "bin" / "Data")
        url_objs = BundleExtractor().search_unity_pack(data_folder, data_type=["TextAsset"], data_name=["GameMainConfig"], condition_connect=True)
        if not url_objs: return

        raw_script = url_objs[0].read().m_Script
        if isinstance(raw_script, str):
            raw_script = raw_script.encode("utf-8", "surrogateescape")
        
        b64_data = base64.b64encode(raw_script).decode("utf-8")
        raw_json_obj = json.loads(convert_string(b64_data, create_key("GameMainConfig")))
        
        ciphers = {
            "ServerInfoDataUrl": "X04YXBFqd3ZpTg9cKmpvdmpOElwnamB2eE4cXDZqc3ZgTg==",
            "DefaultConnectionGroup": "tSrfb7xhQRKEKtZvrmFjEp4q1G+0YUUSkirOb7NhTxKfKv1vqGFPEoQqym8=",
            "SkipTutorial": "8AOaQvLC5wj3A4RC78L4CNEDmEL6wvsI",
            "Language": "wL4EWsDv8QX5vgRaye/zBQ==",
        }
        gmc_dict = json.loads(gamemainconfig)
        for k, v in gmc_dict.items():
            if k in ciphers:
                raw_json_obj[ciphers[k]] = encrypt_string(v, create_key(k))

        new_raw_script = xor(json.dumps(raw_json_obj, separators=(',', ':')).encode("utf-16le"), create_key("GameMainConfig"))
        modified_dir.mkdir(parents=True, exist_ok=True)
        (modified_dir / "GameMainConfig").write_bytes(new_raw_script)
        print("GameMainConfig修改完成。")

    def apply_bundle_modifications(self, main_output_path, modified_dir):
        if not modified_dir.exists(): return
        extractor = BundleExtractor()
        data_folder = str(main_output_path / "assets" / "bin" / "Data")
        for root, _, files in os.walk(modified_dir):
            for file_name in files:
                extractor.replace_asset_from_file(data_folder, Path(root, file_name).stem, str(Path(root) / file_name), crc_fix=True)
        print("bundle文件修改完成。")

    def main(self, coexist="", sdkurl="", gamemainconfig="", trustcert=False, modifylogin="", replace=True, modifybundle=True, server="JP"):
        Config.server = server
        base_dir = Path("Temp")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        decoded_path = base_dir / "Decoded"
        temp_extract_path = base_dir / "TempExtract"
        main_output_path = base_dir / "MainOutput"
        apk_path = base_dir / f"Temp_{Config.server}.apk"
        dex_backup_path = base_dir / "DexBackup"
        dex_backup_path.mkdir(exist_ok=True)

        apk_url, _ = Server().get_apk_url()
        FileDownloader(url=apk_url, headers={"User-Agent": "Androidkb"}).save_file(str(apk_path))

        ZipUtils.extract_zip(str(apk_path), str(decoded_path / "assets"), keywords=["assets/com.YostarJP.BlueArchive"])
        apks = FileUtils.find_files(str(decoded_path / "assets"), ["UnityDataAssetPack", "config", "BlueArchive"])
        main_apk = next(a for a in apks if "UnityDataAssetPack" not in a and "config" not in a)
        others = [a for a in apks if a != main_apk]

        with zipfile.ZipFile(main_apk, 'r') as z:
            for dex in [f for f in z.namelist() if f.startswith("classes") and f.endswith(".dex")]:
                (dex_backup_path / dex).write_bytes(z.read(dex))

        self.extract(main_apk, main_output_path)
        ZipUtils.extract_zip(others, str(temp_extract_path))
        for folder in ["lib", "assets"]:
            src = temp_extract_path / folder
            if src.exists():
                copy_tree(str(src), str(main_output_path / folder))

        shutil.rmtree(decoded_path)
        shutil.rmtree(temp_extract_path)
        apk_path.unlink()

        yml_path = main_output_path / "apktool.yml"
        yml_content = yml_path.read_text(encoding='utf-8')
        if 'doNotCompress:' in yml_content and '- mp4' not in yml_content:
            yml_path.write_text(yml_content.replace('doNotCompress:', 'doNotCompress:\n- mp4'), encoding='utf-8')
        print("APKToolyml修改完成。")

        self.modify_manifest(main_output_path, coexist, trustcert)
        if trustcert:
            shutil.copy(str(self.repo / "network_security_config.xml"), str(main_output_path / "res" / "xml" / "network_security_config.xml"))

        self.modify_resources(main_output_path, modifylogin)

        if replace and (self.repo / "Replace").exists():
            copy_tree(str(self.repo / "Replace"), str(main_output_path / "assets"))

        if sdkurl:
            self.modify_sdk_url(main_output_path, sdkurl)

        modified_dir = self.repo / "Modified"
        if gamemainconfig:
            self.modify_game_main_config(main_output_path, gamemainconfig, modified_dir)
            
        if modifybundle:
            self.apply_bundle_modifications(main_output_path, modified_dir)

        raw_apk, temp_align, final_apk = Path("unaligned.apk"), Path("temp.apk"), Path("蔚蓝档案.apk")
        self.build(main_output_path, str(raw_apk))
        
        TARGET_DATE = (1981, 1, 1, 0, 0, 0)
        with zipfile.ZipFile(raw_apk, 'r') as zin, zipfile.ZipFile(temp_align, 'w') as zout:
            for item in zin.infolist():
                if item.filename.startswith("classes") and item.filename.endswith(".dex"): continue
                new_item = zipfile.ZipInfo(item.filename)
                new_item.date_time = TARGET_DATE
                new_item.external_attr = item.external_attr
                new_item.compress_type = item.compress_type
                zout.writestr(new_item, zin.read(item.filename))
            for dex_file in dex_backup_path.iterdir():
                new_item = zipfile.ZipInfo(dex_file.name)
                new_item.date_time = TARGET_DATE
                new_item.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(new_item, dex_file.read_bytes())
        raw_apk.unlink()
        
        CommandUtils.run_command("zipalign", "-p", "-f", "4", str(temp_align), str(final_apk))
        temp_align.unlink()
        
        self.sign(str(final_apk), str(final_apk))

        shutil.rmtree(dex_backup_path)
        shutil.rmtree(main_output_path)
