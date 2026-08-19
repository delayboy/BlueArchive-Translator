# 6月→8月游戏密钥Hook点迁移总结（跨版本通用方法论）

> 背景：2026年8月《蔚蓝档案》PC端大版本更新，ExcelDB.db 的 SQLCipher 密钥值更换，6月版全部断点偏移失效。
> 本文记录本次迁移实操全流程，沉淀为**可复用的跨版本迁移方法论**，供后续版本更新时（人或AI）快速重新定位 Hook 点。
> 原理背景先读：[PC端蔚蓝档案-UI剧情文本汉化解包逆向计划.md](./PC端蔚蓝档案-UI剧情文本汉化解包逆向计划.md)

---

## 0. TL;DR 本次迁移结果

| 项目 | 结果 |
| :--- | :--- |
| 8月版新密钥（已拦截并验证可用） | `ef0aaca06f34b4a4be3172a75a3ea565e815f9ece35b1fb12b7a166ba0807bc4` |
| 6月版旧密钥（已失效，存档对照） | `efa143094711b6563ec2132d4d6bbe8533d4e291ed4820bdb515b26bb57bb3f0` |
| 8月版推荐断点 | `GameAssembly.dll + 0x1985A78`（`mov rdx, rbx`，RDX=64字符hex密钥） |
| 免静态分析CE特征码（两版本均验证唯一命中） | `31 D2 E8 ?? ?? ?? ?? 48 89 C2 E8 ?? ?? ?? ?? 48 89 C3 48 8B 05 ?? ?? ?? ?? 48 8B 80 B8 00 00 00 48 8B 50 20` |
| 拦截手段 | winmm.dll 伪造代理DLL注入 MessageBox 卡住游戏主线程 → CE附加进程 → VT调试器硬件断点 → 关弹窗放行 → 断点命中读寄存器拿密钥 |

**核心结论：两个版本密钥注入机制完全同构，只有地址漂移，没有逻辑变化。** 因此"版本迁移"本质上是**地址重定位**问题，不需要重新逆向。

---

## 1. 密钥注入机制（两版本共同的原理层）

游戏通过两条 PRAGMA 顺序注入 SQLCipher（**顺序固定：license 先、key 后**，这是动态拦截时区分二者的重要依据）：

```
1. String.Concat("PRAGMA cipher_license = '", License, "';")   → ExecuteNonQuery
2. KeyData 3段byte[]拼接 → byte[32] → 转64字符hex
   String.Concat("PRAGMA key = \"x'", hex, "'\";")             → ExecuteNonQuery
```

密钥存储结构（KeyData 类静态字段，故意拆3段混淆，避免静态明文搜索）：

```csharp
class KeyData {           // 持有它的类静态字段布局（两版本一致）：
    byte[] Part1; // 10字节, 对象内偏移+0x10    static_fields +0x18 → KeyData对象
    byte[] Part2; // 10字节, 对象内偏移+0x18    static_fields +0x20 → License字符串
    byte[] Part3; // 12字节, 对象内偏移+0x20    类指针 +0xB8 → static_fields
}                                                类指针 +0xE0 → initialized标记
// 10+10+12 = 32字节 → 64 hex chars → PRAGMA key
```

**只要密钥机制本身不改版（比如换加密库、换注入方式），下述迁移方法可一直复用。**

---

## 2. 两版本DLL的代码共性（迁移的根基）

### 2.1 机制层共性（来自C#源码，编译后形状不变）

- 主函数 `ClientSQLiteConnector.CreateConnection` 内调用序列完全一致：
  `加载KeyData类 → call 拼接函数 → call byte转hex函数 → call String.Concat(license) → call ExecuteNonQuery → call String.Concat(key) → call ExecuteNonQuery`
- 拼接函数（8月版 `KeyData_Concat3Parts_ToByte32`）内部固定 **3次 BlockCopy**，参数为常量 `(0,10) (10,10) (20,12)`——这是验证"找对了拼接函数"的铁证，也是全DLL中极独特的指纹。
- IL2CPP 是 AOT 编译，同样源码+同版Unity工具链 → **机器码指令序列逐条一致**，仅地址类操作数不同。

### 2.2 指令层共性（IL2CPP代码生成模式，跨版本稳定）

密钥构造入口的固定指令形状（6月/8月逐字节同构，仅 `xx` 处不同）：

```asm
48 8B 0D xx xx xx xx     mov rcx, cs:KeyData类指针     ← rip相对，地址会变
83 B9 E0 00 00 00 00     cmp dword ptr [rcx+0E0h], 0   ← 类初始化检查，偏移不变
75 xx                    jnz short
E8 xx xx xx xx           call il2cpp_runtime_class_init
48 8B 0D xx xx xx xx     mov rcx, cs:KeyData类指针
48 8B 81 B8 00 00 00     mov rax, [rcx+0B8h]           ← static_fields，偏移不变
48 8B 48 18              mov rcx, [rax+18h]            ← KeyData对象，偏移不变
48 85 C9                 test rcx, rcx
0F 84 xx xx xx xx        jz
31 D2                    xor edx, edx
E8 xx xx xx xx           call 拼接函数                  ← 3段byte[]→byte[32]
48 89 C2                 mov rdx, rax                  ← ★RAX=byte[32]原始密钥
E8 xx xx xx xx           call byte[]→hex函数
48 89 C3                 mov rbx, rax                  ← ★RBX=64字符hex密钥串
48 8B 05 xx xx xx xx     mov rax, cs:KeyData类指针
48 8B 80 B8 00 00 00     mov rax, [rax+0B8h]
48 8B 50 20              mov rdx, [rax+20h]            ← License字符串（锚点确认）
```

### 2.3 不变的"结构常量"（跨版本比对时的锚点）

| 常量 | 含义 |
| :--- | :--- |
| `+0xB8` | Il2CppClass → static_fields 指针 |
| `+0xE0` | Il2CppClass → initialized 标记 |
| `+0x18` / `+0x20` | static_fields → KeyData对象 / License串 |
| `+0x10/+0x18/+0x20` | KeyData对象内3段byte[]引用 |
| `10 / 10 / 12` | 3段长度（BlockCopy立即数） |
| `+0x20` | IL2CPP数组对象 → 数据起始 |
| `32字节 / 64 hex` | 密钥总长 |

### 2.4 会变的部分（迁移要解决的全部内容）

- 所有**函数地址**（CreateConnection、拼接、hex转换、ExecuteNonQuery封装）
- 所有**全局变量地址**（KeyData类指针、PRAGMA字符串字面量指针）
- 所有 **rel32 调用位移**（call/jmp 的4字节相对偏移）
- 整体代码区漂移：本次 CreateConnection 从 RVA `0x17E32F0` → `0x1985770`（约 +0x1A2000），但**漂移量不均匀，不可简单加偏移推算，必须逐点重定位**

---

## 3. 本次定位过程复盘（如何从共性推差异）

**思路：把"不变量"做成通配符签名 → 在新版中搜唯一命中 → 逐指令同构映射出新地址。**

1. **选锚点**：取6月版密钥构造核心序列（§2.2 的17条指令，66字节）。选它的原因：
   - 含3个call的特定形状 + 多个结构常量（0xB8/0x18），全DLL中极难重复；
   - 恰好完整覆盖两个关键断点（byte[32] 和 hex串）。
2. **做签名**：IDA-MCP `make_signature_for_range`（mask格式，自动通配 rip 相对地址与 rel32 位移，保留指令opcode和结构常量）。
3. **搜新版**：`select_instance` 切到8月IDB → `find_bytes` 用 `??` 通配搜索 → **唯一命中** `0x18198598D`（对应6月 `0x1817E3511`）。
   > 唯一性是关键：命中多于1个说明签名太短，往前/往后扩展几条指令再搜。
4. **同构验证**：反汇编命中点前后各几十条指令，确认与6月版逐指令1:1对应（两个ExecuteNonQuery、两次Concat、license先key后的顺序都在）。
5. **子函数验证**：顺藤摸瓜确认拼接函数 `sub_18107D9C0` 内3次BlockCopy参数 `(0,10)(10,10)(20,12)` 与6月一致，且**唯一调用者**就是新定位的 CreateConnection——双保险。
6. **产出**：新断点RVA表（见附录A），新版IDB重命名+注释+保存，供下次迁移直接当基准。

---

## 4. 推荐AI分析流程（下次版本更新照此执行）

**前置**：新旧两版 `GameAssembly.dll` 各建一个 `.i64`（首次用 Il2CppDumper 跑 script 可以带符号，但本流程不依赖符号），IDA双开并启动 ida-pro-mcp。

```
Step 1  list_instances 确认双实例在线（旧版/新版各一）
Step 2  在旧IDB中打开上次标注的 CreateConnection（本次8月版已重命名为
        ClientSQLiteConnector_CreateConnection = 0x181985770）
Step 3  反汇编密钥构造段，确认指令形状仍如 §2.2（机制未变的快速判据；
        若形状变了 → 机制被改版，回到逆向计划文档从头分析）
Step 4  make_signature_for_range 对 §2.2 序列做通配符签名（约66字节）
Step 5  select_instance 切新IDB → find_bytes 搜索
        ├─ 唯一命中 → 继续
        └─ 多命中 → 签名向后续指令延长（补充 mov rax,[rax+B8h] / mov rdx,[rax+20h] 等）
Step 6  disasm 命中点，与旧版逐指令对照，映射出全部新断点
Step 7  验证拼接函数：3次BlockCopy(0,10)(10,10)(20,12) + 唯一调用者 == CreateConnection
Step 8  新IDB中 rename + set_comments + idb_save（给下次迁移留锚点，形成闭环）
Step 9  动态拦截拿密钥（见§5/§6），验证密钥能打开 ExcelDB.db 后收工
```

**降级路径**：若特征码在新版搜不到（游戏重写了KeyData逻辑），改用动态法（§5.5 运行时字符串搜索）——PRAGMA语句在运行时必然以UTF-16字符串形式出现在内存中，从字符串反查访问代码即可重新定位，无需任何静态特征。

---

## 5. 免静态分析方案：CE动态特征码定位（推荐优先尝试）

**原理**：IL2CPP AOT编译确定性 + §2.2指令形状稳定 → 一条通配符AOB（Array of Byte）在新版进程内存中直接扫描命中，命中点内部偏移即断点。**全程不需要IDA，不需要符号。**

### 5.1 已验证特征码（6月/8月双版本均唯一命中，下版优先直接试）

```
31 D2 E8 ?? ?? ?? ?? 48 89 C2 E8 ?? ?? ?? ?? 48 89 C3 48 8B 05 ?? ?? ?? ?? 48 8B 80 B8 00 00 00 48 8B 50 20
```

- 6月命中：`0x1817E3541`（RVA `0x17E3541`）；8月命中：`0x1819859BD`（RVA `0x19859BD`），两库均**唯一匹配**。
- 末尾三段 `48 8B 05 ?? ?? ?? ?? 48 8B 80 B8 00 00 00 48 8B 50 20`（KeyData类→static_fields→License字段）是该AOB的防误伤加强段；嫌长可先只用前16字节 `31 D2 E8 ?? ?? ?? ?? 48 89 C2 E8 ?? ?? ?? ?? 48 89 C3` 粗筛，再用加强段过滤。

### 5.2 命中点内偏移 = 断点（这是最稳的断点表示法，天然跨版本）

```
AOB命中地址 + 0x07  →  mov rdx, rax   断点①：RAX = byte[32]原始密钥对象，数据在 [RAX+0x20] 起32字节
AOB命中地址 + 0x0F  →  mov rbx, rax   断点②：RBX = 64字符hex密钥串（IL2CPP String对象）
```

断点②最方便：RBX 就是密钥串对象，按 §5.4 布局直接读64个hex字符。

### 5.3 CE操作步骤

1. 游戏启动并用 §6 方法卡住进程后，CE attach 到 `BlueArchive.exe`；
2. Memory Scan → Scan Type: **Array of Byte**，勾选 **Hex**，粘贴AOB（CE原生支持 `??` 通配），Memory Scan Options 的区间设为 `GameAssembly.dll` 模块（减少误命中）；
3. 扫描结果若唯一：记下地址，RVA = 命中地址 − GameAssembly.dll基址（CE内存视图 goto 支持直接输入 `GameAssembly.dll+偏移`）；
4. 打开 Memory Viewer 定位到 `命中地址+0x0F`，F5（或VT调试器）下**硬件断点**；
5. 放行游戏（关掉卡进程的MessageBox），游戏预加载打开 ExcelDB.db 时断点命中；
6. 读 RBX 指向的字符串（§5.4），即 `ef0aac...` 这样的64字符hex → 拼成 `PRAGMA key = "x'...'";` 验证解密。
   - 注意：途中会**先**经过 cipher_license 的 ExecuteNonQuery（在更早地址），特征码断点不会误停它，无需担心6月时截到license的坑。

### 5.4 IL2CPP对象内存布局（断点命中后读数用）

| 对象 | 布局 |
| :--- | :--- |
| `byte[]`（数组） | 对象头0x20字节，**数据从 +0x20 开始**（长度在 +0x18 的 max_length） |
| `String`（字符串） | **字符数(int32)在 +0x10，UTF-16LE字符从 +0x14 开始**（CE中用宽字符视图直接看） |

### 5.5 备选：运行时字符串搜索法（AOB失效时的Plan B）

PRAGMA语句运行时必然驻留内存：

1. CE扫 **UTF-16/Unicode** 文本 `PRAGMA key`（或 `cipher_license`）；
2. 对字符串地址右键 **Find out what accesses this address**，让游戏跑一次开库；
3. 访问它的指令就是 String.Concat 调用点（等价于6月 `0x17E3607`/8月 `0x1985A7E`），此时 RDX 即hex密钥——绕过一切静态特征，机制改版也能用。

---

## 6. 进程阻塞与调试器附加（本次实操的动态拦截手段）

难点：游戏启动后很快就打开ExcelDB.db，直接调试器启动易被反调试感知，附加时机也难拿捏。本次解法：

```
① winmm.dll 伪造代理注入
   游戏目录放一个伪造 winmm.dll（Windows早期加载的 KnownDLL 之一，游戏进程启动即加载）。
   它把真实调用转发给系统 winmm.dll（保证游戏正常跑），并在 DLL_PROCESS_ATTACH 时
   弹出 MessageBox —— 主线程阻塞在弹窗上，游戏冻结在启动早期、反调试尚未完全就绪。

② CE 附加
   进程"活着但卡住"的窗口期内，Cheat Engine 附加进程，从容完成AOB扫描+下硬件断点。

③ VT调试器 + 硬件断点
   用CE的VT虚拟化调试器（硬件断点，DR寄存器上限4个），断在 GameAssembly.dll+0x1985A78
   （或AOB命中+0x0F）。硬件断点不改代码字节，相对低调。

④ 放行截获
   关闭MessageBox → 游戏继续启动 → 预加载打开ExcelDB.db → 断点命中 →
   读RDX（IL2CPP String，字符在+0x14）拿到64字符hex密钥。
```

优势总结：不依赖调试器方式启动进程（父子关系/启动标志干净）、卡住点在反调试初始化前、时序完全可控。仓库根目录的 `winmm.dll` 即该代理。

---

## 附录A：6月/8月关键偏移对照表（GameAssembly.dll RVA）

| 结构 | 6月版 | 8月版 |
| :--- | :--- | :--- |
| CreateConnection 主函数 | `0x17E32F0` | `0x1985770`（IDB已命名 `ClientSQLiteConnector_CreateConnection`） |
| KeyData类加载（签名锚点） | `0x17E3511` | `0x198598D` |
| byte[32]捕获 `mov rdx,rax` | `0x17E3548` | `0x19859C4` |
| **hex密钥入RDX `mov rdx,rbx`** | `0x17E3601` | **`0x1985A78`** |
| 完整SQL `mov rbx,rax` | `0x17E360C` | `0x1985A83` |
| ExecuteNonQuery(key) | `0x17E3667` | `0x1985AD9` |
| ExecuteNonQuery(license) | `0x17E35D6` | `0x1985A4D` |
| 3段拼接函数 | `sub_180F300C0` | `sub_18107D9C0`（IDB已命名 `KeyData_Concat3Parts_ToByte32`） |
| byte[]→hex函数 | `sub_1817E3980` | `sub_181985C90`（IDB已命名 `ByteArray_ToHexString`） |
| KeyData类指针（全局变量） | `qword_18C511E20` | `qword_18CF23D40` |

## 附录B：密钥存档

| 版本 | 密钥（64 hex） | 状态 |
| :--- | :--- | :--- |
| 2026-06 | `efa143094711b6563ec2132d4d6bbe8533d4e291ed4820bdb515b26bb57bb3f0` | 已失效 |
| 2026-08 | `ef0aaca06f34b4a4be3172a75a3ea565e815f9ece35b1fb12b7a166ba0807bc4` | 当前有效 |

> 密钥仅用于本地ExcelDB.db解包汉化研究，来自对自有合法副本的动态分析。



## 生成本文档所用的用户级提示词

> 2026年6月时已经通过AI逆向分析找到了数据库密钥，并成功实现游戏汉化，整体项目介绍参考【./README.md】，数据库密钥拦截获取方式参考【./相关文档/PC端蔚蓝档案-UI剧情文本汉化解包逆向计划.md】，现在26年8月游戏进行了大版本更新，密钥值变了，现在需要你通过ida-pro-mcp交叉比对6月和8月游戏文件的关键代码差异，并给出26年8月的游戏文件的密钥值可以在哪拦截到（拦截方式类似6月的研究成果），告诉我再哪个关键点位下断点可以拦截到密钥。
>
>
> 目前已拦截到密钥并验证成功，主要使用了winmm.dll伪造dll代理并注入messagebox卡住游戏进程，CE附加进程后，使用VT调试器断点关键点位，并拿到密钥参数。将你上述跨游戏版本迁移HOOK点的经验总结一份【6月到8月游戏密钥hook点迁移总结.md】，方便后续AI能快速上手迁移。
> 重点总结两个版本游戏dll间的代码共性，以及你是如何通过共性准确定位差一点的，未来推荐其他AI走什么分析流程能快速定位hook点（最好能额外补充说一下如果未来不使用ida-pro来静态分析，直接调用CE动态调试，有什么特征码可以快速定位hook点，这样之后可以省去静态分析符号的时间），以及简单总结一下我是通过什么手段阻塞游戏进程附加调试器并拿到密钥的。
