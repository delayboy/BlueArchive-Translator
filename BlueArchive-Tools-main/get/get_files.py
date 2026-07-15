import os
import json
import dotenv
from argparse import ArgumentParser
from lib.downloader import FileDownloader
from utils.config import Config

def parse_args():
    p = ArgumentParser(description="维护更新")
    p.add_argument("server", type=str, choices=["CN", "GL", "JP"], help="服务器区域")
    p.add_argument("type", type=str, choices=["Media", "Table", "Bundle"], help="资源类型")
    p.add_argument("client", type=str, choices=["Android", "iOS", "Windows"], help="客户端平台")
    p.add_argument("-f", "--files", nargs="+", help="文件列表")
    return p.parse_args()

def get_download_url(server, res_type, client, base_url, filename, catalog):
    if server == "JP":
        if res_type == "Table":
            return f"{base_url}/TableBundles/{filename}"
        if res_type == "Media":
            sub = "MediaResources-Windows" if client == "Windows" else "MediaResources"
            return f"{base_url}/{sub}/{filename}"
        if res_type == "Bundle":
            return f"{base_url}/{client}_PatchPack/{filename}"

    if server == "CN":
        if res_type == "Table":
            val = str(catalog.get("Table", {}).get(filename, {}).get("Crc", ""))
            return f"{base_url}/pool/TableBundles/{val[:2]}/{val}" if val else None
        if res_type == "Media":
            val = str(catalog.get(filename.lower(), {}).get("Hash", ""))
            return f"{base_url}/pool/MediaResources/{val[:2]}/{val}" if val else None
        if res_type == "Bundle":
            return f"{base_url}/AssetBundles/{client}/{filename}"

    if server == "GL":
        if res_type == "Table":
            return f"{base_url}/Preload/TableBundles/{filename}"
    
    return None

def main():
    args = parse_args()
    Config.server = args.server
    dotenv.load_dotenv(f"other/BA_{args.server}.env")
    base_url = os.getenv('AddressableCatalogUrl')

    catalog = {}
    if args.server == "CN" and args.files:
        cat_name = "TableCatalog.json" if args.type == "Table" else "MediaCatalog.json"
        with open(os.path.join("Download", cat_name), "r", encoding="utf-8") as f:
            catalog = json.load(f)

    os.makedirs("Download_Temp", exist_ok=True)

    for filename in (args.files or []):
        url = get_download_url(args.server, args.type, args.client, base_url, filename, catalog)
        if url:
            target_path = os.path.join("Download_Temp", filename)
            if FileDownloader(url, enable_progress=True).save_file(target_path):
                print(f"成功: {target_path}")

if __name__ == "__main__":
    main()
