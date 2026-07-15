namespace VersionedSerialization;

public interface IReadable
{
    public void Read<TReader>(ref TReader reader, in StructVersion version = default) where TReader : IReader, allows ref struct;
    public static abstract int Size(in StructVersion version = default, bool is32Bit = false);
}