"""crc32_patch.py — 纯 Python CRC32 修补 + crcmanip monkey-patch。

绕过 crcmanip_fastcrc.pyd 在 Windows 平台的 PyLong_AsLong 溢出 bug。

提供：
  patch_file_crc(path, target_crc)    在文件末尾追加 4 字节，让整体 CRC32 == target_crc
  monkeypatch_crcmanip()              替换 crcmanip.fastcrc.crc_next/crc_prev 为纯 Python 实现

算法：CRC32 (zlib, 多项式 0xEDB88320) 的 4 字节后缀修补。
"""
from __future__ import annotations

import zlib

POLY = 0xEDB88320


def _make_forward_table() -> list[int]:
    table = []
    for n in range(256):
        c = n
        for _ in range(8):
            c = (c >> 1) ^ POLY if (c & 1) else (c >> 1)
        table.append(c)
    return table


def _make_high_byte_reverse(forward: list[int]) -> list[int]:
    """对每个高字节 h，找出 idx 使 (forward[idx] >> 24) == h。

    CRC32 forward 表的高字节构成 0..255 的双射，所以这是良定义的。"""
    rev = [0] * 256
    for idx in range(256):
        h = (forward[idx] >> 24) & 0xFF
        rev[h] = idx
    return rev


FORWARD = _make_forward_table()
REVERSE_HI = _make_high_byte_reverse(FORWARD)


def compute_patch_bytes(data: bytes, target_crc: int) -> bytes:
    """返回 4 字节 P，使 zlib.crc32(data + P) == target_crc。"""
    current = zlib.crc32(data) & 0xFFFFFFFF
    raw_state = current ^ 0xFFFFFFFF          # 处理完 data 之后的 raw accumulator
    target_raw = target_crc ^ 0xFFFFFFFF      # 目标 raw accumulator

    if raw_state == target_raw:
        return b'\x00\x00\x00\x00'  # 已匹配，追加 4 个 0 字节不影响 CRC（其实会改变）

    # 反向 4 步，记录每步的 idx 与"state_prev 的高 24 位"
    # forward: R_new = (R_old >> 8) ^ TABLE[(R_old ^ b) & 0xFF]
    #   令 idx = (R_old ^ b) & 0xFF, 则 TABLE[idx] = R_new ^ (R_old >> 8)
    #   R_new 的高字节 == TABLE[idx] 的高字节（因为 R_old >> 8 是 24-bit）
    #   故 idx = REVERSE_HI[R_new >> 24]，R_old 的高 24 位 = R_new ^ TABLE[idx] 的低 24 位
    backward = []  # 元素：(idx_for_this_step)
    state = target_raw
    for _ in range(4):
        h = (state >> 24) & 0xFF
        idx = REVERSE_HI[h]
        backward.append(idx)
        # R_old 高 24 位：
        high24 = (state ^ FORWARD[idx]) & 0x00FFFFFF
        # 低 8 位未知，置 0 进入下一步（不影响后续高字节推导）
        state = (high24 << 8) & 0xFFFFFFFF

    # 此时 state 的高 24 位 == raw_state 的高 24 位（数学保证，因为映射是双射）
    # 4 步前向求 P：
    P = bytearray(4)
    cur = raw_state
    for i in range(4):
        idx = backward[3 - i]
        P[i] = idx ^ (cur & 0xFF)
        cur = (cur >> 8) ^ FORWARD[idx]
        cur &= 0xFFFFFFFF

    if cur != target_raw:
        raise RuntimeError(
            f'CRC32 patch 自检失败：0x{cur:08X} != 0x{target_raw:08X}'
        )
    return bytes(P)


def patch_file_crc(file_path: str, target_crc: int) -> bool:
    """在 file_path 末尾追加 4 字节让整体 CRC32 == target_crc。

    返回 True 表示已修补；False 表示原本就匹配，无需修补。"""
    with open(file_path, 'rb') as f:
        data = f.read()
    current = zlib.crc32(data) & 0xFFFFFFFF
    if current == (target_crc & 0xFFFFFFFF):
        return False
    patch = compute_patch_bytes(data, target_crc)
    with open(file_path, 'ab') as f:
        f.write(patch)
    # 验证
    with open(file_path, 'rb') as f:
        new_data = f.read()
    new_crc = zlib.crc32(new_data) & 0xFFFFFFFF
    if new_crc != (target_crc & 0xFFFFFFFF):
        raise RuntimeError(f'修补后 CRC 仍不匹配：0x{new_crc:08X} != 0x{target_crc:08X}')
    return True


def monkeypatch_crcmanip() -> None:
    """替换 crcmanip.fastcrc.crc_next/crc_prev 为纯 Python 实现。

    让 bundle.py 里的 _patch_crc 不再触发 C 扩展的 OverflowError。"""
    import sys
    import crcmanip.fastcrc as fastcrc
    import crcmanip.crc as crcmod

    def py_crc_next(codec, source: bytes, value: int) -> int:
        table = codec.lookup_table
        v = value & 0xFFFFFFFF
        for b in source:
            v = (v >> 8) ^ table[(v ^ b) & 0xFF]
        return v & 0xFFFFFFFF

    def py_crc_prev(codec, source: bytes, value: int) -> int:
        # 反向步进，按字节倒序（与 fastcrc.c CrcPrev 的 big_endian=False 分支一致）
        # forward: R_new = (R_old >> 8) ^ TABLE[(R_old ^ b) & 0xFF]
        # reverse: index = R_new >> shift  (shift = 24 for 32-bit)
        #          R_old = byte ^ lookup_table_reverse[index] ^ (R_new << 8)
        num_bytes = codec.num_bytes
        num_bits = codec.num_bits
        shift = (num_bytes << 3) - 8
        mask = (1 << num_bits) - 1
        rev_table = codec.lookup_table_reverse
        v = value & mask
        for c in reversed(source):
            index = (v >> shift) & 0xFF
            v = (c ^ rev_table[index] ^ ((v << 8) & mask)) & mask
        return v

    fastcrc.crc_next = py_crc_next
    fastcrc.crc_prev = py_crc_prev
    crcmod.crc_next = py_crc_next
    crcmod.crc_prev = py_crc_prev


if __name__ == '__main__':
    import os, random, tempfile
    random.seed(42)
    for trial in range(5):
        data = bytes(random.randint(0, 255) for _ in range(random.randint(100, 5000)))
        target = random.randint(0, 0xFFFFFFFF)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            path = f.name
        try:
            patched = patch_file_crc(path, target)
            with open(path, 'rb') as f:
                new_data = f.read()
            actual = zlib.crc32(new_data) & 0xFFFFFFFF
            ok = actual == target
            print(f'Trial {trial+1}: orig_len={len(data)} target=0x{target:08X} '
                  f'actual=0x{actual:08X} patched={patched} {"✓" if ok else "✗"}')
        finally:
            os.unlink(path)
