using System.Collections.Generic;

namespace UABEAvalonia.Cli
{
    /// <summary>
    /// CLI 命令动词
    /// </summary>
    public enum CliVerb
    {
        None,
        Export,
        Import,
        Apply,
        List,
        Info,
        Decompress,
        Compress,
        Help,

        // 旧版兼容命令
        LegacyBatchExportBundle,
        LegacyBatchImportBundle,
        LegacyApplyEmip,
    }

    /// <summary>
    /// CLI 命令目标类型
    /// </summary>
    public enum CliTarget
    {
        None,
        Bundle,      // 保留以兼容旧版解析路径 (decompress/compress 仍使用)
        BundleDir,
        Assets,
        AssetsDir,
        Emip,
        File,        // 新: 单文件，自动检测类型
        Dir,         // 新: 目录，自动检测每个文件
    }

    /// <summary>
    /// 导出格式
    /// </summary>
    public enum CliExportFormat
    {
        Raw,
        Dump,
        Json,
        Png,
        Wav,
        Txt,
    }

    /// <summary>
    /// 压缩方式
    /// </summary>
    public enum CliCompressMethod
    {
        None,
        Lz4,
        Lzma,
    }

    /// <summary>
    /// CLI 解析后的选项模型，存储所有参数
    /// </summary>
    public class CliOptions
    {
        // 命令结构
        public CliVerb Verb { get; set; } = CliVerb.None;
        public CliTarget Target { get; set; } = CliTarget.None;

        // 路径参数
        public string FilePath { get; set; } = string.Empty;         // -f, --file (统一文件路径, auto-detect 类型)
        public string BundlePath { get; set; } = string.Empty;       // -b, --bundle (decompress/compress 专用, 同时设置 FilePath)
        public string AssetsPath { get; set; } = string.Empty;       // -a, --assets (兼容旧版, 同时设置 FilePath)
        public string DirectoryPath { get; set; } = string.Empty;    // -d, --directory
        public string OutputDir { get; set; } = string.Empty;        // -o, --output
        public string InputDir { get; set; } = string.Empty;         // -i, --input
        public string EmipPath { get; set; } = string.Empty;         // -e, --emip

        // 过滤参数
        public List<string> FilterTypes { get; set; } = new List<string>();    // -t, --type
        public List<long> FilterPathIds { get; set; } = new List<long>();       // -p, --pathid
        public string FilterName { get; set; } = string.Empty;                  // -n, --name

        // 导出格式
        public CliExportFormat Format { get; set; } = CliExportFormat.Raw;     // --format
        
        // 导入格式 (纹理): 默认 (TextureFormat)(-1) 表示保持原始格式
        public string TextureFormatOverride { get; set; } = string.Empty; // --tex-format (空 = 保持原始)

        // 压缩
        public CliCompressMethod CompressMethod { get; set; } = CliCompressMethod.None; // --compress

        // EMIP 创建参数
        public string ModName { get; set; } = string.Empty;          // --name
        public string ModAuthor { get; set; } = string.Empty;        // --author

        // Flags
        public bool KeepNames { get; set; } = false;     // --keepnames / -keepnames
        public bool KeepDecomp { get; set; } = false;    // --kd / -kd
        public bool ForceDecomp { get; set; } = false;   // --fd / -fd
        public bool MemoryDecomp { get; set; } = false;  // --md / -md
        public bool Backup { get; set; } = false;        // --backup
        public bool NoBackup { get; set; } = false;      // --no-backup
        public bool Recursive { get; set; } = false;     // --recursive
        public bool DryRun { get; set; } = false;        // --dry-run
        public bool Verbose { get; set; } = false;       // -v, --verbose
        public bool Quiet { get; set; } = false;         // -q, --quiet

        // 旧版兼容：位置参数
        public string LegacyPositionalArg { get; set; } = string.Empty;
        public string LegacyPositionalArg2 { get; set; } = string.Empty;

        // 解析错误
        public List<string> Errors { get; set; } = new List<string>();
        public bool HasErrors => Errors.Count > 0;
    }
}
