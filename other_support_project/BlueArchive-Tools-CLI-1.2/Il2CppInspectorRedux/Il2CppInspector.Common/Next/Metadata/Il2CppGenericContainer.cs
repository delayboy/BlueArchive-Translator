namespace Il2CppInspector.Next.Metadata;

using VersionedSerialization.Attributes;
using GenericParameterIndex = int;

[VersionedStruct]
public partial record struct Il2CppGenericContainer
{
    public int OwnerIndex { get; private set; }
    public int TypeArgc { get; private set; }
    public int IsMethod { get; private set; }
    public GenericParameterIndex GenericParameterStart { get; private set; }
}