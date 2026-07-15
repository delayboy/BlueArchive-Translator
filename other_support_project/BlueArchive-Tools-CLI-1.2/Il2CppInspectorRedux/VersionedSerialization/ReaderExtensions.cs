using System.Runtime.CompilerServices;

namespace VersionedSerialization;

public static class ReaderExtensions
{
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static uint ReadCompressedUInt<T>(this ref T reader) where T : struct, IReader, allows ref struct
    {
        var first = reader.ReadPrimitive<byte>();

        if ((first & 0b10000000) == 0b00000000)
            return first;

        if ((first & 0b11000000) == 0b10000000)
            return (uint)(((first & ~0b10000000) << 8) | reader.ReadPrimitive<byte>());

        if ((first & 0b11100000) == 0b11000000)
            return (uint)(((first & ~0b11000000) << 24) | (reader.ReadPrimitive<byte>() << 16) | (reader.ReadPrimitive<byte>() << 8) | reader.ReadPrimitive<byte>());

        return first switch
        {
            0b11110000 => reader.ReadPrimitive<uint>(),
            0b11111110 => uint.MaxValue - 1,
            0b11111111 => uint.MaxValue,
            _ => throw new InvalidDataException("Invalid compressed uint")
        };
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static int ReadCompressedInt<T>(this ref T reader) where T : struct, IReader, allows ref struct
    {
        var value = reader.ReadCompressedUInt();
        if (value == uint.MaxValue)
            return int.MinValue;

        var isNegative = (value & 0b1) == 1;
        value >>= 1;

        return (int)(isNegative ? -(value + 1) : value);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static ulong ReadSLEB128<T>(this ref T reader) where T : struct, IReader, allows ref struct
    {
        var value = 0uL;
        var shift = 0;
        byte current;

        do
        {
            current = reader.ReadPrimitive<byte>();
            value |= (current & 0x7FuL) << shift;
            shift += 7;
        } while ((current & 0x80) != 0);

        if (64 >= shift && (current & 0x40) != 0)
            value |= ulong.MaxValue << shift;

        return value;
    }
}