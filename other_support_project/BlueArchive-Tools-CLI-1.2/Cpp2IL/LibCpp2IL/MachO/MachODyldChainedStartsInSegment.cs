namespace LibCpp2IL.MachO
{
    public class MachODyldChainedStartsInSegment : ReadableClass
    {
        public const ushort DYLD_CHAINED_PTR_START_NONE = 0xffff;
        public const int Size = sizeof(uint) * 2 + sizeof(ushort) * 3 + sizeof(ulong);
        
        public uint StructSize;
        public ushort PageSize;
        public ushort PointerFormat;
        public ulong SegmentOffset;
        public uint MaxValidPointer;
        public ushort PageCount;

        public override void Read(ClassReadingBinaryReader reader)
        {
            StructSize = reader.ReadUInt32();
            PageSize = reader.ReadUInt16();
            PointerFormat = reader.ReadUInt16();
            SegmentOffset = reader.ReadUInt64();
            MaxValidPointer = reader.ReadUInt32();
            PageCount = reader.ReadUInt16();
        }
    }
}
