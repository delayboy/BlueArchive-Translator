using VersionedSerialization.Attributes;

namespace Il2CppInspector.Next.Metadata;

// Unity 4.6.1p5 - first release, no global-metadata.dat
// Unity 5.2.0f3 -> v15
// Unity 5.3.0f4 -> v16
// Unity 5.3.2f1 -> v19
// Unity 5.3.3f1 -> v20
// Unity 5.3.5f1 -> v21
// Unity 5.5.0f3 -> v22
// Unity 5.6.0f3 -> v23
// Unity 2017.1.0f3 -> v24
// Unity 2018.3.0f2 -> v24.1
// Unity 2019.1.0f2 -> v24.2
// Unity 2019.3.7f1 -> v24.3
// Unity 2019.4.15f1 -> v24.4
// Unity 2019.4.21f1 -> v24.5
// Unity 2020.1.0f1 -> v24.3
// Unity 2020.1.11f1 -> v24.4
// Unity 2020.2.0f1 -> v27
// Unity 2020.2.4f1 -> v27.1
// Unity 2021.1.0f1 -> v27.2
// https://unity3d.com/get-unity/download/archive
// Metadata version is written at the end of Unity.IL2CPP.MetadataCacheWriter.WriteLibIl2CppMetadata or WriteMetadata (Unity.IL2CPP.dll)

[VersionedStruct]
public partial record struct Il2CppGlobalMetadataHeader
{
    public int Sanity { get; private set; }
    public int Version { get; private set; }
    public int StringLiteralOffset { get; private set; }
    public int StringLiteralSize { get; private set; }
    public int StringLiteralDataOffset { get; private set; }
    public int StringLiteralDataSize { get; private set; }
    public int StringOffset { get; private set; }
    public int StringSize { get; private set; }
    public int EventsOffset { get; private set; }
    public int EventsSize { get; private set; }
    public int PropertiesOffset { get; private set; }
    public int PropertiesSize { get; private set; }
    public int MethodsOffset { get; private set; }
    public int MethodsSize { get; private set; }

    [VersionCondition(GreaterThan = "16.0")]
    [VersionCondition(EqualTo = "16.0")]
    public int ParameterDefaultValuesOffset { get; private set; }

    [VersionCondition(GreaterThan = "16.0")]
    [VersionCondition(EqualTo = "16.0")]
    public int ParameterDefaultValuesSize { get; private set; }
    public int FieldDefaultValuesOffset { get; private set; }
    public int FieldDefaultValuesSize { get; private set; }
    public int FieldAndParameterDefaultValueDataOffset { get; private set; }
    public int FieldAndParameterDefaultValueDataSize { get; private set; }

    [VersionCondition(GreaterThan = "16.0")]
    public int FieldMarshaledSizesOffset { get; private set; }

    [VersionCondition(GreaterThan = "16.0")]
    public int FieldMarshaledSizesSize { get; private set; }
    public int ParametersOffset { get; private set; }
    public int ParametersSize { get; private set; }
    public int FieldsOffset { get; private set; }
    public int FieldsSize { get; private set; }
    public int GenericParametersOffset { get; private set; }
    public int GenericParametersSize { get; private set; }
    public int GenericParameterConstraintsOffset { get; private set; }
    public int GenericParameterConstraintsSize { get; private set; }
    public int GenericContainersOffset { get; private set; }
    public int GenericContainersSize { get; private set; }
    public int NestedTypesOffset { get; private set; }
    public int NestedTypesSize { get; private set; }
    public int InterfacesOffset { get; private set; }
    public int InterfacesSize { get; private set; }
    public int VTableMethodsOffset { get; private set; }
    public int VTableMethodsSize { get; private set; }
    public int InterfaceOffsetsOffset { get; private set; }
    public int InterfaceOffsetsSize { get; private set; }
    public int TypeDefinitionsOffset { get; private set; }
    public int TypeDefinitionsSize { get; private set; }

    [VersionCondition(LessThan = "24.1")]
    public int RgctxEntriesOffset { get; private set; }

    [VersionCondition(LessThan = "24.1")] 
    public int RgctxEntriesCount { get; private set; }

    [VersionCondition(GreaterThan = "16.0")]
    public int ImagesOffset { get; private set; }

    [VersionCondition(GreaterThan = "16.0")]
    public int ImagesSize { get; private set; }

    [VersionCondition(GreaterThan = "16.0")]
    public int AssembliesOffset { get; private set; }

    [VersionCondition(GreaterThan = "16.0")]
    public int AssembliesSize { get; private set; }

    [VersionCondition(GreaterThan = "19.0", LessThan = "24.5")]
    public int MetadataUsageListsOffset { get; private set; }

    [VersionCondition(GreaterThan = "19.0", LessThan = "24.5")]
    public int MetadataUsageListsCount { get; private set; }

    [VersionCondition(GreaterThan = "19.0", LessThan = "24.5")]
    public int MetadataUsagePairsOffset { get; private set; }

    [VersionCondition(GreaterThan = "19.0", LessThan = "24.5")]
    public int MetadataUsagePairsCount { get; private set; }

    [VersionCondition(GreaterThan = "19.0")]
    public int FieldRefsOffset { get; private set; }

    [VersionCondition(GreaterThan = "19.0")]
    public int FieldRefsSize { get; private set; }

    [VersionCondition(GreaterThan = "20.0")]
    public int ReferencedAssembliesOffset { get; private set; }

    [VersionCondition(GreaterThan = "20.0")]
    public int ReferencedAssembliesSize { get; private set; }

    [VersionCondition(GreaterThan = "21.0", LessThan = "27.2")]
    public int AttributesInfoOffset { get; private set; }

    [VersionCondition(GreaterThan = "21.0", LessThan = "27.2")]
    public int AttributesInfoCount { get; private set; }

    [VersionCondition(GreaterThan = "21.0", LessThan = "27.2")]
    public int AttributesTypesOffset { get; private set; }

    [VersionCondition(GreaterThan = "21.0", LessThan = "27.2")]
    public int AttributesTypesCount { get; private set; }

    [VersionCondition(GreaterThan = "29.0")]
    public int AttributeDataOffset { get; private set; }

    [VersionCondition(GreaterThan = "29.0")]
    public int AttributeDataSize { get; private set; }

    [VersionCondition(GreaterThan = "29.0")]
    public int AttributeDataRangeOffset { get; private set; }

    [VersionCondition(GreaterThan = "29.0")]
    public int AttributeDataRangeSize { get; private set; }

    [VersionCondition(GreaterThan = "22.0")]
    public int UnresolvedIndirectCallParameterTypesOffset { get; private set; }

    [VersionCondition(GreaterThan = "22.0")]
    public int UnresolvedIndirectCallParameterTypesSize { get; private set; }

    [VersionCondition(GreaterThan = "22.0")]
    public int UnresolvedIndirectCallParameterRangesOffset { get; private set; }

    [VersionCondition(GreaterThan = "22.0")]
    public int UnresolvedIndirectCallParameterRangesSize { get; private set; }

    [VersionCondition(GreaterThan = "23.0")]
    public int WindowsRuntimeTypeNamesOffset { get; private set; }

    [VersionCondition(GreaterThan = "23.0")]
    public int WindowsRuntimeTypeNamesSize { get; private set; }

    [VersionCondition(GreaterThan = "27.0")]
    public int WindowsRuntimeStringsOffset { get; private set; }

    [VersionCondition(GreaterThan = "27.0")]
    public int WindowsRuntimeStringsSize { get; private set; }

    [VersionCondition(GreaterThan = "24.0")]
    public int ExportedTypeDefinitionsOffset { get; private set; }

    [VersionCondition(GreaterThan = "24.0")]
    public int ExportedTypeDefinitionsSize { get; private set; }


    public const int ExpectedSanity = unchecked((int)0xFAB11BAF);
    public readonly bool SanityValid => Sanity == ExpectedSanity;
}