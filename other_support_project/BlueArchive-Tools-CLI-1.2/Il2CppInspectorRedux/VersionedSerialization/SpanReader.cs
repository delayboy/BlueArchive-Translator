using System.Buffers.Binary;
using System.Collections.Immutable;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;

namespace VersionedSerialization;

// ReSharper disable ReplaceSliceWithRangeIndexer | The range indexer gets compiled into .Slice(x, y) and not .Slice(x) which worsens performance
public ref struct SpanReader(ReadOnlySpan<byte> data, int offset = 0, bool littleEndian = true, bool is32Bit = false) : IReader
{
    public int Offset = offset;
    public readonly byte Peek => _data[Offset];
    public readonly bool IsLittleEndian => _littleEndian;
    public readonly bool Is32Bit => _is32Bit;
    public readonly int Length => _data.Length;
    public readonly int PointerSize => Is32Bit ? sizeof(uint) : sizeof(ulong);

    private readonly ReadOnlySpan<byte> _data = data;
    private readonly bool _littleEndian = littleEndian;
    private readonly bool _is32Bit = is32Bit;

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private T ReadInternal<T>() where T : unmanaged
    {
        var value = MemoryMarshal.Read<T>(_data.Slice(Offset));
        Offset += Unsafe.SizeOf<T>();
        return value;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static TTo Cast<TFrom, TTo>(in TFrom from) => Unsafe.As<TFrom, TTo>(ref Unsafe.AsRef(in from));

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public ReadOnlySpan<byte> ReadBytes(int length)
    {
        var val = _data.Slice(Offset, length);
        Offset += length;
        return val;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public T ReadPrimitive<T>() where T : unmanaged
    {
        if (typeof(T) == typeof(byte))
            return Cast<byte, T>(_data[Offset++]);

        var value = ReadInternal<T>();
        if (!_littleEndian)
        {
            if (value is ulong val)
            {
                var converted = BinaryPrimitives.ReverseEndianness(val);
                value = Cast<ulong, T>(converted);
            } 
            else if (typeof(T) == typeof(long))
            {
                var converted = BinaryPrimitives.ReverseEndianness(Cast<T, long>(value));
                value = Cast<long, T>(converted);
            }
            else if (typeof(T) == typeof(uint))
            {
                var converted = BinaryPrimitives.ReverseEndianness(Cast<T, uint>(value));
                value = Cast<uint, T>(converted);
            }
            else if (typeof(T) == typeof(int))
            {
                var converted = BinaryPrimitives.ReverseEndianness(Cast<T, int>(value));
                value = Cast<int, T>(converted);
            }
            else if (typeof(T) == typeof(ushort))
            {
                var converted = BinaryPrimitives.ReverseEndianness(Cast<T, ushort>(value));
                value = Cast<ushort, T>(converted);
            }
            else if (typeof(T) == typeof(short))
            {
                var converted = BinaryPrimitives.ReverseEndianness(Cast<T, short>(value));
                value = Cast<short, T>(converted);
            }
        }

        return value;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public ImmutableArray<T> ReadPrimitiveArray<T>(long count) where T : unmanaged
    {
        var array = ImmutableArray.CreateBuilder<T>(checked((int)count));
        for (long i = 0; i < count; i++)
            array.Add(ReadPrimitive<T>());

        return array.MoveToImmutable();
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public T ReadVersionedObject<T>(in StructVersion version = default) where T : IReadable, new()
    {
        var obj = new T();
        obj.Read(ref this, in version);
        return obj;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public ImmutableArray<T> ReadVersionedObjectArray<T>(long count, in StructVersion version = default) where T : IReadable, new() 
    {
        var array = ImmutableArray.CreateBuilder<T>(checked((int)count));
        for (long i = 0; i < count; i++)
            array.Add(ReadVersionedObject<T>(in version));

        return array.MoveToImmutable();
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public string ReadString()
    {
        var length = _data.Slice(Offset).IndexOf(byte.MinValue);

        if (length == -1)
            throw new InvalidDataException("Failed to find string in span.");

        var val = _data.Slice(Offset, length);
        Offset += length + 1; // Skip null terminator

        return Encoding.UTF8.GetString(val);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public bool ReadBoolean() => ReadPrimitive<byte>() != 0;

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public ulong ReadNUInt() => _is32Bit ? ReadPrimitive<uint>() : ReadPrimitive<ulong>();

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public long ReadNInt() => _is32Bit ? ReadPrimitive<int>() : ReadPrimitive<long>();

    public void Align(int alignment = 0)
    {
        if (alignment == 0)
            alignment = Is32Bit ? 4 : 8;

        var rem = Offset % alignment;
        if (rem != 0)
            Offset += alignment - rem;
    }

    public void Skip(int count)
    {
        Offset += count;
    }
}