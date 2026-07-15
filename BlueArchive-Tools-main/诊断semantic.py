"""深度语义对比：逐字段读取原始/repack 数据，并对比实际字符串/向量字节。"""
import flatbuffers
from FlatData.dump_wrapper import dump_CharacterDialogEventExcel
from FlatData.CharacterDialogEventExcel import CharacterDialogEventExcel
from FlatData.repack_wrapper import pack_CharacterDialogEventExcel

test_bytes = b'@\x00\x00\x00\x00\x00:\x00|\x00p\x00h\x00`\x00X\x00T\x00P\x00L\x00\x00\x00\x00\x00@\x00\x00\x00<\x00\x00\x00\x00\x008\x004\x000\x00,\x00(\x00$\x00 \x00\x1f\x00\x18\x00\x14\x00\x00\x00\x08\x00\x04\x00:\x00\x00\x00x\x00\x00\x00\x85J]\x05\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x01\x88\x00\x00\x00\x8c\x00\x00\x00\xd0\x00\x00\x00\x08\x01\x00\x00\x94\x01\x00\x00\xe4\x01\x00\x00\x18\x02\x00\x00\x1c\x02\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00"\x00\x00\x00\x03\x00\x00\x00\xbd\x02\x00\x00\x00\x00\x00\x00\x1a\'\x00\x00\x00\x00\x00\x004N\x00\x00\x00\x00\x00\x00\xa9uMq\x00\x00\x00\x00\x00\x00\x00\x00&\x00\x00\x00CVGroup_UISpecialOperationLobby_Enter1\x00\x00\x01\x00\x00\x00\x0e0\x10\x18C\x00\x00\x00It\'s time for the Super Phenomenon Task Force to begin its mission.\x005\x00\x00\x00\xe9\x82\xa3\xe9\xba\xbc\xef\xbc\x8c\xe9\x96\x8b\xe5\xa7\x8b\n\xe7\x89\xb9\xe7\x95\xb0\xe7\x8f\xbe\xe8\xb1\xa1\xe6\x90\x9c\xe6\x9f\xa5\xe9\x83\xa8\xe7\x9a\x84\n\xe6\xb4\xbb\xe5\x8b\x95\xe5\x90\xa7\xe3\x80\x82\x00\x00\x00\x8b\x00\x00\x00\xe0\xb8\xa1\xe0\xb8\xb2\xe0\xb9\x80\xe0\xb8\xa3\xe0\xb8\xb5\xe0\xb9\x88\xe0\xb8\xa1\xe0\xb8\xa0\xe0\xb8\xb2\xe0\xb8\xa3\xe0\xb8\x81\xe0\xb8\xb4\xe0\xb8\x88\xe0\xb8\x82\xe0\xb8\xad\xe0\xb8\x87\xe0\xb8\x8a\xe0\xb8\xa1\xe0\xb8\xa3\xe0\xb8\xa1\n\xe0\xb8\x9b\xe0\xb8\xa3\xe0\xb8\xb2\xe0\xb8\x81\xe0\xb8\x8f\xe0\xb8\x81\xe0\xb8\xb2\xe0\xb8\xa3\xe0\xb8\x93\xe0\xb9\x8c\xe0\xb8\xa5\xe0\xb8\xb5\xe0\xb9\x89\xe0\xb8\xa5\xe0\xb8\xb1\xe0\xb8\x9a\xe0\xb9\x80\xe0\xb8\xa5\xe0\xb8\xa2\xe0\xb8\x94\xe0\xb8\xb5\xe0\xb9\x84\xe0\xb8\xab\xe0\xb8\xa1\xe0\xb8\x84\xe0\xb8\xb0\x00M\x00\x00\x00\xe3\x81\xa7\xe3\x81\xaf\xe3\x80\x81\n\xe7\x89\xb9\xe7\x95\xb0\xe7\x8f\xbe\xe8\xb1\xa1\xe6\x8d\x9c\xe6\x9f\xbb\xe9\x83\xa8\xe3\x81\xa8\xe3\x81\x97\xe3\x81\xa6\xe3\x81\xae\n\xe6\xb4\xbb\xe5\x8b\x95\xe3\x82\x92\xe5\xa7\x8b\xe3\x82\x81\xe3\x81\xbe\xe3\x81\x97\xe3\x82\x87\xe3\x81\x86\xe3\x81\x8b\xe3\x80\x82\x00\x00\x001\x00\x00\x00\xec\xb4\x88\xed\x98\x84\xec\x83\x81\xed\x8a\xb9\xeb\xac\xb4\xeb\xb6\x80\xec\x9d\x98 \xec\x9e\x84\xeb\xac\xb4.\n\xec\x8b\x9c\xec\x9e\x91\xed\x95\xb4\xeb\xb3\xb4\xea\xb9\x8c\xec\x9a\x94.\x00\x00\x00\x02\x00\x00\x0003\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

fb = CharacterDialogEventExcel.GetRootAs(test_bytes)
json_data = dump_CharacterDialogEventExcel(fb)
builder = flatbuffers.Builder(4096)
offset = pack_CharacterDialogEventExcel(builder, json_data, False)
builder.Finish(offset)
out = bytes(builder.Output())
fb2 = CharacterDialogEventExcel.GetRootAs(out)

# Direct accessor comparison
print("=" * 70)
print("Field-by-field direct accessor comparison")
print("=" * 70)
fields_to_check = [
    ("CostumeUniqueId", lambda f: f.CostumeUniqueId()),
    ("OriginalCharacterId", lambda f: f.OriginalCharacterId()),
    ("DisplayOrder", lambda f: f.DisplayOrder()),
    ("EventID", lambda f: f.EventID()),
    ("ProductionStep", lambda f: f.ProductionStep()),
    ("DialogCategory", lambda f: f.DialogCategory()),
    ("DialogCondition", lambda f: f.DialogCondition()),
    ("DialogConditionDetail", lambda f: f.DialogConditionDetail()),
    ("DialogConditionDetailValue", lambda f: f.DialogConditionDetailValue()),
    ("GroupId", lambda f: f.GroupId()),
    ("DialogType", lambda f: f.DialogType()),
    ("ActionName", lambda f: f.ActionName()),
    ("Duration", lambda f: f.Duration()),
    ("DurationKr", lambda f: f.DurationKr()),
    ("AnimationName", lambda f: f.AnimationName()),
    ("LocalizeKR", lambda f: f.LocalizeKR()),
    ("LocalizeJP", lambda f: f.LocalizeJP()),
    ("LocalizeTH", lambda f: f.LocalizeTH()),
    ("LocalizeTW", lambda f: f.LocalizeTW()),
    ("LocalizeEN", lambda f: f.LocalizeEN()),
    ("VoiceIdLength", lambda f: f.VoiceIdLength()),
    ("VoiceId[0]", lambda f: f.VoiceId(0) if f.VoiceIdLength() > 0 else None),
    ("VoiceIdIsNone", lambda f: f.VoiceIdIsNone()),
    ("CollectionVisible", lambda f: f.CollectionVisible()),
    ("CVCollectionType", lambda f: f.CVCollectionType()),
    ("CVUnlockScenarioType", lambda f: f.CVUnlockScenarioType()),
    ("UnlockEventSeason", lambda f: f.UnlockEventSeason()),
    ("ScenarioGroupId", lambda f: f.ScenarioGroupId()),
    ("LocalizeCVGroup", lambda f: f.LocalizeCVGroup()),
    ("ScenarioCharacterShapes", lambda f: f.ScenarioCharacterShapes()),
]
for name, accessor in fields_to_check:
    v1 = accessor(fb)
    v2 = accessor(fb2)
    same = "OK" if v1 == v2 else "*** DIFFERENT ***"
    print(f"  {name:<30} orig={v1!r:<55} repack={v2!r:<55} {same}")

# Now look at the strings/vectors section in raw bytes for both
print("\n" + "=" * 70)
print("Strings/vectors section raw bytes (offset 180 to 270)")
print("=" * 70)
print("ORIG:", " ".join(f"{b:02x}" for b in test_bytes[180:270]))
print("REPK:", " ".join(f"{b:02x}" for b in out[180:270]))

# Check if any meaningful content differs by extracting all strings from both buffers
print("\n" + "=" * 70)
print("String extraction directly from raw bytes (search for length-prefixed UTF-8)")
print("=" * 70)
def find_strings(buf, label):
    print(f"\n{label}:")
    i = 0
    found = []
    while i < len(buf) - 4:
        # Check if this looks like a string length prefix
        length = int.from_bytes(buf[i:i+4], "little")
        if 1 <= length <= 200 and i + 4 + length < len(buf):
            # Check if there's a null terminator at i+4+length
            if buf[i+4+length] == 0:
                try:
                    s = buf[i+4:i+4+length].decode("utf-8")
                    if s.isprintable() or any(ord(c) > 127 for c in s):
                        found.append((i, length, s))
                        i += 4 + length + 1
                        continue
                except:
                    pass
        i += 1
    for off, length, s in found:
        preview = s[:60].replace("\n", "\\n")
        print(f"  @{off:>4} len={length:<4} {preview!r}")
    return found

s1 = find_strings(test_bytes, "ORIGINAL")
s2 = find_strings(out, "REPACKED")
