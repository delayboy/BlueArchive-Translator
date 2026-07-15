namespace LibCpp2IL.MachO
{
    public class MachODyldChainedFixupsHeader : ReadableClass
    {
        public const uint SupportedFixupsVersion = 0;
        public const uint SupportedImportsFormat = 1; //DYLD_CHAINED_IMPORT
        
        public uint FixupsVersion;
        public uint StartsOffset;
        public uint ImportsOffset;
        public uint SymbolsOffset;
        public uint ImportsCount;
        public uint ImportsFormat;
        public uint SymbolsFormat;

        public override void Read(ClassReadingBinaryReader reader)
        {
            FixupsVersion = reader.ReadUInt32();
            StartsOffset = reader.ReadUInt32();
            ImportsOffset = reader.ReadUInt32();
            SymbolsOffset = reader.ReadUInt32();
            ImportsCount = reader.ReadUInt32();
            ImportsFormat = reader.ReadUInt32();
            SymbolsFormat = reader.ReadUInt32();
        }
    }
}
