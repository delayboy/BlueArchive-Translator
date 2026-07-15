using System.Collections.Immutable;

namespace VersionedSerialization;

public interface IReader
{
    bool Is32Bit { get; }

    bool ReadBoolean();
    long ReadNInt();
    ulong ReadNUInt();
    string ReadString();
    ReadOnlySpan<byte> ReadBytes(int length);

    T ReadPrimitive<T>() where T : unmanaged;
    ImmutableArray<T> ReadPrimitiveArray<T>(long count) where T : unmanaged;

    T ReadVersionedObject<T>(in StructVersion version = default) where T : IReadable, new();
    ImmutableArray<T> ReadVersionedObjectArray<T>(long count, in StructVersion version = default) where T : IReadable, new();

    void Align(int alignment = 0);
    void Skip(int count);
}