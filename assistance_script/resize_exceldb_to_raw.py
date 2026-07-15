"""
resize_exceldb_to_raw.py

Resize ExcelDB.db (binary, in-place) to match ExcelDB-raw.db's file size,
and optionally match its CRC32 checksum -- without breaking DB functionality.

Strategy
--------
SQLCipher/SQLite reads the page count from the (encrypted) page-1 header and
ignores any bytes past the official end of the database. So we can safely
APPEND bytes to grow the file; the DB will still open and query identically.

For CRC32 matching, the last 4 bytes of the appended padding are computed
via GF(2) linear algebra so the whole-file CRC32 equals the reference.
CRC32 is affine over GF(2), and 4 bytes (32 bits) is exactly enough to
force any target CRC -- always solvable.

Usage
-----
    python resize_exceldb_to_raw.py             # pad + match CRC32
    python resize_exceldb_to_raw.py --no-crc    # pad to size only
    python resize_exceldb_to_raw.py --zeros     # use 0x00 padding instead of random
    python resize_exceldb_to_raw.py --restore   # restore from .bak
    python resize_exceldb_to_raw.py --self-test # verify CRC patcher
"""
import os
import sys
import shutil
import binascii
import argparse


HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_DB = os.path.join(HERE, "ExcelDB.db")
REFERENCE_DB = os.path.join(HERE, "ExcelDB-raw.db")
BACKUP_DB = TARGET_DB + ".bak"


# ---------------------------------------------------------------------------
# CRC32 internals (standard zlib polynomial 0xEDB88320, reflected)
# ---------------------------------------------------------------------------

_CRC32_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0xEDB88320 if (_c & 1) else (_c >> 1)
    _CRC32_TABLE.append(_c)


def _crc32_continue(state, data):
    """Continue an internal (pre-final-XOR) CRC32 state by processing data."""
    for b in data:
        state = (state >> 8) ^ _CRC32_TABLE[(state ^ b) & 0xFF]
    return state


def find_crc32_patch(prefix_state, target_crc):
    """
    Given the internal CRC32 state after a prefix, find 4 bytes that, when
    appended to the prefix, produce final CRC32 == target_crc.

    CRC32 is affine over GF(2). We build a 32x32 binary matrix where column j
    is the effect on the final state of flipping bit j of the 4-byte patch,
    then solve `A x = delta` via Gaussian elimination. 4 bytes (32 bits) is
    exactly the output width, so a solution always exists when A is full rank
    (which it is for this construction).
    """
    target_state = target_crc ^ 0xFFFFFFFF
    base_state = _crc32_continue(prefix_state, bytes(4))
    delta = base_state ^ target_state

    # Column j = effect of flipping bit j of the 4-byte patch (vs. all zero)
    bit_effects = []
    for bit_idx in range(32):
        patch = bytearray(4)
        patch[bit_idx // 8] = 1 << (bit_idx % 8)
        state = _crc32_continue(prefix_state, bytes(patch))
        bit_effects.append(state ^ base_state)

    # Augmented rows: 32 rows (one per CRC output bit), cols 0..31 = unknowns,
    # col 32 = augmented delta bit.
    rows = []
    for crc_bit in range(32):
        row = 0
        for col in range(32):
            if (bit_effects[col] >> crc_bit) & 1:
                row |= 1 << col
        if (delta >> crc_bit) & 1:
            row |= 1 << 32
        rows.append(row)

    # Gaussian elimination over GF(2)
    pivot_row_of_col = [-1] * 32
    rank = 0
    for col in range(32):
        pivot = -1
        for r in range(rank, 32):
            if (rows[r] >> col) & 1:
                pivot = r
                break
        if pivot == -1:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for r in range(32):
            if r != rank and ((rows[r] >> col) & 1):
                rows[r] ^= rows[rank]
        pivot_row_of_col[col] = rank
        rank += 1

    for r in range(rank, 32):
        if rows[r] != 0:
            raise RuntimeError("CRC32 system inconsistent (should not happen for 4-byte patch)")

    x = 0
    for col in range(32):
        pr = pivot_row_of_col[col]
        if pr != -1 and ((rows[pr] >> 32) & 1):
            x |= 1 << col

    patch = bytearray(4)
    for bit_idx in range(32):
        if (x >> bit_idx) & 1:
            patch[bit_idx // 8] |= 1 << (bit_idx % 8)
    return bytes(patch)


def crc32_file(path, chunk_size=1 << 20):
    """Stream CRC32 of a (possibly large) file."""
    crc = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            crc = binascii.crc32(chunk, crc)
    return crc & 0xFFFFFFFF


def crc32_data(data, chunk_size=1 << 20):
    """CRC32 of an in-memory buffer, chunked to avoid slicing copies."""
    crc = 0
    for i in range(0, len(data), chunk_size):
        crc = binascii.crc32(bytes(data[i:i + chunk_size]), crc)
    return crc & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test():
    import random
    rng = random.Random(42)
    print("[*] Running CRC32 patcher self-test (100 random trials)...")
    for trial in range(100):
        prefix = bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 200)))
        target = rng.randint(0, 0xFFFFFFFF)
        prefix_state = (binascii.crc32(prefix) & 0xFFFFFFFF) ^ 0xFFFFFFFF
        patch = find_crc32_patch(prefix_state, target)
        got = binascii.crc32(prefix + patch) & 0xFFFFFFFF
        if got != target:
            print(f"[-] Trial {trial} FAILED: got {got:08X}, want {target:08X}")
            return False
    print("[+] Self-test passed.")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Resize ExcelDB.db to match ExcelDB-raw.db (size + optional CRC32).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--no-crc", action="store_true",
                        help="only pad to size, skip CRC matching")
    parser.add_argument("--restore", action="store_true",
                        help="restore ExcelDB.db from the .bak backup and exit")
    parser.add_argument("--self-test", action="store_true",
                        help="run CRC patcher self-test and exit")
    parser.add_argument("--zeros", action="store_true",
                        help="pad with 0x00 instead of random bytes")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(0 if self_test() else 1)

    if args.restore:
        if not os.path.exists(BACKUP_DB):
            print(f"[-] No backup at {BACKUP_DB}")
            sys.exit(1)
        shutil.copy2(BACKUP_DB, TARGET_DB)
        print(f"[+] Restored {TARGET_DB} from {BACKUP_DB}")
        return

    if not os.path.exists(TARGET_DB):
        print(f"[-] Missing: {TARGET_DB}")
        sys.exit(1)
    if not os.path.exists(REFERENCE_DB):
        print(f"[-] Missing: {REFERENCE_DB}")
        sys.exit(1)

    target_size = os.path.getsize(REFERENCE_DB)
    current_size = os.path.getsize(TARGET_DB)
    print(f"[*] {os.path.basename(TARGET_DB)}:  {current_size:,} bytes ({current_size/1024/1024:.2f} MB)")
    print(f"[*] {os.path.basename(REFERENCE_DB)}: {target_size:,} bytes ({target_size/1024/1024:.2f} MB)")

    if current_size > target_size:
        print(f"[!] Current file is LARGER than reference by {current_size - target_size:,} bytes.")
        print(f"    Truncating an encrypted DB would corrupt it; aborting.")
        sys.exit(1)

    diff = target_size - current_size
    need_crc = (not args.no_crc) and diff >= 4

    if diff == 0 and not need_crc:
        print("[*] Sizes already match and CRC step not needed; nothing to do.")
        return

    # Backup (only first time)
    if not os.path.exists(BACKUP_DB):
        shutil.copy2(TARGET_DB, BACKUP_DB)
        print(f"[+] Backup created: {BACKUP_DB}")
    else:
        print(f"[*] Backup already exists, leaving it: {BACKUP_DB}")

    # Read current file fully
    print("[*] Reading current file into memory...")
    with open(TARGET_DB, "rb") as f:
        data = bytearray(f.read())
    assert len(data) == current_size

    if diff > 0:
        if need_crc:
            pad_len = diff - 4          # random/zero padding
            patch_offset = current_size + pad_len  # == target_size - 4
        else:
            pad_len = diff
            patch_offset = None

        if pad_len > 0:
            pad = (b"\x00" * pad_len) if args.zeros else os.urandom(pad_len)
            data.extend(pad)
            kind = "zero" if args.zeros else "random"
            print(f"[+] Added {pad_len:,} bytes of {kind} padding at offset {current_size}.")

        if need_crc:
            data.extend(b"\x00\x00\x00\x00")  # placeholder for the 4-byte CRC patch

    assert len(data) == target_size, f"size mismatch {len(data)} != {target_size}"

    if need_crc:
        print("[*] Computing reference CRC32...")
        target_crc = crc32_file(REFERENCE_DB)
        print(f"[*] Target CRC32: {target_crc:08X}")

        print(f"[*] Computing CRC32 over prefix ({patch_offset:,} bytes)...")
        prefix_crc = crc32_data(data[:patch_offset])
        prefix_state = prefix_crc ^ 0xFFFFFFFF

        print("[*] Solving 32x32 GF(2) system for 4-byte CRC patch...")
        patch = find_crc32_patch(prefix_state, target_crc)
        data[patch_offset:patch_offset + 4] = patch
        print(f"[*] Patch bytes @ offset 0x{patch_offset:X}: {patch.hex()}")

        verify_crc = crc32_data(data)
        print(f"[*] In-memory CRC32:  {verify_crc:08X}")
        print(f"[*] Target CRC32:     {target_crc:08X}")
        if verify_crc != target_crc:
            print("[!] In-memory CRC mismatch -- aborting, file not written.")
            sys.exit(1)

    # Write back
    print(f"[*] Writing {len(data):,} bytes to {TARGET_DB}...")
    with open(TARGET_DB, "wb") as f:
        f.write(bytes(data))

    # Verify on disk
    disk_size = os.path.getsize(TARGET_DB)
    print(f"[*] On-disk size:  {disk_size:,} (target {target_size:,})")
    if disk_size != target_size:
        print("[!] On-disk size mismatch!")
        sys.exit(1)

    if need_crc:
        disk_crc = crc32_file(TARGET_DB)
        ref_crc = crc32_file(REFERENCE_DB)
        print(f"[*] On-disk CRC32:     {disk_crc:08X}")
        print(f"[*] Reference CRC32:   {ref_crc:08X}")
        if disk_crc != ref_crc:
            print("[!] On-disk CRC mismatch!")
            sys.exit(1)

    print()
    print("[+] Done.")
    print(f"    Size matches:  {disk_size == target_size}")
    if need_crc:
        print(f"    CRC32 matches: True")
    print()
    print("Next: verify the DB still opens with:")
    print("    python view_bluearchive_db.py")
    print("If it fails, restore with:")
    print("    python resize_exceldb_to_raw.py --restore")


if __name__ == "__main__":
    main()
