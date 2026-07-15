using VersionedSerialization.Attributes;

namespace Il2CppInspector.Next.BinaryMetadata;

[VersionedStruct]
public partial record struct Il2CppGenericClass
{
    [NativeInteger]
    [VersionCondition(LessThan = "24.5")]
    public int TypeDefinitionIndex;

    [VersionCondition(GreaterThan = "27.0")]
    public Pointer<Il2CppType> Type;

    public Il2CppGenericContext Context;

    public PrimitivePointer<byte> CachedClass; // Il2CppClass*, optional
}