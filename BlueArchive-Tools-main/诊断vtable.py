"""诊断脚本：对比原始 bytes 与 repack 后 bytes 的 vtable 字段存在性差异。
不属于工具本身，只用于分析。"""
import flatbuffers
from FlatData.dump_wrapper import dump_CharacterDialogEventExcel
from FlatData.CharacterDialogEventExcel import CharacterDialogEventExcel
from FlatData.repack_wrapper import pack_CharacterDialogEventExcel

# 字段名 -> vtable 内的 voffset（来自 CharacterDialogEventExcel.py）
FIELDS = [
    ("CostumeUniqueId", 4, "int64"),
    ("OriginalCharacterId", 6, "int64"),
    ("DisplayOrder", 8, "int64"),
    ("EventID", 10, "int64"),
    ("ProductionStep", 12, "int32"),
    ("DialogCategory", 14, "int32"),
    ("DialogCondition", 16, "int32"),
    ("DialogConditionDetail", 18, "int32"),
    ("DialogConditionDetailValue", 20, "int64"),
    ("GroupId", 22, "int64"),
    ("DialogType", 24, "int32"),
    ("ActionName", 26, "string"),
    ("Duration", 28, "int64"),
    ("DurationKr", 30, "int64"),
    ("AnimationName", 32, "string"),
    ("LocalizeKR", 34, "string"),
    ("LocalizeJP", 36, "string"),
    ("LocalizeTH", 38, "string"),
    ("LocalizeTW", 40, "string"),
    ("LocalizeEN", 42, "string"),
    ("VoiceId", 44, "vector"),
    ("CollectionVisible", 46, "bool"),
    ("CVCollectionType", 48, "int32"),
    ("CVUnlockScenarioType", 50, "int32"),
    ("UnlockEventSeason", 52, "int64"),
    ("ScenarioGroupId", 54, "int64"),
    ("LocalizeCVGroup", 56, "string"),
    ("ScenarioCharacterShapes", 58, "int32"),
]


def decode_vtable(buf, pos):
    """返回 (vtable_size_bytes, table_size_bytes, {voffset: slot_value})。"""
    # table 的第一个 int32 是到 vtable 的 soffset（可负）
    soffset = int.from_bytes(buf[pos:pos+4], "little", signed=True)
    vtable_pos = pos - soffset
    vtable_size = int.from_bytes(buf[vtable_pos:vtable_pos+2], "little")
    table_size = int.from_bytes(buf[vtable_pos+2:vtable_pos+4], "little")
    slots = {}
    for i in range((vtable_size - 4) // 2):
        voff = 4 + i * 2
        slot = int.from_bytes(buf[vtable_pos + voff: vtable_pos + voff + 2], "little")
        slots[4 + i * 2] = slot
    return vtable_size, table_size, slots


def present_fields(buf):
    root_off = int.from_bytes(buf[0:4], "little")
    vt_size, t_size, slots = decode_vtable(buf, root_off)
    present = {}
    for name, voff, kind in FIELDS:
        present[name] = (slots.get(voff, 0) != 0)
    return vt_size, t_size, slots, present


def main():
    test_bytes = b'@\x00\x00\x00\x00\x00:\x00|\x00p\x00h\x00`\x00X\x00T\x00P\x00L\x00\x00\x00\x00\x00@\x00\x00\x00<\x00\x00\x00\x00\x008\x004\x000\x00,\x00(\x00$\x00 \x00\x1f\x00\x18\x00\x14\x00\x00\x00\x08\x00\x04\x00:\x00\x00\x00x\x00\x00\x00\x85J]\x05\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x01\x88\x00\x00\x00\x8c\x00\x00\x00\xd0\x00\x00\x00\x08\x01\x00\x00\x94\x01\x00\x00\xe4\x01\x00\x00\x18\x02\x00\x00\x1c\x02\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00"\x00\x00\x00\x03\x00\x00\x00\xbd\x02\x00\x00\x00\x00\x00\x00\x1a\'\x00\x00\x00\x00\x00\x004N\x00\x00\x00\x00\x00\x00\xa9uMq\x00\x00\x00\x00\x00\x00\x00\x00&\x00\x00\x00CVGroup_UISpecialOperationLobby_Enter1\x00\x00\x01\x00\x00\x00\x0e0\x10\x18C\x00\x00\x00It\'s time for the Super Phenomenon Task Force to begin its mission.\x005\x00\x00\x00\xe9\x82\xa3\xe9\xba\xbc\xef\xbc\x8c\xe9\x96\x8b\xe5\xa7\x8b\n\xe7\x89\xb9\xe7\x95\xb0\xe7\x8f\xbe\xe8\xb1\xa1\xe6\x90\x9c\xe6\x9f\xa5\xe9\x83\xa8\xe7\x9a\x84\n\xe6\xb4\xbb\xe5\x8b\x95\xe5\x90\xa7\xe3\x80\x82\x00\x00\x00\x8b\x00\x00\x00\xe0\xb8\xa1\xe0\xb8\xb2\xe0\xb9\x80\xe0\xb8\xa3\xe0\xb8\xb5\xe0\xb9\x88\xe0\xb8\xa1\xe0\xb8\xa0\xe0\xb8\xb2\xe0\xb8\xa3\xe0\xb8\x81\xe0\xb8\xb4\xe0\xb8\x88\xe0\xb8\x82\xe0\xb8\xad\xe0\xb8\x87\xe0\xb8\x8a\xe0\xb8\xa1\xe0\xb8\xa3\xe0\xb8\xa1\n\xe0\xb8\x9b\xe0\xb8\xa3\xe0\xb8\xb2\xe0\xb8\x81\xe0\xb8\x8f\xe0\xb8\x81\xe0\xb8\xb2\xe0\xb8\xa3\xe0\xb8\x93\xe0\xb9\x8c\xe0\xb8\xa5\xe0\xb8\xb5\xe0\xb9\x89\xe0\xb8\xa5\xe0\xb8\xb1\xe0\xb8\x9a\xe0\xb9\x80\xe0\xb8\xa5\xe0\xb8\xa2\xe0\xb8\x94\xe0\xb8\xb5\xe0\xb9\x84\xe0\xb8\xab\xe0\xb8\xa1\xe0\xb8\x84\xe0\xb8\xb0\x00M\x00\x00\x00\xe3\x81\xa7\xe3\x81\xaf\xe3\x80\x81\n\xe7\x89\xb9\xe7\x95\xb0\xe7\x8f\xbe\xe8\xb1\xa1\xe6\x8d\x9c\xe6\x9f\xbb\xe9\x83\xa8\xe3\x81\xa8\xe3\x81\x97\xe3\x81\xa6\xe3\x81\xae\n\xe6\xb4\xbb\xe5\x8b\x95\xe3\x82\x92\xe5\xa7\x8b\xe3\x82\x81\xe3\x81\xbe\xe3\x81\x97\xe3\x82\x87\xe3\x81\x86\xe3\x81\x8b\xe3\x80\x82\x00\x00\x001\x00\x00\x00\xec\xb4\x88\xed\x98\x84\xec\x83\x81\xed\x8a\xb9\xeb\xac\xb4\xeb\xb6\x80\xec\x9d\x98 \xec\x9e\x84\xeb\xac\xb4.\n\xec\x8b\x9c\xec\x9e\x91\xed\x95\xb4\xeb\xb3\xb4\xea\xb9\x8c\xec\x9a\x94.\x00\x00\x00\x02\x00\x00\x0003\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    fb = CharacterDialogEventExcel.GetRootAs(test_bytes)
    json_data = dump_CharacterDialogEventExcel(fb)

    builder = flatbuffers.Builder(4096)
    offset = pack_CharacterDialogEventExcel(builder, json_data, False)
    builder.Finish(offset)
    out = bytes(builder.Output())

    fb2 = CharacterDialogEventExcel.GetRootAs(out)
    json_data2 = dump_CharacterDialogEventExcel(fb2)

    print("=" * 60)
    print("JSON dump from ORIGINAL bytes:")
    print(json_data)
    print("=" * 60)
    print("JSON dump from REPACKED bytes:")
    print(json_data2)
    print("=" * 60)
    print("JSON equal?", json_data == json_data2)
    print("Bytes equal?", test_bytes == out)
    print("Original len:", len(test_bytes), "Repacked len:", len(out))

    vt1, t1, slots1, present1 = present_fields(test_bytes)
    vt2, t2, slots2, present2 = present_fields(out)

    print("=" * 60)
    print(f"Original vtable_size={vt1}, table_size={t1}")
    print(f"Repacked  vtable_size={vt2}, table_size={t2}")

    print("=" * 60)
    print("Field presence comparison (only showing differences):")
    print(f"{'Field':<28} {'Original':<10} {'Repacked':<10} {'Changed?':<10}")
    diff_count = 0
    for name, voff, kind in FIELDS:
        p1 = present1[name]
        p2 = present2[name]
        changed = "YES" if p1 != p2 else ""
        if p1 != p2:
            diff_count += 1
        print(f"{name:<28} {str(p1):<10} {str(p2):<10} {changed:<10}")
    print(f"\nTotal field-presence differences: {diff_count}")

    print("=" * 60)
    print("Per-slot vtable values (voffset -> slot):")
    print(f"{'voff':<6} {'field':<28} {'orig':<8} {'repack':<8}")
    for name, voff, kind in FIELDS:
        s1 = slots1.get(voff, 0)
        s2 = slots2.get(voff, 0)
        print(f"{voff:<6} {name:<28} {s1:<8} {s2:<8}")

    print("=" * 60)
    print("VoiceIdIsNone():")
    print(f"  Original: {fb.VoiceIdIsNone()}")
    print(f"  Repacked: {fb2.VoiceIdIsNone()}")


if __name__ == "__main__":
    main()
