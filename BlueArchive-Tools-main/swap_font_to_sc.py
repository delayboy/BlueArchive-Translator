"""swap_font_to_sc.py — 把 Tw 字体（NotoSansTC）替换成简体中文字体。

把 prologdepengroup-...-2026-03-13 bundle 里的 NotoSansTC-Medium / NotoSansTC-Bold
两个 Font 资源的 m_FontData 替换成你提供的简体字体（推荐 NotoSansSC-Regular/Bold.otf），
然后用 crcmanip 把文件 CRC32 强行还原到原值，绕过游戏的 bundle 校验。

用法:
    benson-python-env.bat   # 进入内嵌 python 环境
    python swap_font_to_sc.py --regular <path-to-Regular.otf> --bold <path-to-Bold.otf>

如不传 --regular/--bold，默认在 ./fonts/ 下找 NotoSansSC-Regular.otf / NotoSansSC-Bold.otf。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import zlib
# crcmanip_fastcrc.pyd 在 Windows 上有 PyLong_AsLong 溢出 bug，
# 先打补丁再用 BundleExtractor（它内部会调 crcmanip 算法修补 CRC）
from crc32_patch import monkeypatch_crcmanip  # noqa: E402

monkeypatch_crcmanip()

from xtractor.bundle import BundleExtractor  # noqa: E402

TOOLS_ROOT = os.path.abspath(".")
PROJECT_ROOT = os.path.dirname(os.path.abspath("."))

# 用户已经把 bundle 拷贝到这个路径（注意是 windows 小写）
BUNDLE_PATH = os.path.join(
    PROJECT_ROOT,
    'BlueArchive_Data', 'StreamingAssets', 'PUB', 'Resource', 'Preload', 'windows',
    'prologdepengroup-assets-_mx-uis-_mxcommon-_mxprolog-2026-03-13_assets_all_842690403.bundle',
)

# 游戏真实路径（打补丁后从这里拷回去）
GAME_BUNDLE_PATH = r'.\SteamLibrary\steamapps\common\BlueArchive\BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\Windows\prologdepengroup-assets-_mx-uis-_mxcommon-_mxprolog-2026-03-13_assets_all_842690403.bundle'

DEFAULT_REGULAR = os.path.join(PROJECT_ROOT, 'fonts', 'NotoSansSC-Regular.otf')
DEFAULT_BOLD = os.path.join(PROJECT_ROOT, 'fonts', 'NotoSansSC-Bold.otf')

TARGETS = [
    ('NotoSansTC-Medium', 'Normal'),
    ('NotoSansTC-Bold', 'Bold'),
]


def crc32_of_file(path: str) -> int:
    with open(path, 'rb') as f:
        return zlib.crc32(f.read()) & 0xFFFFFFFF


def verify_bundle2(path: str) -> None:
    """加载 bundle，打印其中 Font 资源的名称和大小，用于人工确认替换结果。"""
    import UnityPy
    env = UnityPy.load(path)
    found = []
    for obj in env.objects:
        if obj.type.name != 'Font':
            continue
        d = obj.read()
        size = len(d.m_FontData) if d.m_FontData else 0
        # 读前 16 字节看 magic，OTTO=OTF, 00010000=TTF
        magic = bytes(d.m_FontData[:4]) if d.m_FontData else b''
        found.append((d.m_Name, size, magic))
        print(f'    Font: name={d.m_Name!r} size={size} magic={magic!r}')
    if not found:
        print('    [警告] bundle 里没找到 Font 资源 — 替换可能失败！')


def verify_bundle(path: str) -> None:
    from utils.util import CommandUtils
    success, err = CommandUtils.run_command(
        "./tools/BlueArchiveTools.CLI.exe", "uabea", "list", "-f", path
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='把 Tw 繁体字体替换成简体')
    parser.add_argument('--regular', default=DEFAULT_REGULAR,
                        help=f'简体 Regular 字体文件路径 (默认 {DEFAULT_REGULAR})')
    parser.add_argument('--bold', default=DEFAULT_BOLD,
                        help=f'简体 Bold 字体文件路径 (默认 {DEFAULT_BOLD})')
    parser.add_argument('--bundle', default=BUNDLE_PATH,
                        help=f'目标 bundle 路径 (默认拷贝在本项目里的副本)')
    parser.add_argument('--no-backup', action='store_true',
                        help='跳过备份步骤（不推荐）')
    args = parser.parse_args()

    bundle_path = os.path.abspath(args.bundle)
    regular_path = os.path.abspath(args.regular)
    bold_path = os.path.abspath(args.bold)

    # ── 1. 前置检查 ──────────────────────────────────────────────
    print('=' * 64)
    print('简体字体替换工具')
    print('=' * 64)
    if not os.path.exists(bundle_path):
        print(f'[错误] 找不到 bundle：{bundle_path}')
        return 1
    if not os.path.exists(regular_path):
        print(f'[错误] 找不到简体 Regular 字体：{regular_path}')
        print('       下载地址（NotoSansSC OTF，约 10 MB）：')
        print('       https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf')
        return 1
    if not os.path.exists(bold_path):
        print(f'[错误] 找不到简体 Bold 字体：{bold_path}')
        print('       下载地址：')
        print('       https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Bold.otf')
        return 1

    # 检查字体 magic —— OTF 应该是 OTTO，TTF 是 00 01 00 00
    for label, p in (('Regular', regular_path), ('Bold', bold_path)):
        with open(p, 'rb') as f:
            magic = f.read(4)
        if magic == b'OTTO':
            kind = 'OTF (CFF)'
        elif magic == b'\x00\x01\x00\x00':
            kind = 'TTF (glyf) — 注意 Unity 也能用，但与原 OTF 不一致'
        else:
            kind = f'未知 magic={magic!r}'
        print(f'  [{label}] {os.path.basename(p)}  ({kind}, {os.path.getsize(p)} bytes)')

    # ── 2. 备份 ──────────────────────────────────────────────────
    original_crc = crc32_of_file(bundle_path)
    print(f'\n原始 bundle: {os.path.basename(bundle_path)}')
    print(f'           size={os.path.getsize(bundle_path)}  CRC32=0x{original_crc:08X}')

    if not args.no_backup:
        backup_path = bundle_path + '.bak'
        if os.path.exists(backup_path):
            print(f'[跳过] 备份已存在：{os.path.basename(backup_path)}')
        else:
            shutil.copy2(bundle_path, backup_path)
            print(f'[备份] -> {os.path.basename(backup_path)}')

    # ── 3. 调用 BundleExtractor 逐个替换 ─────────────────────────
    print('\n开始替换 Font 资源 ...')
    tools_dir = os.path.join(TOOLS_ROOT, 'tools')
    extractor = BundleExtractor(install_dir=tools_dir)

    for asset_name, role in TARGETS:
        src = regular_path if role == 'Normal' else bold_path
        print(f'\n[{role}] {asset_name}  <-  {os.path.basename(src)}')
        extractor.replace_asset_from_file(bundle_path, asset_name, src, crc_fix=True)

    # ── 4. 校验 ──────────────────────────────────────────────────
    new_crc = crc32_of_file(bundle_path)
    print('\n' + '=' * 64)
    print('替换完成')
    print('=' * 64)
    print(f'  Size: {os.path.getsize(bundle_path)}')
    print(f'  CRC32: 0x{new_crc:08X}  (原始 0x{original_crc:08X}, '
          f'{"匹配 ✓" if new_crc == original_crc else "不匹配 ✗"})')

    print('\nbundle 内 Font 资源当前状态：')
    verify_bundle(bundle_path)

    # ── 5. 提示下一步 ────────────────────────────────────────────
    print('\n下一步：把补丁后的 bundle 拷回游戏目录')
    print(f'  源:   {bundle_path}')
    print(f'  目标: {GAME_BUNDLE_PATH}')
    print('建议用资源管理器手动拷贝（覆盖前先备份游戏原文件）。')

    return 0


if __name__ == '__main__':
    verify_bundle(BUNDLE_PATH)
    # a = input("是否确认执行替换算法")
    sys.exit(main())
