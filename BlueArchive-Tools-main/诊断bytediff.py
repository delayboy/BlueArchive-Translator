"""字节级 diff：找到原始/重打包 bytes 第一个不一致的位置，并解释那段是什么。"""
import flatbuffers
from FlatData.dump_wrapper import dump_CharacterDialogEventExcel
from FlatData.CharacterDialogEventExcel import CharacterDialogEventExcel
from FlatData.repack_wrapper import pack_CharacterDialogEventExcel


def main():
    test_bytes = b'@\x00\x00\x00\x00\x00:\x00|\x00p\x00h\x00`\x00X\x00T\x00P\x00L\x00\x00\x00\x00\x00@\x00\x00\x00<\x00\x00\x00\x00\x008\x004\x000\x00,\x00(\x00$\x00 \x00\x1f\x00\x18\x00\x14\x00\x00\x00\x08\x00\x04\x00:\x00\x00\x00x\x00\x00\x00\x85J]\x05\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x01\x88\x00\x00\x00\x8c\x00\x00\x00\xd0\x00\x00\x00\x08\x01\x00\x00\x94\x01\x00\x00\xe4\x01\x00\x00\x18\x02\x00\x00\x1c\x02\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00"\x00\x00\x00\x03\x00\x00\x00\xbd\x02\x00\x00\x00\x00\x00\x00\x1a\'\x00\x00\x00\x00\x00\x004N\x00\x00\x00\x00\x00\x00\xa9uMq\x00\x00\x00\x00\x00\x00\x00\x00&\x00\x00\x00CVGroup_UISpecialOperationLobby_Enter1\x00\x00\x01\x00\x00\x00\x0e0\x10\x18C\x00\x00\x00It\'s time for the Super Phenomenon Task Force to begin its mission.\x005\x00\x00\x00\xe9\x82\xa3\xe9\xba\xbc\xef\xbc\x8c\xe9\x96\x8b\xe5\xa7\x8b\n\xe7\x89\xb9\xe7\x95\xb0\xe7\x8f\xbe\xe8\xb1\xa1\xe6\x90\x9c\xe6\x9f\xa5\xe9\x83\xa8\xe7\x9a\x84\n\xe6\xb4\xbb\xe5\x8b\x95\xe5\x90\xa7\xe3\x80\x82\x00\x00\x00\x8b\x00\x00\x00\xe0\xb8\xa1\xe0\xb8\xb2\xe0\xb9\x80\xe0\xb8\xa3\xe0\xb8\xb5\xe0\xb9\x88\xe0\xb8\xa1\xe0\xb8\xa0\xe0\xb8\xb2\xe0\xb8\xa3\xe0\xb8\x81\xe0\xb8\xb4\xe0\xb8\x88\xe0\xb8\x82\xe0\xb8\xad\xe0\xb8\x87\xe0\xb8\x8a\xe0\xb8\xa1\xe0\xb8\xa3\xe0\xb8\xa1\n\xe0\xb8\x9b\xe0\xb8\xa3\xe0\xb8\xb2\xe0\xb8\x81\xe0\xb8\x8f\xe0\xb8\x81\xe0\xb8\xb2\xe0\xb8\xa3\xe0\xb8\x93\xe0\xb9\x8c\xe0\xb8\xa5\xe0\xb8\xb5\xe0\xb9\x89\xe0\xb8\xa5\xe0\xb8\xb1\xe0\xb8\x9a\xe0\xb9\x80\xe0\xb8\xa5\xe0\xb8\xa2\xe0\xb8\x94\xe0\xb8\xb5\xe0\xb9\x84\xe0\xb8\xab\xe0\xb8\xa1\xe0\xb8\x84\xe0\xb8\xb0\x00M\x00\x00\x00\xe3\x81\xa7\xe3\x81\xaf\xe3\x80\x81\n\xe7\x89\xb9\xe7\x95\xb0\xe7\x8f\xbe\xe8\xb1\xa1\xe6\x8d\x9c\xe6\x9f\xbb\xe9\x83\xa8\xe3\x81\xa8\xe3\x81\x97\xe3\x81\xa6\xe3\x81\xae\n\xe6\xb4\xbb\xe5\x8b\x95\xe3\x82\x92\xe5\xa7\x8b\xe3\x82\x81\xe3\x81\xbe\xe3\x81\x97\xe3\x82\x87\xe3\x81\x86\xe3\x81\x8b\xe3\x80\x82\x00\x00\x001\x00\x00\x00\xec\xb4\x88\xed\x98\x84\xec\x83\x81\xed\x8a\xb9\xeb\xac\xb4\xeb\xb6\x80\xec\x9d\x98 \xec\x9e\x84\xeb\xac\xb4.\n\xec\x8b\x9c\xec\x9e\x91\xed\x95\xb4\xeb\xb3\xb4\xea\xb9\x8c\xec\x9a\x94.\x00\x00\x00\x02\x00\x00\x0003\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    fb = CharacterDialogEventExcel.GetRootAs(test_bytes)
    json_data = dump_CharacterDialogEventExcel(fb)
    builder = flatbuffers.Builder(4096)
    offset = pack_CharacterDialogEventExcel(builder, json_data, False)
    builder.Finish(offset)
    out = bytes(builder.Output())

    print(f"len orig={len(test_bytes)}, len repack={len(out)}")

    # Find first diff
    first_diff = -1
    last_diff = -1
    diffs = []
    for i in range(min(len(test_bytes), len(out))):
        if test_bytes[i] != out[i]:
            if first_diff == -1:
                first_diff = i
            last_diff = i
            diffs.append(i)

    print(f"First diff at byte offset: {first_diff}")
    print(f"Last diff at byte offset: {last_diff}")
    print(f"Total differing bytes: {len(diffs)}")

    if first_diff >= 0:
        # Show context around first diff
        lo = max(0, first_diff - 16)
        hi = min(min(len(test_bytes), len(out)), first_diff + 32)
        print(f"\nBytes [{lo}, {hi}) ORIGINAL:")
        print(" ".join(f"{b:02x}" for b in test_bytes[lo:hi]))
        print(f"Bytes [{lo}, {hi}) REPACKED:")
        print(" ".join(f"{b:02x}" for b in out[lo:hi]))

    # Show all diff ranges (consecutive)
    print("\nAll diff ranges:")
    if diffs:
        start = diffs[0]
        prev = diffs[0]
        for d in diffs[1:]:
            if d == prev + 1:
                prev = d
            else:
                print(f"  [{start}, {prev}]  ({prev - start + 1} bytes)")
                start = d
                prev = d
        print(f"  [{start}, {prev}]  ({prev - start + 1} bytes)")

    # Check root table position
    root1 = int.from_bytes(test_bytes[0:4], "little")
    root2 = int.from_bytes(out[0:4], "little")
    print(f"\nRoot table offset: orig={root1}, repack={root2}")

    # Look at the vtable position and dump it from both
    def vtable_dump(buf, label):
        root = int.from_bytes(buf[0:4], "little")
        soffset = int.from_bytes(buf[root:root+4], "little", signed=True)
        vt_pos = root - soffset
        vt_size = int.from_bytes(buf[vt_pos:vt_pos+2], "little")
        print(f"\n{label} vtable @ {vt_pos}, size={vt_size}")
        print("  raw:", " ".join(f"{b:02x}" for b in buf[vt_pos:vt_pos+vt_size]))

    vtable_dump(test_bytes, "ORIGINAL")
    vtable_dump(out, "REPACKED")

    # Dump the table data area (after vtable, before string data)
    print(f"\nOriginal table data area (offset {root1}, len ~124):")
    print(" ".join(f"{b:02x}" for b in test_bytes[root1:root1+124]))
    print(f"\nRepacked table data area (offset {root2}, len ~124):")
    print(" ".join(f"{b:02x}" for b in out[root2:root2+124]))

    # Look at VoiceId vector in detail. VoiceId slot value is 32, so vector offset is at root+32.
    def read_voiceid(buf, label):
        root = int.from_bytes(buf[0:4], "little")
        soffset = int.from_bytes(buf[root:root+4], "little", signed=True)
        vt_pos = root - soffset
        vt_size = int.from_bytes(buf[vt_pos:vt_pos+2], "little")
        # VoiceId is at voffset 44, slot index (44-4)/2 = 20
        slot_idx = 20
        if slot_idx < (vt_size - 4) // 2:
            slot_val = int.from_bytes(buf[vt_pos + 4 + slot_idx*2: vt_pos + 4 + slot_idx*2 + 2], "little")
            print(f"\n{label} VoiceId slot value (vtable[20]) = {slot_val}")
            if slot_val != 0:
                vec_uoffset_pos = root + slot_val
                vec_off = int.from_bytes(buf[vec_uoffset_pos:vec_uoffset_pos+4], "little")
                vec_data_pos = vec_uoffset_pos + vec_off
                vec_len = int.from_bytes(buf[vec_data_pos:vec_data_pos+4], "little")
                print(f"  vector uoffset @ {vec_uoffset_pos}, value={vec_off}, vector data @ {vec_data_pos}, len={vec_len}")
                for j in range(vec_len):
                    val = int.from_bytes(buf[vec_data_pos + 4 + j*4: vec_data_pos + 4 + j*4 + 4], "little")
                    print(f"  VoiceId[{j}] = {val} (0x{val:08x})")
                # Show raw bytes around vector
                print(f"  raw bytes around vector ({vec_data_pos - 4}, 16 bytes):")
                print("    ", " ".join(f"{b:02x}" for b in buf[max(0,vec_data_pos-4):vec_data_pos+12]))

    read_voiceid(test_bytes, "ORIGINAL")
    read_voiceid(out, "REPACKED")


if __name__ == "__main__":
    main()
