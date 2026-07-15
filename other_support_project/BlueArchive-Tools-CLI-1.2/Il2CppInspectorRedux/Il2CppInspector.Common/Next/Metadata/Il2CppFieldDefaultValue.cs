using VersionedSerialization.Attributes;

namespace Il2CppInspector.Next.Metadata;

using FieldIndex = int;
using TypeIndex = int;
using DefaultValueDataIndex = int;

[VersionedStruct]
public partial record struct Il2CppFieldDefaultValue
{
    public FieldIndex FieldIndex { get; private set; }
    public TypeIndex TypeIndex { get; private set; }
    public DefaultValueDataIndex DataIndex { get; private set; }
}