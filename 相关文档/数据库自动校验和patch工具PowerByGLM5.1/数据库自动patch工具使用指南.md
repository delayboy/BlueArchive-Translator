数据库功能完全正常 —— 密钥验证通过，能列出全部 408 个表并查询每个表的行数。

## 命令示例

cd "c:/Users/Benson/Desktop/BlueArchive-Hack/BlueArchive_Data/StreamingAssets/Resource/Preload/TableBundles" && python resize_exceldb_to_raw.py --self-test
cd "c:/Users/Benson/Desktop/BlueArchive-Hack/BlueArchive_Data/StreamingAssets/Resource/Preload/TableBundles" && python resize_exceldb_to_raw.py

## 完成总结

脚本：[resize_exceldb_to_raw.py](vscode-webview://0g33afsh4vtoocm85eirbmsl04vmiqc3j79oi84bsaqlno69l5ur/resize_exceldb_to_raw.py)

**结果：**

| 项目      | ExcelDB.db                           | ExcelDB-raw.db | 状态       |
| --------- | ------------------------------------ | -------------- | ---------- |
| 文件大小  | 304,910,336                          | 304,910,336    | ✅ 完全一致 |
| CRC32     | `26CECA1C`                           | `26CECA1C`     | ✅ 完全一致 |
| DB 可打开 | 是（912 行 sqlite_master，408 张表） | —              | ✅ 功能正常 |

**原理：**

1. **大小匹配**：在文件末尾追加 6,643,708 字节随机 padding。SQLite 通过加密页 1 头部中的 "size in pages" 字段判断有效范围，超出部分被忽略，所以追加是安全的。
2. **CRC32 匹配**：在 padding 末尾保留 4 字节，利用 CRC32 在 GF(2) 上的线性性质，建立 32×32 二元线性方程组，高斯消元求解出这 4 字节（结果为 `0e87ddf1`）。4 字节 = 32 位 = CRC32 输出位宽，所以数学上**必定有解**。

**操作记录：**

- 原文件已备份为 `ExcelDB.db.bak`（若再次运行脚本，不会覆盖备份）
- 修改位置：offset `0x122C8FFC`（即 padding 区最末 4 字节），未触及任何加密页

**回滚方式：**



```bash
python resize_exceldb_to_raw.py --restore
```

**注意事项：**

- 脚本假定完整性校验使用的是标准 CRC32（zlib 多项式 `0xEDB88320`）。如果游戏用的是 MD5/SHA 等加密哈希，则 CRC 匹配部分无法实现（加密哈希抗碰撞）。
- 如果校验方读取整文件并使用其他 CRC 变种（如 CRC32C/CRC16），可在 `find_crc32_patch` 中替换多项式与表格。