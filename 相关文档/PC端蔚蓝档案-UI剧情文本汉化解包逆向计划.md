# 解包脚本调用时的输入参数

```text
C:\Users\Benson\Desktop\BlueArchive-Hack\BlueArchive_Data\StreamingAssets\Resource\Preload\TableBundles

C:\Users\Benson\Desktop\BlueArchive-Hack\BlueArchive_Data\StreamingAssets\Resource\Preload\TableJson
```



# 关键目录介绍

-  `BlueArchive-Steam-IL2CPP-dump\cpp2il_out_cs` 使用Cpp2IL.exe导出的游戏C#代码
-  `BlueArchive-Steam-IL2CPP-dump\cpp2il_out_dll` 使用Cpp2IL.exe导出的游戏 DLL 文件，方法体为默认占位符
- `BlueArchive_Data\Plugins\x86_64\sqlcipher.dll` 数据库加密读取支持库
- `BlueArchive_Data\StreamingAssets\Resource\Preload\TableBundles\ExcelDB.db` 游戏相关文本数据，加密存储
- `BlueArchive_Data\StreamingAssets\Resource\Preload\TableBundles\Excel.zip`游戏相关文本数据，使用梅森旋转加密存储
- `BlueArchive_Data\StreamingAssets\Resource\Catalog\TableBundles\TableCatalog.bytes` 似乎和校验和有关的文件
- `BlueArchive-Tools-main-蔚蓝档案解包汉化工具` 在github上收集到的其他作者发布的汉化工具代码（主要对Android端进行适配）

# 主要任务

- 根据【火绒剑ExcelDB调试堆栈】分析PC端ExcelDB.db游戏文本数据库的解密密钥是什么
- 鉴于解密密钥也有可能不以硬编码的形式存储在游戏代码文件里，因此如果发现解密密钥是动态获取的
- 因此具体来说我将提供三种汇报方式供你选择：
  - 方案1（最推荐）：密钥硬编码存储，直接告知用户关键函数点位，和密钥具体值
  - 方案2：告诉用户在游戏启动后的那块内存地址可以直接读取到密钥值
  - 方案3：告诉用户在哪个函数地址下调试断点，可以拦截到密钥参数

## 火绒剑ExcelDB调试堆栈

文件句柄打开堆栈：01:32:04.3539386 BlueArchive.exe 8828 FILE_open C:\Program Files (x86)\Steam\steamapps\common\BlueArchive\BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\TableBundles\ExcelDB.db access:0x00120089 alloc_size:0 attrib:0x00000000 share_access:0x00000003 disposition:0x00000001 options:0x00000060  0x00000000 [The operation completed successfully.  ]

```
0 ntdll.dll+0x9f814
1 KernelBase.dll+0x2a761
2 KernelBase.dll+0x2a37c
3 sqlcipher.dll+0xd9871sqlcipher.dll!sqlite3changeset_start+0xcd2f5
4 sqlcipher.dll+0x25140asqlcipher.dll!sqlite3changeset_start+0x244e8e
5 sqlcipher.dll+0x2044c1sqlcipher.dll!sqlite3changeset_start+0x1f7f45
6 sqlcipher.dll+0x1a2470sqlcipher.dll!sqlite3changeset_start+0x195ef4
7 GameAssembly.dll+0x9a341c
8 GameAssembly.dll+0x17e348f
9 GameAssembly.dll+0x17e484f
10 GameAssembly.dll+0x489b01b
11 GameAssembly.dll+0x48609ea
12 GameAssembly.dll+0x16e2f97
13 GameAssembly.dll+0x167aa5b
14 GameAssembly.dll+0x31f14ef
15 GameAssembly.dll+0x166ecf7
16 GameAssembly.dll+0x1674ab3
17 GameAssembly.dll+0x166dc4e
18 GameAssembly.dll+0x1674049
19 GameAssembly.dll+0x166ddbe
20 GameAssembly.dll+0x1673c70
21 GameAssembly.dll+0x996e727
22 GameAssembly.dll+0x3f4c52
23 GameAssembly.dll+0x3f4acb
24 UnityPlayer.dll+0x627068
25 UnityPlayer.dll+0x62a0c2
26 UnityPlayer.dll+0x645c55
27 UnityPlayer.dll+0x352a54
28 UnityPlayer.dll+0x4a4dba
29 UnityPlayer.dll+0x4a4e60
30 UnityPlayer.dll+0x4a7b38
31 UnityPlayer.dll+0x6a405a
32 UnityPlayer.dll+0x6a2d8b
33 UnityPlayer.dll+0x6a7787
34 UnityPlayer.dll+0x6a963b
35 0x0B4911F2BlueArchive.exe+0x11f2
36 Kernel32.dll+0x1244d
37 ntdll.dll+0x5df78
```

文件句柄读取堆栈：01:32:04.3539386 BlueArchive.exe 8828 FILE_read C:\Program Files (x86)\Steam\steamapps\common\BlueArchive\BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\TableBundles\ExcelDB.db offset:0x00000000 datalen:0x00000064  0x00000000 [The operation completed successfully.  ]

```
0 ntdll.dll+0x9ee34
1 KernelBase.dll+0x2c1a8
2 sqlcipher.dll+0xd5d46sqlcipher.dll!sqlite3changeset_start+0xc97ca
3 sqlcipher.dll+0x204544sqlcipher.dll!sqlite3changeset_start+0x1f7fc8
4 sqlcipher.dll+0x1a2470sqlcipher.dll!sqlite3changeset_start+0x195ef4
5 GameAssembly.dll+0x9a341c
6 GameAssembly.dll+0x17e348f
7 GameAssembly.dll+0x17e484f
8 GameAssembly.dll+0x489b01b
9 GameAssembly.dll+0x48609ea
10 GameAssembly.dll+0x16e2f97
11 GameAssembly.dll+0x167aa5b
12 GameAssembly.dll+0x31f14ef
13 GameAssembly.dll+0x166ecf7
14 GameAssembly.dll+0x1674ab3
15 GameAssembly.dll+0x166dc4e
16 GameAssembly.dll+0x1674049
17 GameAssembly.dll+0x166ddbe
18 GameAssembly.dll+0x1673c70
19 GameAssembly.dll+0x996e727
20 GameAssembly.dll+0x3f4c52
21 GameAssembly.dll+0x3f4acb
22 UnityPlayer.dll+0x627068
23 UnityPlayer.dll+0x62a0c2
24 UnityPlayer.dll+0x645c55
25 UnityPlayer.dll+0x352a54
26 UnityPlayer.dll+0x4a4dba
27 UnityPlayer.dll+0x4a4e60
28 UnityPlayer.dll+0x4a7b38
29 UnityPlayer.dll+0x6a405a
30 UnityPlayer.dll+0x6a2d8b
31 UnityPlayer.dll+0x6a7787
32 UnityPlayer.dll+0x6a963b
33 BlueArchive.exe+0x11f2
34 Kernel32.dll+0x1244d
35 ntdll.dll+0x5df78
```

# Excel.db密钥解析分析报告

# ExcelDB.db 解密密钥分析报告

## 核心发现

ExcelDB.db 使用 **SQLCipher** 加密，密钥通过两条 PRAGMA 指令设置（**未使用** `sqlite3_key` API）：



```
PRAGMA cipher_license = '<license_string>';
PRAGMA key = "x'<32字节十六进制>'";   ← 64 hex chars
```

## 关键函数定位

| 功能           | 函数地址 (GameAssembly.dll 偏移)      | 说明                                                         |
| -------------- | ------------------------------------- | ------------------------------------------------------------ |
| 设置密钥主函数 | `sub_1817E32F0` (偏移 `0x17E32F0`)    | `ClientSQLiteConnector.CreateConnection`，对应堆栈第8帧      |
| 字节数组拼接   | `sub_180F300C0` (偏移 `0x0F300C0`)    | 将 3 段字节数组 (10+10+12) 合并为 `byte[32]`                 |
| 字节转十六进制 | `sub_1817E3980` (偏移 `0x17E3980`)    | 将 `byte[32]` 格式化为 64 字符 hex 串                        |
| 持有密钥的类   | `qword_18C511E20` (偏移 `0x8C511E20`) | 静态字段在偏移 `+0x18`(KeyData对象) 和 `+0x20`(License字符串) |

## 密钥构造机制（关键分析）

在 `sub_1817E32F0` 内部，密钥构造流程（[BlueArchive.Steam.IL2CPP.dump:1817E3511-1817E3543](vscode-webview://0g33afsh4vtoocm85eirbmsl04vmiqc3j79oi84bsaqlno69l5ur/BlueArchive-Steam-IL2CPP-dump#L1817E3511-L1817E3543)）：



```
1. mov rcx, qword_18C511E20      ; 类信息指针
2. mov rax, [rcx+0B8h]           ; static_fields 缓冲区
3. mov rcx, [rax+18h]            ; 读取 KeyData 对象 (静态字段)
4. call sub_180F300C0            ; 拼接 3 个字节数组为 byte[32]
5. call sub_1817E3980            ; 将 byte[32] 转为 64 字符 hex 串
6. String.Concat("PRAGMA key = \"x'", hex, "'\";")
```

**密钥数据结构** ([BlueArchive.Steam.IL2CPP.dump:180F300C0](vscode-webview://0g33afsh4vtoocm85eirbmsl04vmiqc3j79oi84bsaqlno69l5ur/BlueArchive-Steam-IL2CPP-dump#L180F300C0))：



```csharp
class KeyData {
    byte[] Part1;  // 10 字节 - 在 +0x10 偏移
    byte[] Part2;  // 10 字节 - 在 +0x18 偏移
    byte[] Part3;  // 12 字节 - 在 +0x20 偏移
}
// 总计 32 字节 → 转换为 64 hex chars → 作为 SQLCipher 密钥
```

## 三个方案推荐

### ⭐ 方案 3 推荐（最可行）：调试断点拦截

开发者将密钥拆成 3 段 `byte[]` 静态字段是**故意混淆**，无法直接静态搜索到。建议使用 x64dbg/Cheat Engine 在游戏运行时拦截：

**断点位置 1（捕获原始字节数组）**：

- 地址：`GameAssembly.dll + 0x17E3548`（`sub_180F300C0` 调用之后）
- 寄存器：**RAX** = 指向 `byte[32]` 数组的指针
- 读取：`[RAX+0x20]` 开始的 32 字节即原始密钥
- 转换：将这 32 字节按 `%02x` 格式化为 64 字符 hex 串

**断点位置 2（捕获完整 PRAGMA 语句）**：

- 地址：`GameAssembly.dll + 0x17E3607`（`String.Concat` 调用之前）
- 此处 `rbx` 寄存器 = 已格式化的 64 字符 hex 字符串

**断点位置 3（最简单，捕获最终 SQL）**：

- 地址：`GameAssembly.dll + 0x17E35D6`（`SQLiteCommand.ExecuteNonQuery` 调用）
- `rdx` = 完整的 `PRAGMA key = "x'...'";` SQL 字符串

### 方案 2：游戏运行后从内存读取

游戏加载 ExcelDB 后类已初始化，可直接读取：



```
1. 查找 GameAssembly.dll 基址 (用 GetModuleHandle)
2. 读取 [base + 0x8C511E20] 得到 Il2CppClass* 指针
3. 读取 [Il2CppClass + 0xB8] 得到 static_fields 指针
4. 读取 [static_fields + 0x18] 得到 KeyData 对象
5. 读取 KeyData+0x10, +0x18, +0x20 处的 3 个 byte[] 引用
6. 每个 byte[] 在 +0x20 处开始为字节数据
7. [static_fields + 0x20] = License 字符串 (UTF-16)
```

### 方案 1（无法完全静态提取）

⚠️ **限制**：`qword_18C511E20` 类被 3674 个函数引用，.cctor（静态构造函数）难以静态识别。密钥 3 段字节值在 .cctor 中通过 `il2cpp_array_new_specific` + 单字节 `mov` 指令逐个写入，未以明文字符串形式存在元数据中。

如需方案 1，需进一步：

1. 启动游戏后 dump 内存
2. 用方案 3 拦截后即可获得最终密钥

## 解密 ExcelDB.db（供汉化使用）

获得 32 字节密钥（64 hex chars）后，可用 DB Browser for SQLite (SQLCipher 版本) 或 sqlcipher CLI：



```bash
sqlcipher ExcelDB.db
PRAGMA key = "x'<your_64_hex_chars>'";
PRAGMA cipher_page_size = 4096;     # 默认值
PRAGMA kdf_iter = 64000;            # SQLCipher 默认值，可能需要调整
.tables
```

或使用 Python `pysqlcipher3`：



```python
from pysqlcipher3 import dbapi2 as sql
conn = sql.connect("ExcelDB.db")
cur = conn.cursor()
cur.execute("PRAGMA key = \"x'<your_hex_key>'\"")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cur.fetchall())
```

## 总结

| 项目     | 值                                                           |
| -------- | ------------------------------------------------------------ |
| 加密方式 | SQLCipher（PRAGMA key）                                      |
| 密钥长度 | 32 字节（64 hex chars）                                      |
| 密钥存储 | 类 `qword_18C511E20` 的静态字段，拆成 3 段 byte[]            |
| 设置函数 | `sub_1817E32F0` (`CreateConnection`)                         |
| 推荐方案 | **方案 3**：断点 `GameAssembly.dll + 0x17E3548`，读取 RAX 指向的 byte[32] |

获取到密钥后即可解密 ExcelDB.db 提取剧情文本进行汉化。



# ExcelDB.db 解密密钥修正报告

> 我在GameAssembly.dll+0x17E35D6断点得到的sql是这个，好像不是PRAGMA key是不是点位不对 PRAGMA cipher_license = 'OmNpZDowMDFWSjAwMDAwY3pzaVlZQVE6cGxhdGZvcm06MjY6ZXhwaXJlOm5ldmVyOnZlcnNpb246MTpsaWJ2ZXI6NC4xMC4wOmhtYWM6ODQ1Y2JkMzQ0MDc3YjIxNmRlYTgyOWI3OTIyMzRkM2UwYmUyMzNhYw==';

抱歉点位错了！你截到的是 **cipher_license（许可证）** 的执行点，而密钥执行点在更后面。但你这个截取很有价值——我们已经拿到了许可证：

**Base64 解码许可证**:



```
:cid:001VJ00000czsiYYAQ:platform:26:expire:never:version:1:libver:4.10.0:hmac:845cbd344077b216dea829b792234d3e0be233ac
```

确认是 **SQLCipher 4.10.0 商业版**。

## 正确的断点位置

参考反汇编，函数 `sub_1817E32F0` 中依次执行两条 PRAGMA：

| 偏移        | 指令                     | 作用                                    |
| ----------- | ------------------------ | --------------------------------------- |
| `0x17E35D6` | call ExecuteNonQuery     | **执行 cipher_license（你刚才截到的）** |
| `0x17E35FA` | mov rcx, qword_18C65A2B0 | 加载 `PRAGMA key = "x'` 前缀            |
| `0x17E3601` | mov rdx, rbx             | **rbx = 64 字符 hex 密钥字符串**        |
| `0x17E3607` | call String.Concat       | 拼接成完整 `PRAGMA key = "x'...'";`     |
| `0x17E360C` | mov rbx, rax             | **rax = 完整 PRAGMA key SQL 字符串**    |
| `0x17E3667` | call ExecuteNonQuery     | **执行 PRAGMA key（这才是你要的）**     |

## 三个推荐点位

**点位 A（最直接 - 推荐）：偏移 `0x17E3601`**

- 此时 `RDX` (=rbx) = 64 字符的 hex 密钥（纯 hex，无前后缀）
- 直接读 RDX 指向的字符串就是密钥

**点位 B（完整 SQL）：偏移 `0x17E360C`**

- 此时 `RAX` = 完整的 `PRAGMA key = "x'<64hex>'";` 字符串

**点位 C（捕获 byte[32] 原始字节）：偏移 `0x17E3548`**

- 此时 `RAX` = byte[32] 数组指针
- 读取 `[RAX+0x20]` 起的 32 字节 = 原始密钥字节

## 实际操作

把断点改到 **`GameAssembly.dll + 0x17E3601`**（或 `0x17E3667`），重新运行游戏打开 ExcelDB.db，触发断点后查看 RDX 寄存器指向的字符串即可。

由于是顺序执行，license pragma 比 key pragma 先触发——所以你的 0x17E35D6 断点每次都先命中 license。换成 `0x17E3667` 就会停在 key 的执行上。

最终获得如下密钥：

RAGMA key = "x'efa143094711b6563ec2132d4d6bbe8533d4e291ed4820bdb515b26bb57bb3f0'";
