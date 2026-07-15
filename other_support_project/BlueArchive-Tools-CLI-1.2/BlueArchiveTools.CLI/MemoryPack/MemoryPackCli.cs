using System;
using System.IO;
using System.Text.Json;
using System.Text.Encodings.Web;
using MemoryPack;

namespace BlueArchiveTools.CLI.MemoryPack;

public enum CommandMode { Deserialize, Serialize }

public class MemoryPackCli
{
    private readonly AppJsonContext _jsonContext;

    public MemoryPackCli()
    {
        RegisterFormatters();
        var options = new JsonSerializerOptions
        {
            WriteIndented = true,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
        };
        _jsonContext = new AppJsonContext(options);
    }

    public void Execute(string[] args)
    {
        string modeStr = args[1].ToLower(); // 加解密
        string server = args[2].ToLower(); // 服务器
        string type = args[3].ToLower(); // catalog类型
        string inputPath = args[4]; // 输入路径
        string outputPath = args[5]; // 输出路径

        if (modeStr == "serialize") 
            Run(CommandMode.Serialize, server, type, inputPath, outputPath);
        else if (modeStr == "deserialize") 
            Run(CommandMode.Deserialize, server, type, inputPath, outputPath);
    }

    private void Run(CommandMode mode, string server, string type, string input, string output)
    {
        try
        {
            if (mode == CommandMode.Deserialize)
                ProcessDeserialization(server, type, input, output);
            else
                ProcessSerialization(server, type, input, output);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[Error] {ex.GetType().Name}: {ex.Message}");
        }
    }

    private void ProcessDeserialization(string server, string type, string input, string output)
    {
        byte[] data = File.ReadAllBytes(input);
        string json = string.Empty;

        if (server == "jp")
        {
            json = type switch
            {
                "table" => JsonSerializer.Serialize(MemoryPackSerializer.Deserialize<TableCatalog>(data), _jsonContext.TableCatalog),
                "media" => SerializeMediaJP(data),
                "bundle" => JsonSerializer.Serialize(MemoryPackSerializer.Deserialize<BundlePatchPackInfo>(data), _jsonContext.BundlePatchPackInfo),
                _ => string.Empty
            };
        }
        else if (server == "gl")
        {
            json = type switch
            {
                "table" => JsonSerializer.Serialize(MemoryPackSerializer.Deserialize<TableCatalogGL>(data), _jsonContext.TableCatalogGL),
                "media" => SerializeMediaGL(data),
                _ => string.Empty
            };
        }

        if (!string.IsNullOrEmpty(json)) File.WriteAllText(output, json);
    }

    private void ProcessSerialization(string server, string type, string input, string output)
    {
        string json = File.ReadAllText(input);
        byte[]? bin = null;

        if (server == "jp")
        {
            bin = type switch
            {
                "table" => MemoryPackSerializer.Serialize(JsonSerializer.Deserialize(json, _jsonContext.TableCatalog)),
                "media" => DeserializeMediaJP(json),
                "bundle" => MemoryPackSerializer.Serialize(JsonSerializer.Deserialize(json, _jsonContext.BundlePatchPackInfo)),
                _ => null
            };
        }
        else if (server == "gl")
        {
            bin = type switch
            {
                "table" => MemoryPackSerializer.Serialize(JsonSerializer.Deserialize(json, _jsonContext.TableCatalogGL)),
                "media" => DeserializeMediaGL(json),
                _ => null
            };
        }

        if (bin != null) File.WriteAllBytes(output, bin);
    }

    private string SerializeMediaJP(byte[] data)
    {
        var obj = MemoryPackSerializer.Deserialize<MediaCatalog>(data);
        if (obj != null) foreach (var m in obj.Table.Values) m.Path = m.Path.Replace("\\", "/");
        return JsonSerializer.Serialize(obj, _jsonContext.MediaCatalog);
    }

    private string SerializeMediaGL(byte[] data)
    {
        var obj = MemoryPackSerializer.Deserialize<MediaCatalogGL>(data);
        if (obj != null)
        {
            foreach (var m in obj.Table.Values) m.Path = m.Path.Replace("\\", "/");
            foreach (var m in obj.Catalog.Values) m.Path = m.Path.Replace("\\", "/");
        }
        return JsonSerializer.Serialize(obj, _jsonContext.MediaCatalogGL);
    }

    private byte[] DeserializeMediaJP(string json)
    {
        var obj = JsonSerializer.Deserialize(json, _jsonContext.MediaCatalog);
        if (obj != null) foreach (var m in obj.Table.Values) m.Path = m.Path.Replace("/", "\\");
        return MemoryPackSerializer.Serialize(obj);
    }

    private byte[] DeserializeMediaGL(string json)
    {
        var obj = JsonSerializer.Deserialize(json, _jsonContext.MediaCatalogGL);
        if (obj != null)
        {
            foreach (var m in obj.Table.Values) m.Path = m.Path.Replace("/", "\\");
            foreach (var m in obj.Catalog.Values) m.Path = m.Path.Replace("/", "\\");
        }
        return MemoryPackSerializer.Serialize(obj);
    }

    private void RegisterFormatters()
    {
        MemoryPackFormatterProvider.Register<TableBundle>();
        MemoryPackFormatterProvider.Register<TablePatchPack>();
        MemoryPackFormatterProvider.Register<TableCatalog>();
        MemoryPackFormatterProvider.Register<TableBundleGL>();
        MemoryPackFormatterProvider.Register<TableCatalogGL>();
        MemoryPackFormatterProvider.Register<Media>();
        MemoryPackFormatterProvider.Register<MediaCatalog>();
        MemoryPackFormatterProvider.Register<MediaGL>();
        MemoryPackFormatterProvider.Register<MediaCatalogGL>();
        MemoryPackFormatterProvider.Register<BundleFile>();
        MemoryPackFormatterProvider.Register<BundlePatchPack>();
        MemoryPackFormatterProvider.Register<BundlePatchPackInfo>();
    }
}
