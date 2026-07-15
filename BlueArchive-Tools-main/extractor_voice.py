import os
import json
import zipfile
import shutil
import time

from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from lib.downloader import FileDownloader
from xtractor.catalog import CNMXCatalog
from lib.encryption import calculate_crc, zip_password
from PyCriCodecs import *
from utils.util import ZipUtils

load_dotenv("other/BA_CN.env")

base_url = os.getenv("AddressableCatalogUrl")
media_ver = os.getenv("MediaVersion")

voice_json_path = "other/Voice.json"

# 初始化
if not os.path.exists(voice_json_path):
    with open(voice_json_path, "w", encoding="utf-8") as f:
        json.dump({"CN": {}}, f)

def process(files_info):
    downloaded_paths = []
    # 确保awb先被下载，否则单acb会解析错误
    for path, info in sorted(files_info, key=lambda x: x[0], reverse=True):
        file_hash = info["Hash"]
        download_url = f"{base_url}/pool/MediaResources/{file_hash[:2]}/{file_hash}"
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if FileDownloader(url=download_url).save_file(path):
            downloaded_paths.append(path)
            if path.endswith(".acb"):
                # 基于acb文件名生成的Temp路径
                temp = os.path.join("Temp", os.path.splitext(os.path.basename(path))[0])
                os.makedirs(temp, exist_ok=True)
                
                acb_obj = ACB(path)
                acb_obj.extract(dirname=temp, decode=True, key=0)

                extracted = [f for f in os.listdir(temp) if os.path.isfile(os.path.join(temp, f))]
                # 把Temp的文件压缩为zip到Voice文件夹
                # zip名为提取的第一个文件，去掉最后一个_后面的所有内容
                if extracted:
                    extracted.sort()
                    zip_name = f"{extracted[0].rsplit('_', 1)[0]}.zip"
                    zip_path = os.path.join("Voice", zip_name)
                    password = zip_password(zip_name.lower())
                    success = ZipUtils.create_zip(
                        file_paths=extracted,
                        dest_zip=zip_path,
                        base_dir=temp,
                        password=password,
                        verbose=True
                    )
                    if success:
                        crc32_val = calculate_crc(zip_path)
                        size_val = os.path.getsize(zip_path)
                        
                        group_key = os.path.splitext(path)[0]
                        hashes = {os.path.splitext(p)[1][1:]: inf["Hash"] for p, inf in files_info}
                        
                        # 生成Voice.json，用于校验文件完整性并保存zip crc size
                        with open(voice_json_path, "r+", encoding="utf-8") as f:
                            v_data = json.load(f)
                            if "CN" not in v_data:
                                v_data["CN"] = {}
                            v_data["CN"][group_key] = {
                                "acb_hash": hashes.get("acb"),
                                "awb_hash": hashes.get("awb"),
                                "zip_name": zip_name,
                                "zip_crc32": crc32_val,
                                "zip_size": size_val,
                                "zip_password": password.decode(),
                                "zip_files": extracted
                            }
                            f.seek(0)
                            json.dump(v_data, f, indent=4)
                            f.truncate()

                shutil.rmtree(temp)

    # 处理完成后删除下载的原始 acb/awb 文件
    for p in downloaded_paths:
        if os.path.exists(p):
            os.remove(p)

if __name__ == "__main__":
    while True:
        downloader = FileDownloader(url=f"{base_url}/Manifest/MediaResources/{media_ver}/MediaManifest", verbose=False)    
        if downloader.save_file("MediaManifest"):
            # 把MediaManifest转为人能看懂的json格式
            print("开始解析...")
            with open("MediaManifest", "r", encoding="utf-8") as f:
                catalog = CNMXCatalog(f.read())

            manifest_json = catalog.parse_media_manifest()
            with open("MediaManifest.json", "w", encoding="utf-8") as f:
                f.write(manifest_json)
                
            data = json.loads(manifest_json)
            groups = {}

            with open(voice_json_path, "r", encoding="utf-8") as f:
                existing_records = json.load(f).get("CN", {})

            for path, info in data.items():
                if "voc_cn" in path and info["MediaType"] in ["acb", "awb"]:
                    # 只处理中配的acb，awb文件，一对acb，awb为一组
                    key = os.path.splitext(path)[0]
                    groups.setdefault(key, []).append((path, info))

            filtered_groups = {}
            for key, files in groups.items():
                if key in existing_records:
                    record = existing_records[key]
                    current_hashes = {os.path.splitext(p)[1][1:]: inf["Hash"] for p, inf in files}
                    # 校验Hash与本地缓存是否相同
                    if record.get("acb_hash") == current_hashes.get("acb") and record.get("awb_hash") == current_hashes.get("awb"):
                        continue
                filtered_groups[key] = files

            if not filtered_groups:
                print("所有音频已处理完毕。")
                break

            print(f"开始处理 {len(filtered_groups)} 组音频...")

            completed = 0
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(process, g) for g in filtered_groups.values()]
                for future in futures:
                    future.result()
                    completed += 1
                    if completed % 50 == 0:
                        # 防卡死
                        os.system(f'cd Voice && git add *.zip && git commit -m "提交语音资源（50个/第{completed}组）" && git push')
                        print(f"进度报告：已完成 {completed} 组")
            os.system('cd Voice && git add . && git commit -m "提交语音资源（最后一组）" && git push')
            print("本轮处理结束，正在重新检查是否存在下载失败的文件...")
        else:
            print("文件下载失败，10秒后重试...")
            time.sleep(10)
    
    print("任务结束。")
