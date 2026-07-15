namespace Il2CppInspector.Next.Metadata;

using ParameterIndex = int;
using TypeIndex = int;
using DefaultValueDataIndex = int;
using VersionedSerialization.Attributes;

[VersionedStruct]
public partial record struct Il2CppParameterDefaultValue
{
    public ParameterIndex ParameterIndex { get; private set; }
    public TypeIndex TypeIndex { get; private set; }
    public DefaultValueDataIndex DataIndex { get; private set; }
}