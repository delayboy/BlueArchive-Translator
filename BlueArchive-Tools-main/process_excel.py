import os
import sys
import json
from argparse import ArgumentParser
from pathlib import Path
from utils.config import Config
from xtractor.table import TableProcess
from utils.util import CommandUtils
from lib.encryption import calculate_crc
from xtractor.catalog import CatalogMemoryPack


def parse_args():
    p = ArgumentParser(description="JSON 数据提取/打包工具")
    p.add_argument("table_file_folder", type=Path)
    p.add_argument("file_path", type=Path)
    p.add_argument("server", choices=["CN", "GL", "JP"])
    p.add_argument("type", choices=["Extract", "Repack"])
    p.add_argument("--catalog", action="store_true")
    p.add_argument("--name", action="store_true")
    p.add_argument("--db_key", type=str)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    args.file_path.mkdir(parents=True, exist_ok=True)
    Config.server = args.server

    if args.db_key:
        Config.db_password = args.db_key

    catalog_data = None
    if args.type == "Repack" and args.catalog:  # 改成windows客户端
        CommandUtils.run_command(sys.executable, "-m", "get.get_catalog", args.server, "Table", "Windows")
        with open("Download/TableCatalog.json", "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

    process = TableProcess(str(args.table_file_folder), str(args.file_path), "FlatData")

    if os.path.exists(os.path.join(args.table_file_folder, "ExcelDB.db")):
        process.process_table("ExcelDB.db", args.type, True)
        if catalog_data and "ExcelDB.db" in catalog_data.get("Table", {}):
            file_path = os.path.join(args.table_file_folder, "ExcelDB.db")
            new_crc = calculate_crc(file_path)
            catalog_data["Table"]["ExcelDB.db"]["Size"] = os.path.getsize(file_path)
            catalog_data["Table"]["ExcelDB.db"]["Crc"] = new_crc
            if args.name:
                new_name = f"6993339912994747134_{new_crc}"
                os.rename(file_path, os.path.join(args.table_file_folder, new_name))

    if os.path.exists(os.path.join(args.table_file_folder, "Excel.zip")):
        process.process_table("Excel.zip", args.type)
        if catalog_data and "Excel.zip" in catalog_data.get("Table", {}):
            file_path = os.path.join(args.table_file_folder, "Excel.zip")
            new_crc = calculate_crc(file_path)
            catalog_data["Table"]["Excel.zip"]["Size"] = os.path.getsize(file_path)
            catalog_data["Table"]["Excel.zip"]["Crc"] = new_crc
            if args.name:
                new_name = f"16300795542385574620_{new_crc}"
                os.rename(file_path, os.path.join(args.table_file_folder, new_name))

    if catalog_data:
        with open("Download/TableCatalog.json", "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2, ensure_ascii=False)

        if Config.server != "CN":
            CatalogMemoryPack(install_dir="tools").run(
                server=args.server, mode="serialize", catalog_type="table",
                input_path=os.path.abspath("Download/TableCatalog.json"),
                output_path=os.path.abspath("Download/TableCatalog.bytes")
            )
