import json
import re
import os
from xtractor.catalog import CatalogMemoryPack
from lib.console import notice

def update_media_catalog():
    CatalogMemoryPack_obj = CatalogMemoryPack(install_dir = "tools")

    with open("MediaCatalog.json", "r", encoding="utf-8") as f:
        media_data = json.load(f)

    with open("other/Voice.json", "r", encoding="utf-8") as f:
        voice_data = json.load(f)

    table = media_data.get("Table", {})

    for key in voice_data:
        item = voice_data[key]
        zip_name = item.get("zip_name")
        new_key = f"audio/voc_cn/cn_main/{zip_name.replace('.zip', '').lower()}"
        is_prologue = False
        match = re.search(r"Main_(\d+)\.zip", zip_name)

        if match:
            number = int(match.group(1))
            if 11000 <= number < 11010:
                is_prologue = True

        table[new_key] = {
            "path": f"GameData/Audio/VOC_CN/{zip_name}",
            "FileName": zip_name,
            "Bytes": item.get("zip_size"),
            "Crc": item.get("zip_crc32"),
            "IsPrologue": is_prologue,
            "IsSplitDownload": False,
            "MediaType": 1
        }

    media_data["Table"] = table

    with open("MediaCatalog.json", "w", encoding="utf-8") as f:
        json.dump(media_data, f, indent=4, ensure_ascii=False)
    
    notice("MediaCatalog 更新完成。")

    success, error_msg = CatalogMemoryPack_obj.run(
        server="JP",
        mode="serialize",
        catalog_type="Media",
        input_path="MediaCatalog.json",
        output_path="MediaCatalog.bytes"
    )

    if not success:
        print(f"执行出错：{error_msg}")
    else:
        notice("MediaCatalog序列化完成。")

    os.remove("MediaCatalog.json")
    os.remove("Download/MediaCatalog.bytes")

def update_voice_excel(voice_excel_path, scenario_script_path):
    with open(voice_excel_path, "r", encoding="utf-8") as f:
        excel_list = json.load(f)

    with open(scenario_script_path, "r", encoding="utf-8") as f:
        scenario_list = json.load(f)

    with open("other/Voice.json", "r", encoding="utf-8") as f:
        voice_data = json.load(f)

    existing_ids = {item["Id"] for item in excel_list}
    current_max_unique_id = max((item["UniqueId"] for item in excel_list), default=0)
    current_id_counter = 2026430 # 这是写这段代码的日期，很有纪念意义不是吗

    audio_name_to_id = {}
    
    for key in voice_data:
        item = voice_data[key]
        zip_folder = item.get("zip_name").replace(".zip", "")
        zip_files = item.get("zip_files", [])

        for ogg_file in zip_files:
            while current_id_counter in existing_ids:
                current_id_counter += 1
            
            current_max_unique_id += 1
            audio_name = ogg_file.replace(".ogg", "")
            
            # 记录映射
            audio_name_to_id[audio_name] = current_id_counter
            
            new_entry = {
                "UniqueId": current_max_unique_id,
                "Id": current_id_counter,
                "Nation": ["All"],
                "Path": [f"Audio/VOC_CN/{zip_folder}/{audio_name}"],
                "Volume": [1.0]
            }
            
            excel_list.append(new_entry)
            existing_ids.add(current_id_counter)
            current_id_counter += 1

    with open(voice_excel_path, "w", encoding="utf-8") as f:
        json.dump(excel_list, f, indent=4, ensure_ascii=False)
    
    notice("VoiceExcel.json 更新完成。")
        
    for entry in scenario_list:
        voice_id_val = entry.get("VoiceId")
        if voice_id_val == "":
            entry["VoiceId"] = 0
        elif isinstance(voice_id_val, str):
            # 如果映射表里有这个音频名，则替换为 ID
            if voice_id_val in audio_name_to_id:
                entry["VoiceId"] = audio_name_to_id[voice_id_val]
        
    with open(scenario_script_path, "w", encoding="utf-8") as f:
        json.dump(scenario_list, f, indent=4, ensure_ascii=False)
    notice("ScenarioScriptExcel.json 更新完成。")

if __name__ == "__main__":
    process_media_catalog()
