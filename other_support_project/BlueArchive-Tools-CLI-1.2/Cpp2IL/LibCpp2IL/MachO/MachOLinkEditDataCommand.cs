namespace LibCpp2IL.MachO
{
    public class MachOLinkEditDataCommand : ReadableClass
    {
        public uint Offset;
        public uint Size;

        public override void Read(ClassReadingBinaryReader reader)
        { 
            Offset = reader.ReadUInt32();
            Size = reader.ReadUInt32();
        }
    }
}
