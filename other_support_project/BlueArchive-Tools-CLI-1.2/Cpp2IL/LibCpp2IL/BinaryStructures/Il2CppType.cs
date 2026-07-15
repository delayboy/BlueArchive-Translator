using System;
using System.Diagnostics;
using LibCpp2IL.Metadata;
using LibCpp2IL.Reflection;

namespace LibCpp2IL.BinaryStructures;

public class Il2CppType : ReadableClass
{
    // Populated by Il2CppBinary.Init for per-context usage.
    internal Il2CppBinary? OwningBinary { get; set; }
    internal Il2CppMetadata? OwningMetadata { get; set; }
    internal bool? Il2CppTypeHasNumMods5Bits { get; set; }

    public ulong Datapoint;
    public uint Bits;
    public Union Data { get; set; } = null!; //Late-bound
    public uint Attrs { get; set; }
    public Il2CppTypeEnum Type { get; set; }
    public uint NumMods { get; set; }
    public uint Byref { get; set; }
    public uint Pinned { get; set; }
    public uint ValueType { get; set; }

    private void InitUnionAndFlags()
    {
        Attrs = Bits & 0b1111_1111_1111_1111; //Lowest 16 bits
        Type = (Il2CppTypeEnum)((Bits >> 16) & 0b1111_1111); //Bits 16-23
        Data = new Union { Dummy = Datapoint };

        var hasNumMods5Bits = Il2CppTypeHasNumMods5Bits ?? LibCpp2IlMain.Il2CppTypeHasNumMods5Bits;
        if (hasNumMods5Bits)
        {
            //Unity 2021 (v27.2) changed num_mods to be 5 bits not 6
            //Which shifts byref and pinned left one
            //And adds a new bit 31 which is valuetype
            NumMods = (Bits >> 24) & 0b1_1111;
            Byref = (Bits >> 29) & 1;
            Pinned = (Bits >> 30) & 1;
            ValueType = Bits >> 31;
        }
        else
        {
            NumMods = (Bits >> 24) & 0b11_1111;
            Byref = (Bits >> 30) & 1;
            Pinned = Bits >> 31;
            ValueType = 0;
        }
    }

    public class Union
    {
        public ulong Dummy;
        
        //DynamicWidth: Dummy is always nint, not dynamic, so temp usage is ok
        public Il2CppVariableWidthIndex<Il2CppTypeDefinition> ClassIndex => Il2CppVariableWidthIndex<Il2CppTypeDefinition>.MakeTemporaryForFixedWidthUsage((int) Dummy);
        public ulong Type => Dummy;
        public ulong Array => Dummy;
        //DynamicWidth: Dummy is always nint, not dynamic, so temp usage is ok
        public Il2CppVariableWidthIndex<Il2CppGenericParameter> GenericParameterIndex => Il2CppVariableWidthIndex<Il2CppGenericParameter>.MakeTemporaryForFixedWidthUsage((int) Dummy);
        public ulong GenericClass => Dummy;
    }

    private Il2CppTypeDefinition? Class
    {
        get
        {
            if (Type is not Il2CppTypeEnum.IL2CPP_TYPE_CLASS and not Il2CppTypeEnum.IL2CPP_TYPE_VALUETYPE)
                return null;

            var metadata = OwningMetadata ?? LibCpp2IlMain.TheMetadata;
            return metadata!.GetTypeDefinitionFromIndex(Data.ClassIndex);
        }
    }

    public Il2CppTypeDefinition AsClass()
    {
        return Class ?? throw new Exception("Type is not a class, but a " + Type);
    }

    private Il2CppType? EncapsulatedType
    {
        get
        {
            if (Type is not Il2CppTypeEnum.IL2CPP_TYPE_PTR and not Il2CppTypeEnum.IL2CPP_TYPE_SZARRAY)
                return null;

            var binary = OwningBinary ?? LibCpp2IlMain.Binary;
            return binary!.GetIl2CppTypeFromPointer(Data.Type);
        }
    }

    public Il2CppType GetEncapsulatedType()
    {
        return EncapsulatedType ?? throw new Exception("Type does not have a encapsulated type - it is not a pointer or an szarray");
    }

    private Il2CppArrayType? ArrayType
    {
        get
        {
            if (Type is not Il2CppTypeEnum.IL2CPP_TYPE_ARRAY)
                return null;

            var binary = OwningBinary ?? LibCpp2IlMain.Binary;
            var at = binary!.ReadReadableAtVirtualAddress<Il2CppArrayType>(Data.Array);
            at.OwningBinary = binary;
            return at;
        }
    }

    public Il2CppArrayType GetArrayType()
    {
        return ArrayType ?? throw new Exception("Type is not an array");
    }

    public Il2CppType GetArrayElementType() => GetArrayType().GetElementTypeOrThrow();

    public int GetArrayRank() => GetArrayType().rank;

    private Il2CppGenericParameter? GenericParameter
    {
        get
        {
            if (Type is not Il2CppTypeEnum.IL2CPP_TYPE_VAR and not Il2CppTypeEnum.IL2CPP_TYPE_MVAR)
                return null;

            var metadata = OwningMetadata ?? LibCpp2IlMain.TheMetadata;
            return metadata!.GetGenericParameterFromIndex(Data.GenericParameterIndex);
        }
    }

    public Il2CppGenericParameter GetGenericParameterDef()
    {
        var result = GenericParameter ?? throw new Exception("Type is not a generic parameter");
        Debug.Assert(result.Type == Type);
        return result;
    }

    private Il2CppGenericClass? GenericClass
    {
        get
        {
            if (Type is not Il2CppTypeEnum.IL2CPP_TYPE_GENERICINST)
                return null;

            var binary = OwningBinary ?? LibCpp2IlMain.Binary;
            var gc = binary!.ReadReadableAtVirtualAddress<Il2CppGenericClass>(Data.GenericClass);
            gc.OwningBinary = binary;
            gc.OwningMetadata = OwningMetadata ?? LibCpp2IlMain.TheMetadata;
            gc.Context.OwningBinary = binary;
            return gc;
        }
    }

    public Il2CppGenericClass GetGenericClass()
    {
        return GenericClass ?? throw new Exception("Type is not a generic class");
    }

    public override void Read(ClassReadingBinaryReader reader)
    {
        Datapoint = reader.ReadNUint();
        Bits = reader.ReadUInt32();

        InitUnionAndFlags();
    }

    public Il2CppTypeDefinition CoerceToUnderlyingTypeDefinition()
    {
        if (Type is Il2CppTypeEnum.IL2CPP_TYPE_VAR or Il2CppTypeEnum.IL2CPP_TYPE_MVAR)
            throw new("Can't get the type definition of a generic parameter");

        return Type switch
        {
            Il2CppTypeEnum.IL2CPP_TYPE_GENERICINST => GetGenericClass().TypeDefinition,
            Il2CppTypeEnum.IL2CPP_TYPE_PTR or Il2CppTypeEnum.IL2CPP_TYPE_SZARRAY => GetEncapsulatedType().CoerceToUnderlyingTypeDefinition(),
            Il2CppTypeEnum.IL2CPP_TYPE_ARRAY => GetArrayElementType().CoerceToUnderlyingTypeDefinition(),
            _ => Type.IsIl2CppPrimitive() ? LibCpp2IlReflection.PrimitiveTypeDefinitions[Type] : AsClass()
        };
    }

    public bool ThisOrElementIsGenericParam()
    {
        return Type switch
        {
            Il2CppTypeEnum.IL2CPP_TYPE_PTR or Il2CppTypeEnum.IL2CPP_TYPE_SZARRAY => GetEncapsulatedType().ThisOrElementIsGenericParam(),
            Il2CppTypeEnum.IL2CPP_TYPE_ARRAY => GetArrayElementType().ThisOrElementIsGenericParam(),
            Il2CppTypeEnum.IL2CPP_TYPE_MVAR or Il2CppTypeEnum.IL2CPP_TYPE_VAR => true,
            _ => false
        };
    }

    public string GetGenericParamName()
    {
        if (!ThisOrElementIsGenericParam())
            throw new("Type is not a generic parameter");

        return Type switch
        {
            Il2CppTypeEnum.IL2CPP_TYPE_PTR => $"{GetEncapsulatedType().GetGenericParamName()}&",
            Il2CppTypeEnum.IL2CPP_TYPE_SZARRAY => $"{GetEncapsulatedType().GetGenericParamName()}[]",
            Il2CppTypeEnum.IL2CPP_TYPE_ARRAY => $"{GetArrayElementType().GetGenericParamName()}{"[]".Repeat(GetArrayRank())}",
            _ => $"{GetGenericParameterDef().Name}",
        };
    }
}
