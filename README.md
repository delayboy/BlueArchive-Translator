# BlueArchive-Hack

> PC 端《蔚蓝档案》（Blue Archive, Steam IL2CPP 版）UI / 剧情文本汉化与资源修改工作目录。
> 采用 **离线解包 → 翻译/修改 → 重新打包 → 绕过完整性校验** 的工作流，无需内存 Hook 或网络代理。

> [!IMPORTANT]
> 本仓库仅用于**个人学习与本地化研究**。[B站视频教程链接](https://www.bilibili.com/video/BV1aBja6sESp/)
> "Blue Archive" 是 NEXON Korea Corp. & NEXON GAMES Co., Ltd. 的注册商标。使用本仓库任何成果时，请确保遵守当地法律法规，自负风险。

---

## 项目背景

Steam 版《蔚蓝档案》客户端原生仅支持 `Kr / Jp / Th / Tw / En` 五种语言（见 `dump.cs` 中 `Language` 枚举），**没有简体中文（Cn）**。本项目通过解包与重建官方资源，让简体中文文本与字形能够正确显示。整体路线为：

```
官方资源 (加密) ──解密/解码──▶ 可读中间格式 (JSON / OTF / Texture2D)
        │                                              │
        │                                              ▼
        │                                      人工翻译 / 字形替换
        │                                              │
        ▼                                              ▼
原始加密资源 ◀──────重新加密/重打包 + 校验绕过◀──────修改后资源
```

关键挑战有两个：
1. **加密**：FlatBuffer XOR（类名密钥）、ZIP 密码（文件名派生）、SQLCipher 数据库（硬编码密钥）。
2. **完整性校验**：`TableCatalog.bytes` 中的 Size/CRC 字段，以及游戏对 bundle 整体 CRC 的检查。

---

## 目录结构

| 路径 | 作用 |
| :--- | :--- |
| `BlueArchive_Data/` | 游戏运行时数据副本（StreamingAssets、Plugins、il2cpp_data 等），是汉化输入源。 |
| `BlueArchive_Data/StreamingAssets/Resource/Preload/TableBundles/ExcelDB.db` | SQLCipher 加密 SQLite，存放绝大多数剧情/UI 数据表（FlatBuffer 二进制）。 |
| `BlueArchive_Data/StreamingAssets/Resource/Preload/TableBundles/Excel.zip` | 同批数据表的另一种打包形式，ZIP + XOR 加密。 |
| `BlueArchive_Data/Plugins/x86_64/sqlcipher.dll` | 游戏运行时用于读取加密 DB 的支持库。 |
| `BlueArchive-Steam-IL2CPP-dump/` | 通过 `Cpp2IL.exe` / `Il2CppDumper` 从 `GameAssembly.dll` 导出的 C# 代码与 DLL，是 FlatBuffer Schema 与密钥定位的来源。 |
| `BlueArchive-Tools-main/` | 主力汉化工具链（来自 [beichen23333/BlueArchive-Tools](https://github.com/beichen23333) 系列的本地修改版）。 |
| `BlueArchiveLocalizationTools-main/` | asfu222 开源解包/封包工具，提供 FlatData 生成、voice zip 打包等能力。 |
| `assistance_script/` | 本地辅助脚本（繁→简转换、DB 查看、CRC padding 等）。 |
| `fonts/` | 替换用的简体字体（`NotoSansSC-Regular.otf` / `NotoSansSC-Bold.otf`）。 |
| `backup_game_files/` | 原始 `GameAssembly.dll`、`ExcelDB.db`、`TableCatalog.bytes` 等的备份，包含 `.i64` IDA 数据库。 |
| `other_support_project/` | 外部支撑项目源码与发行包（UABEA、Il2CppInspectorRedux、pycrcmanip、BA-FlatData、Spine 转换器等）。 |
| `python_embeded/` | 便携式 Python 解释器，供脚本本地运行（由 `benson-python-env.bat` 注入 PATH）。 |
| `相关文档/` | 逆向与调试过程产生的分析报告、调试堆栈、工具使用指南（见下文）。 |

---

## 核心技术路线

### 1. 剧情与数据表汉化（Excel.zip / ExcelDB.db）

入口：`BlueArchive-Tools-main/process_excel.py` → `xtractor/table.py`

- **Excel.zip**：ZIP 密码由 `xxh32("Excel") → MT19937` 派生（15 字节 base64）；内部 `.bytes` 再用 `XOR(MT19937(xxh32(FlatBuffer 类名)))` 二次加密。
- **ExcelDB.db**：SQLCipher 4.10.0 商业版加密的 SQLite；32 字节密钥拆成 3 段 `byte[]`（10+10+12）保存在 `qword_18C511E20` 类的静态字段中，通过 `ClientSQLiteConnector.CreateConnection`（`GameAssembly.dll + 0x17E32F0`）在运行时拼接为 64 字符 hex 串后通过 `PRAGMA key = "x'...'";` 注入。详见 [`相关文档/PC端蔚蓝档案-UI剧情文本汉化解包逆向计划.md`](相关文档/PC端蔚蓝档案-UI剧情文本汉化解包逆向计划.md)。
- 解密后的 `Bytes` 列存放 FlatBuffer 二进制，用 [BA-FlatData](https://github.com/beichen23333/BA-FlatData.git) 提供的 Schema 反序列化为 JSON；翻译后通过 `pack_*` 重新序列化、XOR 回去、写回 DB/ZIP，并 `VACUUM` 优化。

### 2. 字体替换（繁体字形 → 简体字形）

入口：`BlueArchive-Tools-main/swap_font_to_sc.py` + `crc32_patch.py`

- 游戏将简中渲染挂在 `Language.Tw` 分支，字形使用 `NotoSansTC-Medium/Bold.otf`，因此简体字会以繁体字形显示（生硬、缺字）。
- 在 `prologdepengroup-...-842690403.bundle` 中定位到目标 Font 资产，通过 UABEA CLI 将 `m_FontData` 替换为 `NotoSansSC-*.otf`，保持资产名不变。
- 替换会改变 bundle 字节，利用 CRC32 在 GF(2) 上的线性性质，通过 `pycrcmanip` 在文件末尾追加 4 字节，使整体 CRC32 等于原值，从而绕过游戏的 bundle 校验。详见 [`相关文档/字体配置分析.md`](相关文档/字体配置分析.md)。

### 3. DB 尺寸匹配（修改后保持原文件大小与 CRC）

入口：`相关文档/数据库自动校验和patch工具PowerByGLM5.1/resize_exceldb_to_raw.py`

- 修改 `ExcelDB.db` 后，文件大小和 CRC 会变化，触发游戏完整性校验。
- 脚本通过在文件末尾追加随机 padding 让文件大小等于原始大小（SQLite 通过加密页 1 头部中的 size-in-pages 字段判定有效范围，超出部分被忽略）。
- 再利用 CRC32 的线性性质建立 32×32 二元线性方程组，高斯消元求解 padding 末 4 字节，使最终 CRC 与原文件完全一致。详见 [`相关文档/数据库自动校验和patch工具PowerByGLM5.1/数据库自动patch工具使用指南.md`](相关文档/数据库自动校验和patch工具PowerByGLM5.1/数据库自动patch工具使用指南.md)。

### 4. 绕过完整性校验的两种策略

| 策略 | 适用场景 | 做法 |
| :--- | :--- | :--- |
| **改 catalog 法** | Table 表（`TableCatalog.bytes`） | 修改后重算 CRC/Size 写回 catalog，让游戏比对时认为合法。 |
| **CRC 伪造法** | Unity AssetBundle | 不动 catalog，用 `pycrcmanip` 让修改后文件的整体 CRC32 等于原值。 |

---

## 关键技术文档（`相关文档/`）

| 文档 | 摘要 |
| :--- | :--- |
| [`PC端蔚蓝档案-UI剧情文本汉化解包逆向计划.md`](相关文档/PC端蔚蓝档案-UI剧情文本汉化解包逆向计划.md) | ExcelDB.db 的 SQLCipher 密钥逆向全过程：火绒剑抓取的 FILE_open / FILE_read 堆栈，函数地址定位（`sub_1817E32F0`、`sub_180F300C0`、`sub_1817E3980`），三种获取密钥方案，最终在 `0x17E3667` 断点拦截到完整 `PRAGMA key`。 |
| [`字体配置分析.md`](相关文档/字体配置分析.md) | 分析 `FontContainer` 与 `Language` 枚举的对应关系，确认简中走 Tw 分支；定位 Tw 字体所在 bundle，给出替换思路与 UABEA / UnityPy 方案对比。 |
| [`翻译后活动立绘消失根因.md`](相关文档/翻译后活动立绘消失根因.md) | `CharacterDialogEventExcel` 表打包后游戏内文本加载失败的根因分析：`VoiceId` 空向量在 `repack_wrapper.py` 中由"字段不存在"变为"存在但为空"，导致游戏端走错分支。 |
| [`数据库自动校验和patch工具PowerByGLM5.1/数据库自动patch工具使用指南.md`](相关文档/数据库自动校验和patch工具PowerByGLM5.1/数据库自动patch工具使用指南.md) | `resize_exceldb_to_raw.py` 使用指南：原理、自检、回滚方式，以及对 CRC 多项式替换的注意事项。 |
| [`调试断点拦截到的密钥原文.txt`](相关文档/调试断点拦截到的密钥原文.txt) | x64dbg 实际拦截到的 `PRAGMA cipher_license` 与 `PRAGMA key` 原文（已脱敏归档）。 |
| [`ida-mcp全自动逆向提示词.txt`](相关文档/ida-mcp全自动逆向提示词.txt) | 通过 IDA + MCP 进行自动化逆向分析的提示词模板。 |

---

## 快速开始

### 环境准备

```bash
# 1. 激活便携式 Python（会自动设置 HF_HOME / PATH）
benson-python-env.bat

# 2. 进入主力工具目录
cd BlueArchive-Tools-main
```

### 常用命令

```bash
# 查看 ExcelDB.db（需要密钥，由逆向得到）
cd BlueArchive_Data/StreamingAssets/Resource/Preload/TableBundles
python view_bluearchive_db.py

# 将修改后的 ExcelDB.db 尺寸与 CRC 对齐到原始值
python resize_exceldb_to_raw.py --self-test
python resize_exceldb_to_raw.py
python resize_exceldb_to_raw.py --restore   # 回滚

# 字体替换（繁 → 简）
cd BlueArchive-Tools-main
python swap_font_to_sc.py

# FlatBuffer 表解包 / 重打包
python process_excel.py
```

---

## 密钥派生链一览

| 加密层 | 算法 | 密钥种子 | 是否需要逆向 |
| :--- | :--- | :--- | :--- |
| FlatBuffer `.bytes` XOR | `MT19937(xxh32(name))` | FlatBuffer 类名（公开） | 否，公开字符串即可 |
| ZIP 密码 | `base64(MT19937(xxh32(name), 15))` | ZIP 主名（公开） | 否 |
| `GameMainConfig` 字段 | XOR（字段名派生） | 字段名字符串 | 否 |
| **ExcelDB.db SQLCipher** | SQLCipher 4.10.0 | IL2CPP 中 3 段 `byte[]` 硬编码 | **是**，需 `GameAssembly.dll + 0x17E3667` 断点拦截 |

---

## 安全与合规

- 本仓库不包含任何无法从公开渠道获取的游戏原始资源（`BlueArchive_Data/`、`backup_game_files/` 中的实际资产已在 `.gitignore` 中排除）。
- 涉及到的密钥、断点地址等技术细节，来自对**自有合法副本**的静态/动态分析，仅用于个人研究。
- 严禁将本仓库工具用于制作并公开发布可分发的汉化补丁、绕过反作弊、破坏多人模式平衡等用途。
- 若版权方提出异议，请通过 Issue 联系，将在确认后删除相关内容。

---

## 致谢

本项目参考以下开源社区代码，感谢各位大佬们对蔚蓝档案翻译工作的贡献：

- [beichen23333/BlueArchive-Tools](https://github.com/beichen23333) — 汉化工具链主体
- [asfu222/BlueArchiveLocalizationTools](https://github.com/asfu222/BlueArchiveLocalizationTools) — FlatData / voice 打包
- [beichen23333/BA-FlatData](https://github.com/beichen23333/BA-FlatData.git) — FlatBuffer Schema
- [SamboyCoding/Cpp2IL](https://github.com/SamboyCoding/Cpp2IL) & [LukeFZ/Il2CppInspectorRedux](https://github.com/LukeFZ/Il2CppInspectorRedux) — IL2CPP 反向工程
- [H9per/UABEA](https://github.com/H9per/UABEA) — AssetBundle 操作
- [rr-/pycrcmanip](https://github.com/rr-/pycrcmanip) — CRC32 伪造
- [ZM-Kimu/Blue-Archive-Asset-Downloader](https://github.com/ZM-Kimu/Blue-Archive-Asset-Downloader) — 资源下载
- [wang606/SpineSkeletonDataConverter](https://github.com/wang606/SpineSkeletonDataConverter) — Spine 动画转换

"Blue Archive" 是 NEXON Korea Corp. & NEXON GAMES Co., Ltd. 的注册商标。
