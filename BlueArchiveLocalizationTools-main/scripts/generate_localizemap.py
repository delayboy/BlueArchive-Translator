import json
import re

with open("localization.cn.json", "r", encoding = "utf8") as dataf_cn: # https://schaledb.com/data/cn/students.min.json
    data_schaledb_cn = json.loads(dataf_cn.read())
with open("localization.jp.json", "r", encoding = "utf8") as dataf_jp: # https://schaledb.com/data/jp/students.min.json
    data_schaledb_jp = json.loads(dataf_jp.read())
def has_jp(text):
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u31F0-\u31FF\uFF66-\uFF9F]', text))
def flatten_dict(d, parent_key=""):
    """Recursively flatten a nested dictionary."""
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key))
        else:
            items[new_key] = v
    return items
flat_jp = flatten_dict(data_schaledb_jp)
flat_cn = flatten_dict(data_schaledb_cn)
map_data = {jpt: flat_cn[key] for key, jpt in flat_jp.items() if has_jp(jpt)}
map_data = dict(sorted(map_data.items(), key=lambda i: len(i[0]), reverse = True))
with open("localization.jp2cn.json", "wb") as fs:
    fs.write(json.dumps(map_data, separators=(",",":"), ensure_ascii=False).encode())