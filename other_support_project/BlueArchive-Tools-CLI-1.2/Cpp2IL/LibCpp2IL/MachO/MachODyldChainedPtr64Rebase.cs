namespace LibCpp2IL.MachO
{
    public class MachODyldChainedPtr64Rebase : ReadableClass
    {
        private ulong _value;
        
        public ulong Target => _value & 0xfffffffff;
        public ulong High8 => (_value >> 36) & 0xff;
        public ulong Reserved => (_value >> (36 + 8)) & 0x7f;
        public ulong Next => (_value >> (36 + 8 + 7)) & 0xfff;
        public bool Bind => ((_value >> (36 + 8 + 7 + 12)) & 0x1) == 0x1;

        public override void Read(ClassReadingBinaryReader reader)
        {
            _value = reader.ReadUInt64();
        }
    }
}
