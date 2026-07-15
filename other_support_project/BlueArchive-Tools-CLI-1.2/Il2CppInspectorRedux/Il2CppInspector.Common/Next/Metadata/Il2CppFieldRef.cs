using VersionedSerialization.Attributes;

namespace Il2CppInspector.Next.Metadata;

using FieldIndex = int;
using TypeIndex = int;

[VersionedStruct]
public partial record struct Il2CppFieldRef
{
    public TypeIndex TypeIndex { get; private set; }
    public FieldIndex FieldIndex { get; private set; }
}