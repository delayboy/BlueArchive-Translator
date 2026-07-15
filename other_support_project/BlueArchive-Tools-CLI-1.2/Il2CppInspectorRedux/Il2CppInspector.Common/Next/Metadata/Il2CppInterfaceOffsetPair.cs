using VersionedSerialization.Attributes;

namespace Il2CppInspector.Next.Metadata;

using TypeIndex = int;

[VersionedStruct]
public partial record struct Il2CppInterfaceOffsetPair
{
    public TypeIndex InterfaceTypeIndex { get; private set; }
    public int Offset { get; private set; }
}