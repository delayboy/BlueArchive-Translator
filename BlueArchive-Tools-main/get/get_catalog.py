import os
import requests
import dotenv
from argparse import ArgumentParser
from typing import Optional, Tuple
from lib.downloader import FileDownloader
from lib.console import notice
from utils.config import Config
from utils.util import ZipUtils
from xtractor.catalog import CatalogMemoryPack, CNMXCatalog

def parse_args():
    p = ArgumentParser(description="维护更新")
    p.add_argument("server", type=str, choices=["CN", "GL", "JP"], help="服务器区域")
    p.add_argument("type", type=str, choices=["Media", "Table", "Bundle"], help="资源类型")
    p.add_argument("client", type=str, choices=["Android", "iOS", "Windows"], help="客户端平台")
    return p.parse_args()

def process_cn_manifest(args, base_url: str):
    if args.type == "Media":
        url = f"{base_url}/Manifest/MediaResources/{os.getenv('MediaVersion')}/MediaManifest"
        output_path = "Download/MediaManifest"
        
        FileDownloader(url, verbose=False).save_file(output_path)
        
        with open(output_path, "r", encoding="utf-8") as manifest_file:
            catalog_content = CNMXCatalog(manifest_file.read()).parse_media_manifest()
            
        with open("Download/MediaCatalog.json", "w", encoding="utf-8") as json_file:
            json_file.write(catalog_content)
    
    elif args.type == "Bundle" and args.client != "Windows":
        url = f"{base_url}/AssetBundles/Catalog/{os.getenv('ResourceVersion')}/{args.client}/bundleDownloadInfo.json"
        FileDownloader(url, verbose=False).save_file("Download/BundlePackingInfo.json")
        
    elif args.type == "Table":
        url = f"{base_url}/Manifest/TableBundles/{os.getenv('TableVersion')}/TableManifest"
        FileDownloader(url, verbose=False).save_file("Download/TableCatalog.json")

def resolve_download_metadata(args, base_url: str) -> Tuple[Optional[str], Optional[str]]:
    server, resource_type, platform = args.server, args.type, args.client
    
    if server == "JP":
        if resource_type == "Media":
            suffix = "MediaResources-Windows" if platform == "Windows" else "MediaResources"
            return f"{base_url}/{suffix}/Catalog/MediaCatalog.bytes", "MediaCatalog.bytes"
        if resource_type == "Bundle":
            return f"{base_url}/{platform}_PatchPack/BundlePackingInfo.bytes", "BundlePackingInfo.bytes"
        if resource_type == "Table":
            return f"{base_url}/TableBundles/TableCatalog.bytes", "TableCatalog.bytes"
            
    if server == "GL":
        if resource_type == "Media":
            return f"{base_url}/Catalog/MediaResources/MediaCatalog.bytes", "MediaCatalog.bytes"
        if resource_type == "Table":
            return f"{base_url}/Catalog/TableBundles/TableCatalog.bytes", "TableCatalog.bytes"
        if resource_type == "Bundle" and platform == "Android":
            return os.getenv('ServerInfoDataUrl'), "BundlePackingInfo.json"
            
    return None, None

def run_deserialization(args, filename: str):
    input_full_path = os.path.abspath(f"Download/{filename}")
    output_full_path = os.path.abspath(f"Download/{filename.replace('.bytes', '.json')}")
    
    CatalogMemoryPack(install_dir="tools").run(
        server=args.server,
        mode="deserialize",
        catalog_type=args.type,
        input_path=input_full_path,
        output_path=output_full_path
    )

def main():
    args = parse_args()
    Config.server = args.server
    
    dotenv.load_dotenv(f"other/BA_{Config.server}.env")
    base_url = os.getenv('AddressableCatalogUrl')
    
    url_to_check = None
    if args.server == "CN":
        if args.type == "Media":
            url_to_check = f"{base_url}/Manifest/MediaResources/{os.getenv('MediaVersion')}/MediaManifest"
        elif args.type == "Bundle":
            url_to_check = f"{base_url}/AssetBundles/Catalog/{os.getenv('ResourceVersion')}/{args.client}/bundleDownloadInfo.json"
        elif args.type == "Table":
            url_to_check = f"{base_url}/Manifest/TableBundles/{os.getenv('TableVersion')}/TableManifest"
    else:
        url_to_check, _ = resolve_download_metadata(args, base_url)

    # 判断服务器开没开
    if url_to_check:
        try:
            res = requests.head(url_to_check, timeout=10)
            if res.status_code != 200:
                res = requests.get(url_to_check, stream=True, timeout=10)
                if res.status_code != 200:
                    return
        except:
            return

    os.makedirs("Download", exist_ok=True)

    if args.server == "CN":
        process_cn_manifest(args, base_url)
    else:
        url, filename = resolve_download_metadata(args, base_url)
        
        if url and filename:
            if os.path.exists(f"Download/{filename}"):
                print(f"[get_catalog]已存在{filename}文件，跳过下载阶段")
            else:
                FileDownloader(url).save_file(f"Download/{filename}")
                if args.server == "JP" and args.type == "Bundle" and args.client != "Windows":
                    zip_url = f"{base_url}/{args.client}_PatchPack/catalog_{args.client}.zip"
                    zip_path = f"Download/catalog_{args.client}.zip"
                    FileDownloader(zip_url).save_file(zip_path)
                    ZipUtils.extract_zip(zip_path, "Download")

            run_deserialization(args, filename)
            
    with open("CATALOG_FOUND", "w") as f:
        f.write("1")

if __name__ == "__main__":
    main()
