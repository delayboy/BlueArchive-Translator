import json
with open("students.cn.json", "r", encoding = "utf8") as dataf_cn: # https://schaledb.com/data/cn/students.min.json
    data_schaledb_cn = json.loads(dataf_cn.read())
with open("students.jp.json", "r", encoding = "utf8") as dataf_jp: # https://schaledb.com/data/jp/students.min.json
    data_schaledb_jp = json.loads(dataf_jp.read())
map_data = {data_schaledb_jp[k]["Name"]:data_schaledb_cn[k]["Name"] for k in data_schaledb_cn.keys()}
map_data = dict(sorted(map_data.items(), key=lambda i: len(i[0]), reverse = True))
with open("students.jp2cn.json", "wb") as fs:
    fs.write(json.dumps(map_data, separators=(",",":"), ensure_ascii=False).encode())