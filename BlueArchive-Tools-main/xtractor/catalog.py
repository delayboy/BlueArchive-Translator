import io
import struct
import json
import os
from utils.util import CommandUtils, ZipUtils, ToolManager
from lib.downloader import FileDownloader

class CNMXCatalog:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.media_type = {
            0: "none",
            1: "ogg",
            2: "mp4",
            3: "jpg",
            4: "png",
            5: "acb",
            6: "awb"
        }

    def parse_media_manifest(self):
        lines = self.raw_data.strip().split('\n')
        result = {}
        for line in lines:
            if not line.strip():
                continue

            parts = [p.strip() for p in line.rstrip(',').split(',')]

            if len(parts) >= 4:
                # 为确保Key值唯一，故此进行文件后缀拼接
                raw_key = parts[0]
                m_type_value = int(parts[2])
                media_type = self.media_type.get(m_type_value, str(m_type_value))
                unique_key = f"{raw_key}.{media_type}"            
                result[unique_key] = {
                    "Hash": parts[1],
                    "MediaType": media_type,
                    "Size": int(parts[3])
                }
        return json.dumps(result, indent=4, ensure_ascii=False)

class CatalogMemoryPack(ToolManager):
    def run(self, mode: str, server: str, catalog_type: str, input_path: str, output_path: str) -> tuple[bool, str]:
        bin_path = self.ensure_tool()
        # memorypack <mode> <server> <type> <input> <output>
        success, err = CommandUtils.run_command(
            bin_path, "memorypack", mode.lower(), server.lower(), catalog_type.lower(), input_path, output_path,
        )
        return success, err

