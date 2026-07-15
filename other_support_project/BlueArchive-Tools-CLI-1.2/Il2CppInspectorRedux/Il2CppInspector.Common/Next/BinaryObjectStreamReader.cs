using System.Collections.Immutable;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using NoisyCowStudios.Bin2Object;
using VersionedSerialization;

namespace Il2CppInspector.Next;

public class BinaryObjectStreamReader : BinaryObjectStream, IReader
{
    public new StructVersion Version
    {
        get => _version;
        set
        {
            _version = value;
            base.Version = _version.AsDouble;
        }
    }

    private StructVersion _version;

    public virtual int Bits { get; set; }
    public bool Is32Bit => Bits == 32;

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static TTo Cast<TFrom, TTo>(in TFrom from) => Unsafe.As<TFrom, TTo>(ref Unsafe.AsRef(in from));

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private T ReadInternal<T>() where T : unmanaged
    {
        var size = Unsafe.SizeOf<T>();
        var value = MemoryMarshal.Read<T>(ReadBytes(size));
        return value;
    }

    public T ReadPrimitive<T>() where T : unmanaged
    {
        if (typeof(T) == typeof(sbyte))
            return Cast<byte, T>(ReadByte());

        if (typeof(T) == typeof(short))
            return Cast<short, T>(ReadInt16());

        if (typeof(T) == typeof(int))
            return Cast<int, T>(ReadInt32());

        if (typeof(T) == typeof(long))
            return Cast<long, T>(ReadInt64());

        if (typeof(T) == typeof(byte))
            return Cast<byte, T>(ReadByte());

        if (typeof(T) == typeof(ushort))
            return Cast<ushort, T>(ReadUInt16());

        if (typeof(T) == typeof(uint))
            return Cast<uint, T>(ReadUInt32());

        if (typeof(T) == typeof(ulong))
            return Cast<ulong, T>(ReadUInt64());

        return ReadInternal<T>();
    }

    public ImmutableArray<T> ReadPrimitiveArray<T>(long count) where T : unmanaged
    {
        var array = ImmutableArray.CreateBuilder<T>(checked((int)count));
        for (long i = 0; i < count; i++)
            array.Add(ReadPrimitive<T>());

        return array.MoveToImmutable();
    }

    public T ReadVersionedObject<T>() where T : IReadable, new() => ReadVersionedObject<T>(Version);

    public T ReadVersionedObject<T>(in StructVersion version = default) where T : IReadable, new()
    {
        var obj = new T();
        var a = this;
        obj.Read(ref a, in version);
        return obj;
    }

    public ImmutableArray<T> ReadVersionedObjectArray<T>(long count) where T : IReadable, new() => ReadVersionedObjectArray<T>(count, Version);

    public ImmutableArray<T> ReadVersionedObjectArray<T>(long count, in StructVersion version = default) where T : IReadable, new()
    {
        var array = ImmutableArray.CreateBuilder<T>(checked((int)count));
        for (long i = 0; i < count; i++)
            array.Add(ReadVersionedObject<T>(in version));

        return array.MoveToImmutable();
    }

    public long ReadNInt()
        => Is32Bit ? ReadPrimitive<int>() : ReadPrimitive<long>();

    public ulong ReadNUInt()
        => Is32Bit ? ReadPrimitive<uint>() : ReadPrimitive<ulong>();

    public string ReadString() => ReadNullTerminatedString();

    public new ReadOnlySpan<byte> ReadBytes(int length)
    {
        return base.ReadBytes(length);
    }

    public void Align(int alignment = 0)
    {
        if (alignment == 0)
            alignment = Is32Bit ? 4 : 8;

        var rem = Position % alignment;
        if (rem != 0)
            Position += alignment - rem;
    }

    public TType ReadPrimitive<TType>(long addr) where TType : unmanaged
    {
        Position = addr;
        return ReadPrimitive<TType>();
    }

    public ImmutableArray<TType> ReadPrimitiveArray<TType>(long addr, long count) where TType : unmanaged
    {
        Position = addr;
        return ReadPrimitiveArray<TType>(count);
    }

    public TType ReadVersionedObject<TType>(long addr) where TType : IReadable, new()
    {
        Position = addr;
        return ReadVersionedObject<TType>(Version);
    }

    public ImmutableArray<TType> ReadVersionedObjectArray<TType>(long addr, long count) where TType : IReadable, new()
    {
        Position = addr;
        return ReadVersionedObjectArray<TType>(count, Version);
    }

    public void Skip(int count)
    {
        Position += count;
    }
}