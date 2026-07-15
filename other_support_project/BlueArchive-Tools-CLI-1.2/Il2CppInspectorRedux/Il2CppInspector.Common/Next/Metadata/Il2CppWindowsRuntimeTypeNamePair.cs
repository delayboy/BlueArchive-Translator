namespace Il2CppInspector.Next.Metadata;

using VersionedSerialization.Attributes;
using StringIndex = int;
using TypeIndex = int;

[VersionedStruct]
public partial record struct Il2CppWindowsRuntimeTypeNamePair
{
    public StringIndex NameIndex { get; private set; }
    public TypeIndex TypeIndex { get; private set; }
}