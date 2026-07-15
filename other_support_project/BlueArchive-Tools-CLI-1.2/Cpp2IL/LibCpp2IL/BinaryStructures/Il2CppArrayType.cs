using System;

namespace LibCpp2IL.BinaryStructures;

public class Il2CppArrayType : ReadableClass
{
    // Populated by the caller after reading.
    internal Il2CppBinary? OwningBinary { get; set; }

    public ulong etype;
    public byte rank;
    public byte numsizes;
    public byte numlobounds;
    public ulong sizes;
    public ulong lobounds;

    public Il2CppType? ElementType
    {
        get
        {
            var binary = OwningBinary ?? LibCpp2IlMain.Binary;
            return binary == null ? null : binary.GetIl2CppTypeFromPointer(etype);
        }
    }

    public Il2CppType GetElementTypeOrThrow()
        => ElementType ?? throw new InvalidOperationException("No binary context available to resolve Il2CppArrayType.ElementType");

    public override void Read(ClassReadingBinaryReader reader)
    {
        etype = reader.ReadNUint();
        rank = reader.ReadByte();
        numsizes = reader.ReadByte();
        numlobounds = reader.ReadByte();
        sizes = reader.ReadNUint();
        lobounds = reader.ReadNUint();
    }
}
