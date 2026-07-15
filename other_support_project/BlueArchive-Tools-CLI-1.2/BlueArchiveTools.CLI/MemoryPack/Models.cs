using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;
using MemoryPack;

namespace BlueArchiveTools.CLI.MemoryPack;

public enum MediaType
{
    None,
    Audio,
    Video,
    Texture
}

public enum StorageType
{
    None,
    InBuild,
    Preload,
    GameData
}

[MemoryPackable]
public partial class TableBundle
{
    public string Name { get; set; } = string.Empty;
    public long Size { get; set; }
    public long Crc { get; set; }
    public bool isInbuild { get; set; }
    public bool isChanged { get; set; }
    public bool IsPrologue { get; set; }
    public bool IsSplitDownload { get; set; }
    public string[] Includes { get; set; } = Array.Empty<string>();
}

[MemoryPackable]
public partial class TablePatchPack
{
    public string Name { get; set; } = string.Empty;
    public long Size { get; set; }
    public long Crc { get; set; }
    public bool IsPrologue { get; set; }
    public TableBundle[] BundleFiles { get; set; } = Array.Empty<TableBundle>();
}

[MemoryPackable]
public partial class TableCatalog
{
    public Dictionary<string, TableBundle> Table { get; set; } = new();
    public Dictionary<string, TablePatchPack> TablePack { get; set; } = new();
}

[MemoryPackable]
public partial class TableBundleGL
{
    public string Name { get; set; } = string.Empty;
    public long Crc { get; set; }
    public bool IsPrologue { get; set; }
    public List<string> Includes { get; set; } = new();
}

[MemoryPackable]
public partial class TableCatalogGL
{
    public Dictionary<string, TableBundleGL> Table { get; set; } = new();
    public Dictionary<string, TableBundleGL> Catalog { get; set; } = new();
}

[MemoryPackable]
public partial class Media
{
    [JsonPropertyName("path")]
    public string Path { get; set; } = string.Empty;
    public string FileName { get; set; } = string.Empty;
    public long Bytes { get; set; }
    public long Crc { get; set; }
    public bool IsPrologue { get; set; }
    public bool IsSplitDownload { get; set; }
    public MediaType MediaType { get; set; }
}

[MemoryPackable]
public partial class MediaCatalog
{
    public Dictionary<string, Media> Table { get; set; } = new();
}

[MemoryPackable]
public partial class MediaGL
{
    [JsonPropertyName("path")]
    public string Path { get; set; } = string.Empty;
    public StorageType StorageType { get; set; }
    public MediaType MediaType { get; set; }
}

[MemoryPackable]
public partial class MediaCatalogGL
{
    public Dictionary<string, MediaGL> Table { get; set; } = new();
    public Dictionary<string, MediaGL> Catalog { get; set; } = new();
}

[MemoryPackable]
public partial class BundleFile
{
    public string Name { get; set; } = string.Empty;
    public long Size { get; set; }
    public bool IsPrologue { get; set; }
    public long Crc { get; set; }
    public bool IsSplitDownload { get; set; }
    public ulong FileHash { get; set; }
    public string Signature { get; set; } = string.Empty;
}

[MemoryPackable]
public partial class BundlePatchPack
{
    public string PackName { get; set; } = string.Empty;
    public long PackSize { get; set; }
    public long Crc { get; set; }
    public bool IsPrologue { get; set; }
    public bool IsSplitDownload { get; set; }
    public BundleFile[] BundleFiles { get; set; } = Array.Empty<BundleFile>();
}

[MemoryPackable]
public partial class BundlePatchPackInfo
{
    public string Milestone { get; set; } = string.Empty;
    public int PatchVersion { get; set; }
    public BundlePatchPack[] FullPatchPacks { get; set; } = Array.Empty<BundlePatchPack>();
    public BundlePatchPack[] UpdatePacks { get; set; } = Array.Empty<BundlePatchPack>();
}

[JsonSerializable(typeof(TableCatalog))]
[JsonSerializable(typeof(MediaCatalog))]
[JsonSerializable(typeof(BundlePatchPackInfo))]
[JsonSerializable(typeof(TableCatalogGL))]
[JsonSerializable(typeof(MediaCatalogGL))]
internal partial class AppJsonContext : JsonSerializerContext { }
