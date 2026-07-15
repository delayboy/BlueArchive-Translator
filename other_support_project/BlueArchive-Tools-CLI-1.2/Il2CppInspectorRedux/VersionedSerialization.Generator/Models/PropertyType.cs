using System;

namespace VersionedSerialization.Generator.Models;

public enum PropertyType
{
    Unsupported = -1,
    None,
    Boolean,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
    Int8,
    Int16,
    Int32,
    Int64,
    String,
    Custom,
    NativeInteger,
    UNativeInteger,
}

public static class PropertyTypeExtensions
{
    public static string GetTypeName(this PropertyType type)
        => type switch
        {
            PropertyType.Unsupported => nameof(PropertyType.Unsupported),
            PropertyType.None => nameof(PropertyType.None),
            PropertyType.UInt8 => nameof(Byte),
            PropertyType.Int8 => nameof(SByte),
            PropertyType.Boolean => nameof(PropertyType.Boolean),
            PropertyType.UInt16 => nameof(PropertyType.UInt16),
            PropertyType.UInt32 => nameof(PropertyType.UInt32),
            PropertyType.UInt64 => nameof(PropertyType.UInt64),
            PropertyType.Int16 => nameof(PropertyType.Int16),
            PropertyType.Int32 => nameof(PropertyType.Int32),
            PropertyType.Int64 => nameof(PropertyType.Int64),
            PropertyType.String => nameof(String),
            PropertyType.Custom => "",
            PropertyType.NativeInteger => "NInt",
            PropertyType.UNativeInteger => "NUInt",
            _ => throw new ArgumentOutOfRangeException(nameof(type), type, null)
        };

    public static bool IsSeperateMethod(this PropertyType type)
        => type switch
        {
            PropertyType.Boolean => true,
            PropertyType.String => true,
            PropertyType.Custom => true,
            PropertyType.NativeInteger => true,
            PropertyType.UNativeInteger => true,
            _ => false
        };

    public static int GetTypeSize(this PropertyType type)
        => type switch
        {
            PropertyType.Unsupported => -1,
            PropertyType.None => 0,
            PropertyType.UInt8 => 1,
            PropertyType.Int8 => 1,
            PropertyType.Boolean => 1,
            PropertyType.UInt16 => 2,
            PropertyType.UInt32 => 4,
            PropertyType.UInt64 => 8,
            PropertyType.Int16 => 2,
            PropertyType.Int32 => 4,
            PropertyType.Int64 => 8,
            PropertyType.String => -1,
            PropertyType.Custom => -1,
            PropertyType.NativeInteger => -1,
            PropertyType.UNativeInteger => -1,
            _ => throw new ArgumentOutOfRangeException(nameof(type), type, null)
        };

    public static bool IsUnsignedType(this PropertyType type)
        => type switch
        {
            PropertyType.UInt8
                or PropertyType.UInt16
                or PropertyType.UInt32
                or PropertyType.UInt64 => true,
            _ => false
        };
}