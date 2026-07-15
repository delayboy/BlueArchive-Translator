namespace Il2CppInspector.Next.Metadata;

using VersionedSerialization.Attributes;
using StringIndex = int;
using TypeIndex = int;

[VersionedStruct]
public partial record struct Il2CppParameterDefinition
{
    public StringIndex NameIndex { get; private set; }
    public uint Token { get; private set; }

    [VersionCondition(LessThan = "24.0")]
    public int CustomAttributeIndex { get; private set; }

    public TypeIndex TypeIndex { get; private set; }

    public readonly bool IsValid => NameIndex != 0;
}