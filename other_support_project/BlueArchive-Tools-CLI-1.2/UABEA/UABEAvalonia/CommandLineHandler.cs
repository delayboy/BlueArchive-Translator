using AssetsTools.NET;
using AssetsTools.NET.Extra;
using AssetsTools.NET.Texture;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Processing;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UABEAvalonia.Cli;
using UABEAvalonia.Plugins;

namespace UABEAvalonia
{
    public class CommandLineHandler
    {
        private static PluginManager? pluginManager;
        private static AssetsManager? assetsManager;

        #region Help

        public static void PrintHelp()
        {
            Console.WriteLine("UABE Avalonia - CLI");
            Console.WriteLine();
            Console.WriteLine("Usage: UABEAvalonia <command> [options] [flags]");
            Console.WriteLine();
            Console.WriteLine("Commands:");
            Console.WriteLine("  export    Export assets from a file or directory (auto-detects bundle/assets)");
            Console.WriteLine("  import    Import assets into a file or directory (auto-detects bundle/assets)");
            Console.WriteLine("  list      List assets in a file or directory");
            Console.WriteLine("  info      Show file metadata summary");
            Console.WriteLine("  apply     Apply a mod package (e.g. apply emip)");
            Console.WriteLine("  decompress  Decompress a bundle file");
            Console.WriteLine("  compress    Compress a bundle file");
            Console.WriteLine();
            Console.WriteLine("Path options:");
            Console.WriteLine("  -f, --file <path>       File path (auto-detect bundle/assets)");
            Console.WriteLine("  -b, --bundle <path>     Bundle file path (alias for -f; required for compress/decompress)");
            Console.WriteLine("  -a, --assets <path>     Assets file path (alias for -f)");
            Console.WriteLine("  -d, --directory <path>  Directory for batch processing");
            Console.WriteLine("  -o, --output <path>     Output directory/file path");
            Console.WriteLine("  -i, --input <path>      Input directory (for import)");
            Console.WriteLine("  -e, --emip <path>       EMIP file path");
            Console.WriteLine();
            Console.WriteLine("Filter options:");
            Console.WriteLine("  -t, --type <types>      Filter by type (comma-separated, e.g. Texture2D,Font)");
            Console.WriteLine("  -p, --pathid <ids>      Filter by PathID (comma-separated)");
            Console.WriteLine("  -n, --name <pattern>    Filter by name. Supports multiple modes:");
            Console.WriteLine("                            hero        substring match (default)");
            Console.WriteLine("                            =hero_icon  exact match");
            Console.WriteLine("                            ~hero_\\d+  regex match");
            Console.WriteLine("                            hero*       wildcard (* and ?)");
            Console.WriteLine("                            !villain    negation (exclude)");
            Console.WriteLine("                            a,b,c       OR: match any pattern");
            Console.WriteLine("                            !=bg_dark   combine: negate + exact");
            Console.WriteLine();
            Console.WriteLine("Format & compression:");
            Console.WriteLine("  --format <fmt>          Export format: raw, dump, json, png, wav, txt");
            Console.WriteLine("  --method <method>       Compress method: lz4, lzma, none");
            Console.WriteLine("  --tex-format <fmt>      Override texture format for PNG import (default: keep original)");
            Console.WriteLine("                          e.g. RGBA32, DXT1, DXT5, ETC2_RGBA8, ASTC_RGBA_4x4, BC7...");
            Console.WriteLine();
            Console.WriteLine("Flags:");
            Console.WriteLine("  --keepnames             Export using original asset name only (no PathID suffix)");
            Console.WriteLine("  --kd                    Keep .decomp files after processing");
            Console.WriteLine("  --fd                    Force re-decompress (ignore existing .decomp)");
            Console.WriteLine("  --md                    Decompress to memory (no .decomp file)");
            Console.WriteLine("  --backup                Backup original file before import");
            Console.WriteLine("  --no-backup             Skip backup");
            Console.WriteLine("  --recursive             Process subdirectories recursively");
            Console.WriteLine("  --dry-run               Preview mode, no actual changes");
            Console.WriteLine("  -v, --verbose           Verbose output");
            Console.WriteLine("  -q, --quiet             Quiet mode");
            Console.WriteLine();
            Console.WriteLine("Legacy commands (backward compatible):");
            Console.WriteLine("  batchexportbundle <directory>");
            Console.WriteLine("  batchimportbundle <directory>");
            Console.WriteLine("  applyemip <emip_file> <directory>");
            Console.WriteLine();
            Console.WriteLine("Examples:");
            Console.WriteLine("  UABEAvalonia export -f game.bundle -o ./out/ -t Texture2D --format png");
            Console.WriteLine("  UABEAvalonia export -d ./GameData/ -o ./out/ --recursive");
            Console.WriteLine("  UABEAvalonia import -f game.bundle -i ./modified/ --backup");
            Console.WriteLine("  UABEAvalonia import -f game.bundle -i ./modified/ --tex-format RGBA32");
            Console.WriteLine("  UABEAvalonia list -f game.bundle -n hero -t Texture2D");
            Console.WriteLine("  UABEAvalonia apply emip -e mod.emip -d /game/data/");
            Console.WriteLine("  UABEAvalonia decompress -b res.bundle -o res.unpacked");
        }

        #endregion

        #region Shared Utilities

        public static AssetBundleFile DecompressBundle(string file, string? decompFile)
        {
            AssetBundleFile bun = new AssetBundleFile();

            Stream fs = File.OpenRead(file);
            AssetsFileReader r = new AssetsFileReader(fs);

            bun.Read(r);
            if (bun.Header.GetCompressionType() != 0)
            {
                Stream nfs;
                if (decompFile == null)
                    nfs = new MemoryStream();
                else
                    nfs = File.Open(decompFile, FileMode.Create, FileAccess.ReadWrite);

                AssetsFileWriter w = new AssetsFileWriter(nfs);
                bun.Unpack(w);

                nfs.Position = 0;
                fs.Close();

                fs = nfs;
                r = new AssetsFileReader(fs);

                bun = new AssetBundleFile();
                bun.Read(r);
            }

            return bun;
        }

        public static string? GetDecompFilePath(string file, CliOptions options)
        {
            if (options.MemoryDecomp) return null;
            string decompPath = $"{file}.decomp";
            // --fd: force re-decompress by deleting existing .decomp file
            if (options.ForceDecomp && File.Exists(decompPath))
            {
                File.Delete(decompPath);
            }
            return decompPath;
        }

        public static void CleanupDecomp(string? decompFile, CliOptions options)
        {
            if (!options.KeepDecomp && !options.MemoryDecomp && decompFile != null && File.Exists(decompFile))
                File.Delete(decompFile);
        }

        public static string? GetNextBackup(string affectedFilePath)
        {
            for (int i = 0; i < 10000; i++)
            {
                string bakName = $"{affectedFilePath}.bak{i.ToString().PadLeft(4, '0')}";
                if (!File.Exists(bakName))
                {
                    return bakName;
                }
            }

            Console.WriteLine("Too many backups, exiting for your safety.");
            return null;
        }

        public static void Log(CliOptions options, string message)
        {
            if (!options.Quiet)
                Console.WriteLine(message);
        }

        public static void LogVerbose(CliOptions options, string message)
        {
            if (options.Verbose && !options.Quiet)
                Console.WriteLine(message);
        }

        #endregion

        #region Plugin & AssetsManager Initialization

        private static PluginManager InitPlugins()
        {
            PluginManager pm = new PluginManager();
            string pluginDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "plugins");
            if (Directory.Exists(pluginDir))
            {
                pm.LoadPluginsInDirectory(pluginDir);
            }
            return pm;
        }

        private static AssetsManager InitAssetsManager()
        {
            AssetsManager am = new AssetsManager();
            string classDataPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "classdata.tpk");
            if (File.Exists(classDataPath))
            {
                am.LoadClassPackage(classDataPath);
            }
            else
            {
                Console.WriteLine("Warning: classdata.tpk not found. Type resolution may not work.");
            }
            return am;
        }

        #endregion

        #region Asset Filtering & Export Helpers

        /// <summary>
        /// Filter assets by type name, PathID, and name pattern.
        /// </summary>
        private static List<AssetContainer> FilterAssets(
            AssetWorkspace workspace,
            List<AssetContainer> allAssets,
            CliOptions options)
        {
            List<AssetContainer> result = allAssets;

            // Filter by PathID
            if (options.FilterPathIds.Count > 0)
            {
                HashSet<long> pathIdSet = new HashSet<long>(options.FilterPathIds);
                result = result.Where(c => pathIdSet.Contains(c.PathId)).ToList();
            }

            // Filter by type name
            if (options.FilterTypes.Count > 0)
            {
                HashSet<string> typeFilter = new HashSet<string>(options.FilterTypes, StringComparer.OrdinalIgnoreCase);
                result = result.Where(c =>
                {
                    string typeName = GetTypeName(workspace, c);
                    return typeFilter.Contains(typeName);
                }).ToList();
            }

            // Filter by name: supports multiple modes via prefix syntax
            //   default    -> substring match (case-insensitive)
            //   =pattern   -> exact match (case-insensitive)
            //   ~pattern   -> regex match (case-insensitive)
            //   */?        -> wildcard match (case-insensitive)
            //   !prefix    -> negation (exclude matching)
            //   p1,p2,p3   -> OR: match any of the comma-separated patterns
            if (!string.IsNullOrEmpty(options.FilterName))
            {
                var matchers = ParseNameMatchers(options.FilterName);
                result = result.Where(c =>
                {
                    AssetNameUtils.GetDisplayNameFast(workspace, c, false, out string assetName, out string _);
                    return EvaluateNameMatchers(assetName, matchers);
                }).ToList();
            }

            return result;
        }

        #region Name Filter Matching

        private enum NameMatchMode { Substring, Exact, Wildcard, Regex }

        private struct NameMatcher
        {
            public NameMatchMode Mode;
            public string Pattern;       // original pattern text (for Substring/Exact) or compiled regex source
            public Regex? CompiledRegex; // for Wildcard and Regex modes
            public bool Negate;          // ! prefix: invert the match
        }

        /// <summary>
        /// Parse the -n value into a list of matchers.
        /// Comma-separated parts are OR'd. Each part can have prefix: ! (negate), = (exact), ~ (regex).
        /// If the part contains * or ?, it is treated as a wildcard pattern.
        /// Otherwise it is a substring match.
        /// </summary>
        private static List<NameMatcher> ParseNameMatchers(string filterInput)
        {
            var matchers = new List<NameMatcher>();
            // Split by comma for OR logic, but respect escaped commas
            string[] parts = filterInput.Split(',');

            foreach (string rawPart in parts)
            {
                string part = rawPart.Trim();
                if (string.IsNullOrEmpty(part))
                    continue;

                bool negate = false;
                if (part.StartsWith('!'))
                {
                    negate = true;
                    part = part.Substring(1);
                }

                if (string.IsNullOrEmpty(part))
                    continue;

                NameMatcher m = new NameMatcher { Negate = negate };

                if (part.StartsWith('='))
                {
                    // Exact match
                    m.Mode = NameMatchMode.Exact;
                    m.Pattern = part.Substring(1);
                }
                else if (part.StartsWith('~'))
                {
                    // Regex match
                    m.Mode = NameMatchMode.Regex;
                    string regexPattern = part.Substring(1);
                    m.Pattern = regexPattern;
                    try
                    {
                        m.CompiledRegex = new Regex(regexPattern, RegexOptions.IgnoreCase | RegexOptions.Compiled);
                    }
                    catch (ArgumentException)
                    {
                        Console.WriteLine($"  Warning: Invalid regex pattern '{regexPattern}', treating as substring");
                        m.Mode = NameMatchMode.Substring;
                        m.Pattern = regexPattern;
                    }
                }
                else if (part.Contains('*') || part.Contains('?'))
                {
                    // Wildcard match
                    m.Mode = NameMatchMode.Wildcard;
                    m.Pattern = part;
                    string regexPattern = "^" + Regex.Escape(part)
                        .Replace("\\*", ".*").Replace("\\?", ".") + "$";
                    m.CompiledRegex = new Regex(regexPattern, RegexOptions.IgnoreCase | RegexOptions.Compiled);
                }
                else
                {
                    // Substring match (default)
                    m.Mode = NameMatchMode.Substring;
                    m.Pattern = part;
                }

                matchers.Add(m);
            }

            return matchers;
        }

        /// <summary>
        /// Evaluate matchers against an asset name.
        /// Positive matchers (non-negated) are OR'd: at least one must match.
        /// Negative matchers (negated) are AND'd: ALL must pass (i.e., name must NOT match any of them).
        /// If there are only negative matchers, all assets pass the positive check.
        /// </summary>
        private static bool EvaluateNameMatchers(string assetName, List<NameMatcher> matchers)
        {
            bool hasPositive = false;
            bool anyPositiveMatch = false;

            foreach (var m in matchers)
            {
                bool matches = MatchSingle(assetName, m);
                if (m.Negate)
                {
                    // Negated: if it matches, the asset is excluded
                    if (matches)
                        return false;
                }
                else
                {
                    hasPositive = true;
                    if (matches)
                        anyPositiveMatch = true;
                }
            }

            // If there were positive matchers, at least one must have matched
            return !hasPositive || anyPositiveMatch;
        }

        private static bool MatchSingle(string assetName, NameMatcher m)
        {
            return m.Mode switch
            {
                NameMatchMode.Exact => assetName.Equals(m.Pattern, StringComparison.OrdinalIgnoreCase),
                NameMatchMode.Substring => assetName.Contains(m.Pattern, StringComparison.OrdinalIgnoreCase),
                NameMatchMode.Wildcard => m.CompiledRegex != null && m.CompiledRegex.IsMatch(assetName),
                NameMatchMode.Regex => m.CompiledRegex != null && m.CompiledRegex.IsMatch(assetName),
                _ => false,
            };
        }

        #endregion

        private static string GetTypeName(AssetWorkspace workspace, AssetContainer cont)
        {
            AssetNameUtils.GetDisplayNameFast(workspace, cont, false, out string _, out string typeName);
            return typeName;
        }

        private static string GetSafeFileName(string name)
        {
            string safe = PathUtils.ReplaceInvalidPathChars(name);

            // Collapse repeated (Clone) suffixes: "Foo(Clone)(Clone)..." → "Foo(Clone)x47"
            var cloneMatch = System.Text.RegularExpressions.Regex.Match(safe, @"(\(Clone\)){2,}");
            if (cloneMatch.Success)
            {
                int count = cloneMatch.Value.Length / "(Clone)".Length;
                safe = safe.Substring(0, cloneMatch.Index) + $"(Clone)x{count}" + safe.Substring(cloneMatch.Index + cloneMatch.Length);
            }

            return safe;
        }

        /// <summary>
        /// Robustly load the class database for a given AssetsFileInstance.
        /// Tries: assets metadata version -> parentBundle engine version -> fallback latest.
        /// </summary>
        private static void LoadClassDatabase(AssetsManager am, AssetsFileInstance fileInst, CliOptions options)
        {
            string uVer = fileInst.file.Metadata.UnityVersion;

            // If version is 0.0.0, try to get from parent bundle
            if (uVer == "0.0.0" && fileInst.parentBundle != null)
            {
                uVer = fileInst.parentBundle.file.Header.EngineVersion;
            }

            if (uVer != "0.0.0")
            {
                try
                {
                    am.LoadClassDatabaseFromPackage(uVer);
                    return;
                }
                catch
                {
                    LogVerbose(options, $"  Warning: No class database for version '{uVer}', trying fallback...");
                }
            }

            // Try common fallback versions
            string[] fallbacks = { "2022.3.0f1", "2021.3.0f1", "2020.3.0f1", "2019.4.0f1" };
            foreach (string fallback in fallbacks)
            {
                try
                {
                    am.LoadClassDatabaseFromPackage(fallback);
                    LogVerbose(options, $"  Using fallback class database for version '{fallback}'");
                    return;
                }
                catch { }
            }

            if (uVer == "0.0.0")
            {
                Console.WriteLine("  Warning: Unity version unknown and no fallback class database found.");
                Console.WriteLine("  Type names may show as 'Unknown type'. If this file is from a bundle, use 'export bundle' instead.");
            }
        }

        /// <summary>
        /// Get file extension for the given export format.
        /// </summary>
        private static string GetExportExtension(CliExportFormat format)
        {
            return format switch
            {
                CliExportFormat.Raw => ".dat",
                CliExportFormat.Dump => ".txt",
                CliExportFormat.Json => ".json",
                CliExportFormat.Png => ".png",
                CliExportFormat.Wav => ".wav",
                CliExportFormat.Txt => ".txt",
                _ => ".dat",
            };
        }

        /// <summary>
        /// Export a single asset to a file. Supports raw, dump, and json formats.
        /// </summary>
        private static bool ExportSingleAsset(
            AssetWorkspace workspace,
            AssetContainer cont,
            string outputPath,
            CliOptions options)
        {
            try
            {
                AssetImportExport exporter = new AssetImportExport();

                switch (options.Format)
                {
                    case CliExportFormat.Raw:
                    {
                        using FileStream fs = File.Create(outputPath);
                        exporter.DumpRawAsset(fs, cont.FileReader, cont.FilePosition, cont.Size);
                        return true;
                    }
                    case CliExportFormat.Dump:
                    {
                        AssetTypeValueField? baseField = workspace.GetBaseField(cont);
                        if (baseField == null)
                        {
                            LogVerbose(options, $"  Warning: Could not read type tree for PathID {cont.PathId}, falling back to raw");
                            using FileStream fs = File.Create(Path.ChangeExtension(outputPath, ".dat"));
                            exporter.DumpRawAsset(fs, cont.FileReader, cont.FilePosition, cont.Size);
                            return true;
                        }
                        using (StreamWriter sw = new StreamWriter(outputPath))
                        {
                            exporter.DumpTextAsset(sw, baseField);
                        }
                        return true;
                    }
                    case CliExportFormat.Json:
                    {
                        AssetTypeValueField? baseField = workspace.GetBaseField(cont);
                        if (baseField == null)
                        {
                            LogVerbose(options, $"  Warning: Could not read type tree for PathID {cont.PathId}, falling back to raw");
                            using FileStream fs = File.Create(Path.ChangeExtension(outputPath, ".dat"));
                            exporter.DumpRawAsset(fs, cont.FileReader, cont.FilePosition, cont.Size);
                            return true;
                        }
                        using (StreamWriter sw = new StreamWriter(outputPath))
                        {
                            exporter.DumpJsonAsset(sw, baseField);
                        }
                        return true;
                    }
                    case CliExportFormat.Png:
                        return ExportTexture2DAsPng(workspace, cont, outputPath, options);
                    case CliExportFormat.Txt:
                        return ExportTextAssetAsTxt(workspace, cont, outputPath, options);
                    case CliExportFormat.Wav:
                        return ExportAudioClipAsWav(workspace, cont, outputPath, options);
                    default:
                        Console.WriteLine($"  Unknown format '{options.Format}'. Using raw instead.");
                        using (FileStream fs = File.Create(Path.ChangeExtension(outputPath, ".dat")))
                        {
                            exporter.DumpRawAsset(fs, cont.FileReader, cont.FilePosition, cont.Size);
                        }
                        return true;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  Error exporting PathID {cont.PathId}: {ex.Message}");
                LogVerbose(options, $"  Stack: {ex.StackTrace}");
                return false;
            }
        }

        #region Format-Specific Export (PNG / TXT / WAV)

        /// <summary>
        /// Export a Texture2D asset as PNG. Falls back to raw if not a Texture2D or decode fails.
        /// Equivalent to TexturePlugin's BatchExport logic.
        /// </summary>
        private static bool ExportTexture2DAsPng(
            AssetWorkspace workspace, AssetContainer cont, string outputPath, CliOptions options)
        {
            if (cont.ClassId != (int)AssetClassID.Texture2D)
            {
                LogVerbose(options, $"  PathID {cont.PathId} is not Texture2D, falling back to raw");
                return ExportFallbackRaw(cont, outputPath);
            }

            try
            {
                // Read texture base field with byte array handling (same as TextureHelper.GetByteArrayTexture)
                AssetTypeTemplateField textureTemp = workspace.GetTemplateField(cont);
                if (textureTemp == null)
                {
                    LogVerbose(options, $"  Cannot read template for PathID {cont.PathId}, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                AssetTypeTemplateField? imageDataField = textureTemp.Children.FirstOrDefault(f => f.Name == "image data");
                if (imageDataField != null)
                    imageDataField.ValueType = AssetValueType.ByteArray;

                AssetTypeTemplateField? platformBlobField = textureTemp.Children.FirstOrDefault(f => f.Name == "m_PlatformBlob");
                if (platformBlobField != null)
                {
                    AssetTypeTemplateField platformBlobArray = platformBlobField.Children[0];
                    platformBlobArray.ValueType = AssetValueType.ByteArray;
                }

                AssetTypeValueField texBaseField = textureTemp.MakeValue(cont.FileReader, cont.FilePosition);
                TextureFile texFile = TextureFile.ReadTextureFile(texBaseField);

                // Skip 0x0 textures (e.g., Font Texture)
                if (texFile.m_Width == 0 && texFile.m_Height == 0)
                {
                    LogVerbose(options, $"  PathID {cont.PathId}: 0x0 texture, skipping");
                    return false;
                }

                // Load streaming data from bundle if needed (same as TextureHelper.GetResSTexture)
                if (!GetResSTexture(texFile, cont.FileInstance))
                {
                    string resSName = Path.GetFileName(texFile.m_StreamData.path ?? "");
                    Console.WriteLine($"  PathID {cont.PathId}: resS detected but {resSName} not found in bundle, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                // Get raw texture bytes (same as TextureHelper.GetRawTextureBytes)
                byte[]? data = GetRawTextureBytes(texFile, cont.FileInstance);
                if (data == null)
                {
                    string resSName = Path.GetFileName(texFile.m_StreamData.path ?? "");
                    Console.WriteLine($"  PathID {cont.PathId}: resS detected but {resSName} not found on disk, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                // Get platform blob for Switch deswizzle (if applicable)
                byte[]? platformBlob = null;
                AssetTypeValueField pbField = texBaseField["m_PlatformBlob"];
                if (!pbField.IsDummy)
                    platformBlob = pbField["Array"].AsByteArray;

                uint platform = cont.FileInstance.file.Metadata.TargetPlatform;

                // Decode texture to RGBA
                TextureFormat texFormat = (TextureFormat)texFile.m_TextureFormat;
                byte[]? decData = TextureFile.DecodeManaged(data, texFormat, texFile.m_Width, texFile.m_Height);

                if (decData == null)
                {
                    string texFmtName = texFormat.ToString();
                    Console.WriteLine($"  PathID {cont.PathId}: Failed to decode texture format {texFmtName}, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                // DecodeManaged returns BGRA, swap to RGBA
                for (int i = 0; i < decData.Length; i += 4)
                {
                    byte temp = decData[i];
                    decData[i] = decData[i + 2];
                    decData[i + 2] = temp;
                }

                // Create image, flip vertically, save as PNG
                using Image<Rgba32> image = Image.LoadPixelData<Rgba32>(decData, texFile.m_Width, texFile.m_Height);
                image.Mutate(i => i.Flip(FlipMode.Vertical));
                image.SaveAsPng(outputPath);
                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  Error decoding Texture2D PathID {cont.PathId}: {ex.Message}");
                LogVerbose(options, $"  Stack: {ex.StackTrace}");
                return ExportFallbackRaw(cont, outputPath);
            }
        }

        /// <summary>
        /// Export a TextAsset as its raw text/binary data.
        /// Equivalent to TextAssetPlugin's BatchExport logic.
        /// </summary>
        private static bool ExportTextAssetAsTxt(
            AssetWorkspace workspace, AssetContainer cont, string outputPath, CliOptions options)
        {
            if (cont.ClassId != (int)AssetClassID.TextAsset)
            {
                LogVerbose(options, $"  PathID {cont.PathId} is not TextAsset, falling back to raw");
                return ExportFallbackRaw(cont, outputPath);
            }

            try
            {
                AssetTypeValueField? baseField = workspace.GetBaseField(cont);
                if (baseField == null)
                {
                    LogVerbose(options, $"  Cannot read base field for PathID {cont.PathId}, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                byte[] textData = baseField["m_Script"].AsByteArray;

                // Try to determine extension from container path
                string extension = ".txt";
                if (!string.IsNullOrEmpty(cont.Container))
                {
                    string containerFileName = Path.GetFileName(cont.Container);
                    if (containerFileName != Path.GetFileNameWithoutExtension(containerFileName))
                    {
                        extension = Path.GetExtension(cont.Container);
                    }
                }

                string finalPath = Path.ChangeExtension(outputPath, extension);
                File.WriteAllBytes(finalPath, textData);
                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  Error exporting TextAsset PathID {cont.PathId}: {ex.Message}");
                LogVerbose(options, $"  Stack: {ex.StackTrace}");
                return ExportFallbackRaw(cont, outputPath);
            }
        }

        /// <summary>
        /// Export an AudioClip as WAV/OGG. Uses plugin DLL if available, otherwise falls back to raw.
        /// </summary>
        private static bool ExportAudioClipAsWav(
            AssetWorkspace workspace, AssetContainer cont, string outputPath, CliOptions options)
        {
            if (cont.ClassId != (int)AssetClassID.AudioClip)
            {
                LogVerbose(options, $"  PathID {cont.PathId} is not AudioClip, falling back to raw");
                return ExportFallbackRaw(cont, outputPath);
            }

            // Try to use the AudioClipPlugin via plugin manager if available
            if (pluginManager != null)
            {
                var selection = new List<AssetContainer> { cont };
                var menuInfos = pluginManager.GetPluginsThatSupport(workspace.am, selection);
                var exportPlugin = menuInfos.FirstOrDefault(m =>
                    m.displayName.Contains("Export") && m.displayName.Contains("audio", StringComparison.OrdinalIgnoreCase));

                if (exportPlugin != null)
                {
                    // AudioClip plugin found, but ExecutePlugin requires a Window.
                    // Fall through to manual implementation below.
                }
            }

            // Manual AudioClip export: try to load Fmod5Sharp via reflection
            try
            {
                AssetTypeValueField? baseField = workspace.GetBaseField(cont);
                if (baseField == null)
                {
                    LogVerbose(options, $"  Cannot read base field for AudioClip PathID {cont.PathId}, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                string resourceSource = baseField["m_Resource.m_Source"].AsString;
                ulong resourceOffset = baseField["m_Resource.m_Offset"].AsULong;
                ulong resourceSize = baseField["m_Resource.m_Size"].AsULong;

                byte[]? audioData = GetAudioResourceBytes(cont, resourceSource, resourceOffset, resourceSize);
                if (audioData == null || audioData.Length == 0)
                {
                    Console.WriteLine($"  PathID {cont.PathId}: Could not locate audio resource data, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                // Try loading Fmod5Sharp dynamically
                string pluginDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "plugins");
                string fmodPath = Path.Combine(pluginDir, "Fmod5Sharp.dll");
                if (!File.Exists(fmodPath))
                {
                    Console.WriteLine($"  PathID {cont.PathId}: Fmod5Sharp.dll not found in plugins/, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                var fmodAsm = System.Reflection.Assembly.LoadFrom(fmodPath);
                var fsbLoaderType = fmodAsm.GetType("Fmod5Sharp.FsbLoader");
                if (fsbLoaderType == null)
                {
                    Console.WriteLine($"  PathID {cont.PathId}: Cannot find FsbLoader type, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                // Call FsbLoader.TryLoadFsbFromByteArray(audioData, out FmodSoundBank bank)
                var tryLoadMethod = fsbLoaderType.GetMethod("TryLoadFsbFromByteArray",
                    System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                if (tryLoadMethod == null)
                {
                    Console.WriteLine($"  PathID {cont.PathId}: Cannot find TryLoadFsbFromByteArray method, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                object?[] loadArgs = new object?[] { audioData, null };
                bool loaded = (bool)tryLoadMethod.Invoke(null, loadArgs)!;
                if (!loaded || loadArgs[1] == null)
                {
                    Console.WriteLine($"  PathID {cont.PathId}: Failed to parse FSB audio data, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                // bank.Samples[0].RebuildAsStandardFileFormat(out byte[] sampleData, out string sampleExtension)
                object bank = loadArgs[1]!;
                var samplesProperty = bank.GetType().GetProperty("Samples");
                var samples = samplesProperty?.GetValue(bank) as System.Collections.IList;
                if (samples == null || samples.Count == 0)
                {
                    Console.WriteLine($"  PathID {cont.PathId}: No audio samples found in FSB, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                object sample = samples[0]!;
                var rebuildMethod = sample.GetType().GetMethod("RebuildAsStandardFileFormat");
                if (rebuildMethod == null)
                {
                    Console.WriteLine($"  PathID {cont.PathId}: Cannot find RebuildAsStandardFileFormat, falling back to raw");
                    return ExportFallbackRaw(cont, outputPath);
                }

                object?[] rebuildArgs = new object?[] { null, null };
                rebuildMethod.Invoke(sample, rebuildArgs);
                byte[] sampleData = (byte[])rebuildArgs[0]!;
                string sampleExtension = (string)rebuildArgs[1]!;

                if (sampleExtension.Equals("wav", StringComparison.OrdinalIgnoreCase))
                {
                    FixWAV(ref sampleData);
                }

                string finalPath = Path.ChangeExtension(outputPath, "." + sampleExtension);
                File.WriteAllBytes(finalPath, sampleData);
                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  Error exporting AudioClip PathID {cont.PathId}: {ex.Message}");
                LogVerbose(options, $"  Stack: {ex.StackTrace}");
                return ExportFallbackRaw(cont, outputPath);
            }
        }

        /// <summary>
        /// Fallback: export as raw .dat file.
        /// </summary>
        private static bool ExportFallbackRaw(AssetContainer cont, string outputPath)
        {
            try
            {
                string datPath = Path.ChangeExtension(outputPath, ".dat");
                AssetImportExport exporter = new AssetImportExport();
                using FileStream fs = File.Create(datPath);
                exporter.DumpRawAsset(fs, cont.FileReader, cont.FilePosition, cont.Size);
                return true;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Load streaming texture data from bundle (equivalent to TextureHelper.GetResSTexture).
        /// </summary>
        private static bool GetResSTexture(TextureFile texFile, AssetsFileInstance fileInst)
        {
            TextureFile.StreamingInfo streamInfo = texFile.m_StreamData;
            if (streamInfo.path != null && streamInfo.path != "" && fileInst.parentBundle != null)
            {
                string searchPath = streamInfo.path;
                if (searchPath.StartsWith("archive:/"))
                    searchPath = searchPath.Substring(9);

                searchPath = Path.GetFileName(searchPath);

                AssetBundleFile bundle = fileInst.parentBundle.file;
                AssetsFileReader reader = bundle.DataReader;
                AssetBundleDirectoryInfo[] dirInf = bundle.BlockAndDirInfo.DirectoryInfos;
                for (int i = 0; i < dirInf.Length; i++)
                {
                    AssetBundleDirectoryInfo info = dirInf[i];
                    if (info.Name == searchPath)
                    {
                        reader.Position = info.Offset + (long)streamInfo.offset;
                        texFile.pictureData = reader.ReadBytes((int)streamInfo.size);
                        texFile.m_StreamData.offset = 0;
                        texFile.m_StreamData.size = 0;
                        texFile.m_StreamData.path = "";
                        return true;
                    }
                }
                return false;
            }
            return true;
        }

        /// <summary>
        /// Get raw texture bytes from file or streaming data (equivalent to TextureHelper.GetRawTextureBytes).
        /// </summary>
        private static byte[]? GetRawTextureBytes(TextureFile texFile, AssetsFileInstance inst)
        {
            string? rootPath = Path.GetDirectoryName(inst.path);
            if (texFile.m_StreamData.size != 0 && texFile.m_StreamData.path != string.Empty)
            {
                string fixedStreamPath = texFile.m_StreamData.path;
                if (inst.parentBundle == null && fixedStreamPath.StartsWith("archive:/"))
                {
                    fixedStreamPath = Path.GetFileName(fixedStreamPath);
                }
                if (!Path.IsPathRooted(fixedStreamPath) && rootPath != null)
                {
                    fixedStreamPath = Path.Combine(rootPath, fixedStreamPath);
                }
                if (File.Exists(fixedStreamPath))
                {
                    Stream stream = File.OpenRead(fixedStreamPath);
                    stream.Position = (long)texFile.m_StreamData.offset;
                    texFile.pictureData = new byte[texFile.m_StreamData.size];
                    stream.Read(texFile.pictureData, 0, (int)texFile.m_StreamData.size);
                }
                else
                {
                    return null;
                }
            }
            return texFile.pictureData;
        }

        /// <summary>
        /// Get audio resource bytes from bundle or file (equivalent to AudioClipPlugin's GetAudioBytes).
        /// </summary>
        private static byte[]? GetAudioResourceBytes(AssetContainer cont, string filepath, ulong offset, ulong size)
        {
            if (string.IsNullOrEmpty(filepath))
                return null;

            if (cont.FileInstance.parentBundle != null)
            {
                string searchPath = filepath;
                if (searchPath.StartsWith("archive:/"))
                    searchPath = searchPath.Substring(9);

                searchPath = Path.GetFileName(searchPath);

                AssetBundleFile bundle = cont.FileInstance.parentBundle.file;
                AssetsFileReader reader = bundle.DataReader;
                AssetBundleDirectoryInfo[] dirInf = bundle.BlockAndDirInfo.DirectoryInfos;
                for (int i = 0; i < dirInf.Length; i++)
                {
                    AssetBundleDirectoryInfo info = dirInf[i];
                    if (info.Name == searchPath)
                    {
                        reader.Position = info.Offset + (long)offset;
                        return reader.ReadBytes((int)size);
                    }
                }
            }

            string? assetsFileDirectory = Path.GetDirectoryName(cont.FileInstance.path);
            if (cont.FileInstance.parentBundle != null)
            {
                assetsFileDirectory = Path.GetDirectoryName(assetsFileDirectory);
            }

            if (assetsFileDirectory != null)
            {
                string resourceFilePath = Path.Combine(assetsFileDirectory, filepath);
                if (File.Exists(resourceFilePath))
                {
                    AssetsFileReader reader = new AssetsFileReader(resourceFilePath);
                    reader.Position = (long)offset;
                    return reader.ReadBytes((int)size);
                }

                string resourceFileName = Path.Combine(assetsFileDirectory, Path.GetFileName(filepath));
                if (File.Exists(resourceFileName))
                {
                    AssetsFileReader reader = new AssetsFileReader(resourceFileName);
                    reader.Position = (long)offset;
                    return reader.ReadBytes((int)size);
                }
            }

            return null;
        }

        /// <summary>
        /// Fix malformed WAV data from Fmod5Sharp (same as AudioClipPlugin's FixWAV).
        /// </summary>
        private static void FixWAV(ref byte[] wavData)
        {
            int origLength = wavData.Length;
            // remove ExtraParamSize field from fmt subchunk
            for (int i = 36; i < origLength - 2; i++)
            {
                wavData[i] = wavData[i + 2];
            }
            Array.Resize(ref wavData, origLength - 2);
            // write ChunkSize to RIFF chunk
            byte[] riffHeaderChunkSize = BitConverter.GetBytes(wavData.Length - 8);
            if (!BitConverter.IsLittleEndian)
                Array.Reverse(riffHeaderChunkSize);
            riffHeaderChunkSize.CopyTo(wavData, 4);
            // write ChunkSize to fmt chunk
            byte[] fmtHeaderChunkSize = BitConverter.GetBytes(16);
            if (!BitConverter.IsLittleEndian)
                Array.Reverse(fmtHeaderChunkSize);
            fmtHeaderChunkSize.CopyTo(wavData, 16);
            // write ChunkSize to data chunk
            byte[] dataHeaderChunkSize = BitConverter.GetBytes(wavData.Length - 44);
            if (!BitConverter.IsLittleEndian)
                Array.Reverse(dataHeaderChunkSize);
            dataHeaderChunkSize.CopyTo(wavData, 40);
        }

        /// <summary>
        /// Try to encode a texture image via TexturePlugin.dll (loaded as plugin).
        /// Uses TexturePlugin.TextureEncoderDecoder.Encode via reflection.
        /// Returns encoded bytes or null if plugin not available or encoding fails.
        /// </summary>
        private static byte[]? TryEncodeViaTexturePlugin(
            string imagePath,
            Image<Rgba32> image,
            TextureFormat format,
            int width, int height,
            ref int mips,
            uint platform,
            byte[]? platformBlob,
            CliOptions options)
        {
            // Register AssemblyResolve handler so that TexturePlugin.dll's dependencies
            // (which live in the app's base directory, not the plugins/ subdir) can be found.
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            ResolveEventHandler resolveHandler = (sender, resolveArgs) =>
            {
                string dllName = new System.Reflection.AssemblyName(resolveArgs.Name).Name + ".dll";
                string candidate = Path.Combine(baseDir, dllName);
                if (File.Exists(candidate))
                    return System.Reflection.Assembly.LoadFrom(candidate);
                return null;
            };
            AppDomain.CurrentDomain.AssemblyResolve += resolveHandler;

            try
            {
                string pluginDir = Path.Combine(baseDir, "plugins");
                string texPluginPath = Path.Combine(pluginDir, "TexturePlugin.dll");
                if (!File.Exists(texPluginPath))
                {
                    LogVerbose(options, $"  TexturePlugin.dll not found in plugins/, cannot encode {format}");
                    return null;
                }

                var texAsm = System.Reflection.Assembly.LoadFrom(texPluginPath);

                // Add DllImportResolver to find native libraries (like libtextoolwrap.so) in the base directory
                try
                {
                    System.Runtime.InteropServices.NativeLibrary.SetDllImportResolver(texAsm, (libraryName, assembly, searchPath) =>
                    {
                        // Try loading directly from base directory
                        string exactPath = Path.Combine(baseDir, libraryName);
                        if (System.Runtime.InteropServices.NativeLibrary.TryLoad(exactPath, out IntPtr handle))
                            return handle;

                        // Try with "lib" prefix and ".so" suffix (standard Linux)
                        string linuxPath = Path.Combine(baseDir, "lib" + libraryName + ".so");
                        if (System.Runtime.InteropServices.NativeLibrary.TryLoad(linuxPath, out handle))
                            return handle;

                        // Try with just ".so" suffix? or ".dll"?
                        string winPath = Path.Combine(baseDir, libraryName + ".dll");
                        if (System.Runtime.InteropServices.NativeLibrary.TryLoad(winPath, out handle))
                            return handle;
                        
                        return IntPtr.Zero;
                    });
                }
                catch (InvalidOperationException) 
                {
                    // Resolver already set, ignore
                }

                // Find TextureImportExport type — use GetTypes() with fault tolerance
                // since GetType() can return null when some dependency types fail to resolve.
                Type? importExportType = null;
                Type? encoderDecoderType = null;
                try
                {
                    var allTypes = texAsm.GetTypes();
                    LogVerbose(options, $"  TexturePlugin.dll loaded, {allTypes.Length} types found:");
                    foreach (var t in allTypes)
                    {
                        LogVerbose(options, $"    Type: {t.FullName}");
                        if (t.FullName == "TexturePlugin.TextureImportExport")
                            importExportType = t;
                        if (t.FullName == "TexturePlugin.TextureEncoderDecoder")
                            encoderDecoderType = t;
                    }
                }
                catch (System.Reflection.ReflectionTypeLoadException rtle)
                {
                    LogVerbose(options, $"  ReflectionTypeLoadException: {rtle.Message}");
                    if (rtle.LoaderExceptions != null)
                    {
                        foreach (var le in rtle.LoaderExceptions)
                            if (le != null) LogVerbose(options, $"    Loader: {le.Message}");
                    }
                    LogVerbose(options, $"  Loaded types count: {rtle.Types?.Count(t => t != null) ?? 0}");
                    foreach (var t in rtle.Types)
                    {
                        if (t == null) continue;
                        LogVerbose(options, $"    Type: {t.FullName}");
                        if (t.FullName == "TexturePlugin.TextureImportExport")
                            importExportType = t;
                        if (t.FullName == "TexturePlugin.TextureEncoderDecoder")
                            encoderDecoderType = t;
                    }
                }

                // Strategy 1: Use TextureImportExport.Import (handles Switch deswizzle, mipmaps, flip)
                if (importExportType != null)
                {
                    LogVerbose(options, $"  Found TextureImportExport, trying Import method...");
                    return TryCallImportMethod(importExportType, imagePath, image, format, width, height, ref mips, platform, platformBlob, options);
                }

                // Strategy 2: Use TextureEncoderDecoder.Encode directly (no Switch support, but handles most cases)
                if (encoderDecoderType != null)
                {
                    LogVerbose(options, $"  TextureImportExport not found, trying TextureEncoderDecoder.Encode...");
                    return TryCallEncoderDecoder(encoderDecoderType, image, format, width, height, ref mips, options);
                }

                LogVerbose(options, $"  Cannot find TextureImportExport or TextureEncoderDecoder in TexturePlugin.dll");
                return null;
            }
            catch (Exception ex)
            {
                LogVerbose(options, $"  TexturePlugin encode failed: {ex.InnerException?.Message ?? ex.Message}");
                return null;
            }
            finally
            {
                AppDomain.CurrentDomain.AssemblyResolve -= resolveHandler;
            }
        }

        /// <summary>
        /// Try to call TextureImportExport.Import via reflection.
        /// </summary>
        private static byte[]? TryCallImportMethod(
            Type importExportType,
            string imagePath,
            Image<Rgba32> image,
            TextureFormat format,
            int width, int height,
            ref int mips,
            uint platform,
            byte[]? platformBlob,
            CliOptions options)
        {
            try
            {
                // Find the Import method with string (imagePath) overload by parameter count and first param type
                System.Reflection.MethodInfo? importStringMethod = null;
                System.Reflection.MethodInfo? importImageMethod = null;

                foreach (var m in importExportType.GetMethods(
                    System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
                {
                    if (m.Name != "Import") continue;
                    var parms = m.GetParameters();
                    if (parms.Length < 5) continue;

                    if (parms[0].ParameterType == typeof(string))
                        importStringMethod = m;
                    else if (parms[0].ParameterType.Name.Contains("Image"))
                        importImageMethod = m;
                }

                // Prefer the string overload — avoids Image<Rgba32> type mismatch issues
                if (importStringMethod != null)
                {
                    LogVerbose(options, $"  Calling TextureImportExport.Import(string, ...) for {format}");
                    object?[] args = new object?[] { imagePath, format, 0, 0, mips, platform, platformBlob };
                    byte[]? result = (byte[]?)importStringMethod.Invoke(null, args);
                    if (result != null)
                    {
                        mips = (int)args[4]!;
                    }
                    return result;
                }

                if (importImageMethod != null)
                {
                    LogVerbose(options, $"  Calling TextureImportExport.Import(Image, ...) for {format}");
                    // Clone and undo our flip — the Import method flips internally
                    using Image<Rgba32> imageForPlugin = image.Clone();
                    imageForPlugin.Mutate(i => i.Flip(FlipMode.Vertical));

                    object?[] args = new object?[] { imageForPlugin, format, 0, 0, mips, platform, platformBlob };
                    byte[]? result = (byte[]?)importImageMethod.Invoke(null, args);
                    if (result != null)
                    {
                        mips = (int)args[4]!;
                    }
                    return result;
                }

                LogVerbose(options, $"  Cannot find Import method in TextureImportExport");
                return null;
            }
            catch (Exception ex)
            {
                LogVerbose(options, $"  TextureImportExport.Import failed: {ex.InnerException?.Message ?? ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Fallback: call TextureEncoderDecoder.Encode directly via reflection.
        /// </summary>
        private static byte[]? TryCallEncoderDecoder(
            Type encoderDecoderType,
            Image<Rgba32> image,
            TextureFormat format,
            int width, int height,
            ref int mips,
            CliOptions options)
        {
            try
            {
                // Find Encode(Image<Rgba32>, int, int, TextureFormat, int, int) method
                System.Reflection.MethodInfo? encodeMethod = null;
                foreach (var m in encoderDecoderType.GetMethods(
                    System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
                {
                    if (m.Name != "Encode") continue;
                    var parms = m.GetParameters();
                    // Encode(Image<Rgba32> image, int width, int height, TextureFormat format, int quality, int mips)
                    if (parms.Length >= 4 && parms[0].ParameterType.Name.Contains("Image"))
                    {
                        encodeMethod = m;
                        break;
                    }
                }

                if (encodeMethod == null)
                {
                    LogVerbose(options, $"  Cannot find Encode method in TextureEncoderDecoder");
                    return null;
                }

                LogVerbose(options, $"  Calling TextureEncoderDecoder.Encode for {format}");

                // The Encode method expects a pre-flipped image (already done by caller)
                object?[] args;
                var parmInfos = encodeMethod.GetParameters();
                if (parmInfos.Length == 6)
                    args = new object?[] { image, width, height, format, 5, mips };
                else if (parmInfos.Length == 5)
                    args = new object?[] { image, width, height, format, 5 };
                else
                    args = new object?[] { image, width, height, format };

                byte[]? result = (byte[]?)encodeMethod.Invoke(null, args);
                return result;
            }
            catch (Exception ex)
            {
                LogVerbose(options, $"  TextureEncoderDecoder.Encode failed: {ex.InnerException?.Message ?? ex.Message}");
                return null;
            }
        }

        #endregion

        /// <summary>
        /// Core logic: export assets from an AssetsFileInstance that is already loaded.
        /// Returns the number of assets exported.
        /// </summary>
        private static int ExportFromAssetsFile(
            AssetWorkspace workspace,
            AssetsFileInstance fileInst,
            string outputDir,
            CliOptions options,
            string filePrefix = "")
        {
            List<AssetContainer> allAssets = workspace.LoadedAssets.Values
                .Where(c => c.FileInstance == fileInst)
                .ToList();

            List<AssetContainer> filtered = FilterAssets(workspace, allAssets, options);

            if (filtered.Count == 0)
            {
                LogVerbose(options, $"  No matching assets found in {fileInst.name}");
                return 0;
            }

            Log(options, $"  Found {filtered.Count} asset(s) to export from {fileInst.name}");

            string ext = GetExportExtension(options.Format);
            string assetsFileName = Path.GetFileName(fileInst.path);
            int exportedCount = 0;

            foreach (AssetContainer cont in filtered)
            {
                AssetNameUtils.GetDisplayNameFast(workspace, cont, false, out string assetName, out string _);
                string safeName = GetSafeFileName(assetName);
                string fileName;

                if (options.KeepNames)
                {
                    // --keepnames: use original asset name only (no assetsFileName/PathID suffix)
                    fileName = $"{safeName}{ext}";
                    // Handle duplicate names by appending PathID if file already exists
                    string checkPath = Path.Combine(outputDir, fileName);
                    if (File.Exists(checkPath))
                    {
                        fileName = $"{safeName}-{cont.PathId}{ext}";
                    }
                }
                else
                {
                    // GUI-compatible format: {assetName}-{assetsFileName}-{PathID}.{ext}
                    fileName = $"{safeName}-{assetsFileName}-{cont.PathId}{ext}";
                }

                // Truncate filename if it would exceed OS limits (max 255 bytes for most filesystems)
                const int maxFileNameLen = 240; // leave room for filesystem overhead
                if (fileName.Length > maxFileNameLen)
                {
                    // Keep the suffix intact, truncate safeName
                    string suffix = options.KeepNames
                        ? ext
                        : $"-{assetsFileName}-{cont.PathId}{ext}";
                    int availableForName = maxFileNameLen - suffix.Length;
                    if (availableForName < 20) availableForName = 20;
                    if (safeName.Length > availableForName)
                    {
                        safeName = safeName.Substring(0, availableForName) + "~";
                    }
                    fileName = $"{safeName}{suffix}";
                }

                string outputPath = Path.Combine(outputDir, fileName);

                if (options.DryRun)
                {
                    Log(options, $"  [dry-run] Would export: {fileName}");
                    exportedCount++;
                    continue;
                }

                LogVerbose(options, $"  Exporting {fileName}...");
                if (ExportSingleAsset(workspace, cont, outputPath, options))
                {
                    exportedCount++;
                }
            }

            return exportedCount;
        }

        #endregion

        #region Command Routing

        public static void CLHMain(string[] args)
        {
            CliOptions options = CliParser.Parse(args);

            // 打印解析错误
            if (options.HasErrors)
            {
                foreach (string error in options.Errors)
                {
                    Console.WriteLine($"Error: {error}");
                }
                Console.WriteLine();
                Console.WriteLine("Use --help for usage information.");
                return;
            }

            // 帮助命令 / 空参数
            if (options.Verb == CliVerb.Help || options.Verb == CliVerb.None)
            {
                PrintHelp();
                return;
            }

            // 初始化插件和 AssetsManager (仅新版命令需要)
            if (options.Verb != CliVerb.LegacyBatchExportBundle &&
                options.Verb != CliVerb.LegacyBatchImportBundle &&
                options.Verb != CliVerb.LegacyApplyEmip)
            {
                assetsManager = InitAssetsManager();
                pluginManager = InitPlugins();
                LogVerbose(options, "AssetsManager and plugins loaded.");
            }

            // 路由到命令处理器
            switch (options.Verb)
            {
                // ===== 新版命令 =====
                case CliVerb.Export:
                    HandleExport(options);
                    break;
                case CliVerb.Import:
                    HandleImport(options);
                    break;
                case CliVerb.Apply:
                    HandleApply(options);
                    break;
                case CliVerb.List:
                    HandleList(options);
                    break;
                case CliVerb.Info:
                    HandleInfo(options);
                    break;
                case CliVerb.Decompress:
                    HandleDecompress(options);
                    break;
                case CliVerb.Compress:
                    HandleCompress(options);
                    break;

                // ===== 旧版兼容命令 =====
                case CliVerb.LegacyBatchExportBundle:
                    LegacyCommands.BatchExportBundle(args, options);
                    break;
                case CliVerb.LegacyBatchImportBundle:
                    LegacyCommands.BatchImportBundle(args, options);
                    break;
                case CliVerb.LegacyApplyEmip:
                    LegacyCommands.ApplyEmip(args, options);
                    break;

                default:
                    Console.WriteLine($"Command not implemented yet: {options.Verb}");
                    break;
            }
        }

        #endregion

        #region New Command Handlers (Stubs for Phase 2+)

        private static void HandleExport(CliOptions options)
        {
            if (!string.IsNullOrEmpty(options.FilePath))
            {
                // 单文件模式: 自动检测 bundle vs assets
                ExportFile(options);
            }
            else if (!string.IsNullOrEmpty(options.DirectoryPath))
            {
                // 目录批量模式: 自动检测每个文件
                ExportDir(options);
            }
            else
            {
                Console.WriteLine("'export' requires -f <file> or -d <dir>. Use --help for details.");
            }
        }

        private static void HandleImport(CliOptions options)
        {
            if (!string.IsNullOrEmpty(options.FilePath))
            {
                // 单文件模式: 自动检测 bundle vs assets
                ImportFile(options);
            }
            else if (!string.IsNullOrEmpty(options.DirectoryPath))
            {
                // 目录批量模式: 自动检测每个文件
                ImportDir(options);
            }
            else
            {
                Console.WriteLine("'import' requires -f <file> or -d <dir>. Use --help for details.");
            }
        }

        private static void HandleApply(CliOptions options)
        {
            if (options.Target == CliTarget.Emip)
            {
                ApplyEmip(options);
            }
            else
            {
                Console.WriteLine("Unknown apply target. Use: emip");
            }
        }

        private static void HandleList(CliOptions options)
        {
            if (!string.IsNullOrEmpty(options.FilePath))
            {
                // 单文件模式
                string file = options.FilePath;
                if (!File.Exists(file)) { Console.WriteLine($"File not found: {file}"); return; }
                DetectedFileType ft = FileTypeDetector.DetectFileType(file);
                if (ft == DetectedFileType.BundleFile)
                    ListBundle(CloneOptionsWithPath(options, bundlePath: file));
                else if (ft == DetectedFileType.AssetsFile)
                    ListAssets(CloneOptionsWithPath(options, assetsPath: file));
                else
                    Console.WriteLine($"Unsupported file type for 'list': {file}");
            }
            else if (!string.IsNullOrEmpty(options.DirectoryPath))
            {
                // 目录批量模式
                ListDir(options);
            }
            else
            {
                Console.WriteLine("'list' requires -f <file> or -d <dir>.");
            }
        }

        private static void HandleInfo(CliOptions options)
        {
            if (!string.IsNullOrEmpty(options.FilePath))
            {
                string file = options.FilePath;
                if (!File.Exists(file)) { Console.WriteLine($"File not found: {file}"); return; }
                DetectedFileType ft = FileTypeDetector.DetectFileType(file);
                if (ft == DetectedFileType.BundleFile)
                    InfoBundle(CloneOptionsWithPath(options, bundlePath: file));
                else if (ft == DetectedFileType.AssetsFile)
                    InfoAssets(CloneOptionsWithPath(options, assetsPath: file));
                else
                    Console.WriteLine($"Unsupported file type for 'info': {file}");
            }
            else if (!string.IsNullOrEmpty(options.DirectoryPath))
            {
                // 目录批量模式
                InfoDir(options);
            }
            else
            {
                Console.WriteLine("'info' requires -f <file> or -d <dir>.");
            }
        }

        private static void HandleDecompress(CliOptions options)
        {
            string file = options.BundlePath;
            if (string.IsNullOrEmpty(file))
            {
                Console.WriteLine("Error: -b/--bundle is required for decompress.");
                return;
            }
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return;
            }

            string outputFile = options.OutputDir;
            if (string.IsNullOrEmpty(outputFile))
            {
                outputFile = file + ".unpacked";
            }

            Log(options, $"Decompressing {Path.GetFileName(file)}...");

            AssetBundleFile bun = new AssetBundleFile();
            FileStream fs = File.OpenRead(file);
            AssetsFileReader r = new AssetsFileReader(fs);
            bun.Read(r);

            using (FileStream ofs = File.Open(outputFile, FileMode.Create, FileAccess.ReadWrite))
            {
                AssetsFileWriter w = new AssetsFileWriter(ofs);
                bun.Unpack(w);
            }

            bun.Close();
            Log(options, $"Done. Output: {outputFile}");
        }

        private static void HandleCompress(CliOptions options)
        {
            string file = options.BundlePath;
            if (string.IsNullOrEmpty(file))
            {
                Console.WriteLine("Error: -b/--bundle is required for compress.");
                return;
            }
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return;
            }

            string outputFile = options.OutputDir;
            if (string.IsNullOrEmpty(outputFile))
            {
                outputFile = file + ".packed";
            }

            AssetBundleCompressionType compType = options.CompressMethod switch
            {
                CliCompressMethod.Lz4 => AssetBundleCompressionType.LZ4,
                CliCompressMethod.Lzma => AssetBundleCompressionType.LZMA,
                _ => AssetBundleCompressionType.LZ4, // default to LZ4
            };

            Log(options, $"Compressing {Path.GetFileName(file)} with {compType}...");

            AssetBundleFile bun = new AssetBundleFile();
            FileStream fs = File.OpenRead(file);
            AssetsFileReader r = new AssetsFileReader(fs);
            bun.Read(r);

            using (FileStream ofs = File.Open(outputFile, FileMode.Create))
            using (AssetsFileWriter w = new AssetsFileWriter(ofs))
            {
                bun.Pack(bun.Reader, w, compType);
            }

            bun.Close();
            Log(options, $"Done. Output: {outputFile}");
        }

        #endregion

        #region Export Implementations

        /// <summary>
        /// 單文件模式: 自動偵測 bundle vs assets，派發到對應 Export 方法。
        /// </summary>
        private static void ExportFile(CliOptions options)
        {
            string file = options.FilePath;
            DetectedFileType ft = FileTypeDetector.DetectFileType(file);
            if (ft == DetectedFileType.BundleFile)
                ExportBundle(CloneOptionsWithPath(options, bundlePath: file));
            else if (ft == DetectedFileType.AssetsFile)
                ExportAssets(CloneOptionsWithPath(options, assetsPath: file));
            else
                Console.WriteLine($"Cannot determine file type (not a bundle or assets file): {file}");
        }

        /// <summary>
        /// 目錄批量模式: 掃描目錄，自動偵測每個文件並派發。
        /// 合併了原先的 ExportBundleDir + ExportAssetsDir。
        /// </summary>
        private static void ExportDir(CliOptions options)
        {
            string dir = options.DirectoryPath;
            if (!Directory.Exists(dir))
            {
                Console.WriteLine($"Directory not found: {dir}");
                return;
            }

            SearchOption searchOpt = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            int fileCount = 0;

            foreach (string file in Directory.EnumerateFiles(dir, "*", searchOpt))
            {
                DetectedFileType ft = FileTypeDetector.DetectFileType(file);
                if (ft == DetectedFileType.BundleFile)
                {
                    fileCount++;
                    Log(options, $"Processing bundle: {file}");
                    ExportBundle(CloneOptionsWithPath(options, bundlePath: file));
                }
                else if (ft == DetectedFileType.AssetsFile)
                {
                    fileCount++;
                    Log(options, $"Processing assets: {file}");
                    ExportAssets(CloneOptionsWithPath(options, assetsPath: file));
                }
            }

            if (fileCount == 0)
                Console.WriteLine($"No bundle or assets files found in {dir}");
            else
                Log(options, $"Processed {fileCount} file(s).");
        }

        private static void ExportBundle(CliOptions options)
        {
            string file = options.BundlePath;
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return;
            }

            Directory.CreateDirectory(options.OutputDir);

            AssetsManager am = assetsManager!;
            string? decompFile = GetDecompFilePath(file, options);

            // Load bundle via AssetsManager for proper parentBundle linkage
            BundleFileInstance bundleInst;
            AssetBundleFile bun;

            // Check if cached .decomp already exists (reuse unless --fd)
            if (decompFile != null && File.Exists(decompFile))
            {
                LogVerbose(options, $"Reusing cached decomp: {decompFile}");
                Stream cachedStream = File.Open(decompFile, FileMode.Open, FileAccess.Read);
                bundleInst = am.LoadBundleFile(cachedStream, file, false);
                bun = bundleInst.file;
            }
            else
            {
                Log(options, $"Decompressing {Path.GetFileName(file)}...");
                bundleInst = am.LoadBundleFile(file, false);
                bun = bundleInst.file;

                // Decompress if needed
                if (AssetBundleUtil.IsBundleDataCompressed(bun))
                {
                    Stream decompStream;
                    if (decompFile != null)
                        decompStream = File.Open(decompFile, FileMode.Create, FileAccess.ReadWrite);
                    else
                        decompStream = new MemoryStream();

                    AssetsFileWriter w = new AssetsFileWriter(decompStream);
                    bun.Unpack(w);
                    decompStream.Position = 0;

                    am.UnloadBundleFile(bundleInst);
                    bundleInst = am.LoadBundleFile(decompStream, file, false);
                    bun = bundleInst.file;
                }
            }

            int totalExported = 0;
            int entryCount = bun.BlockAndDirInfo.DirectoryInfos.Length;
            for (int i = 0; i < entryCount; i++)
            {
                string entryName = bun.BlockAndDirInfo.DirectoryInfos[i].Name;

                // Load the entry as assets file via AssetsManager with parentBundle set
                AssetsFileInstance? fileInst;
                try
                {
                    fileInst = am.LoadAssetsFileFromBundle(bundleInst, i, false);
                    // Detect if it's actually a valid assets file
                    if (fileInst.file.AssetInfos == null || fileInst.file.AssetInfos.Count == 0)
                    {
                        LogVerbose(options, $"  Skipping non-assets entry: {entryName}");
                        continue;
                    }
                }
                catch
                {
                    LogVerbose(options, $"  Skipping non-assets entry: {entryName}");
                    continue;
                }

                // Load class database for this unity version
                LoadClassDatabase(am, fileInst, options);

                AssetWorkspace workspace = new AssetWorkspace(am, true);
                workspace.LoadAssetsFile(fileInst, false);

                totalExported += ExportFromAssetsFile(workspace, fileInst, options.OutputDir, options);
            }

            am.UnloadBundleFile(bundleInst);
            CleanupDecomp(decompFile, options);

            Log(options, $"Done. Exported {totalExported} asset(s) from {Path.GetFileName(file)}.");
        }

        private static void ExportBundleDir(CliOptions options)
        {
            string dir = options.DirectoryPath;
            if (!Directory.Exists(dir))
            {
                Console.WriteLine($"Directory not found: {dir}");
                return;
            }

            SearchOption searchOpt = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            int totalExported = 0;
            int bundleCount = 0;

            foreach (string file in Directory.EnumerateFiles(dir, "*", searchOpt))
            {
                DetectedFileType fileType = FileTypeDetector.DetectFileType(file);
                if (fileType != DetectedFileType.BundleFile)
                    continue;

                bundleCount++;
                Log(options, $"Processing bundle: {file}");

                // Reuse ExportBundle by temporarily setting the bundle path
                CliOptions singleOptions = CloneOptionsWithPath(options, bundlePath: file);
                ExportBundle(singleOptions);
            }

            if (bundleCount == 0)
                Console.WriteLine($"No bundle files found in {dir}");
            else
                Log(options, $"Processed {bundleCount} bundle(s).");
        }

        private static void ExportAssets(CliOptions options)
        {
            string file = options.AssetsPath;
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return;
            }

            Directory.CreateDirectory(options.OutputDir);

            AssetsManager am = assetsManager!;
            AssetsFileInstance fileInst = am.LoadAssetsFile(file, true);

            LoadClassDatabase(am, fileInst, options);

            AssetWorkspace workspace = new AssetWorkspace(am, false);
            workspace.LoadAssetsFile(fileInst, false);

            int count = ExportFromAssetsFile(workspace, fileInst, options.OutputDir, options);

            Log(options, $"Done. Exported {count} asset(s) from {Path.GetFileName(file)}.");
        }

        private static void ExportAssetsDir(CliOptions options)
        {
            string dir = options.DirectoryPath;
            if (!Directory.Exists(dir))
            {
                Console.WriteLine($"Directory not found: {dir}");
                return;
            }

            SearchOption searchOpt = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            int fileCount = 0;

            foreach (string file in Directory.EnumerateFiles(dir, "*", searchOpt))
            {
                DetectedFileType fileType = FileTypeDetector.DetectFileType(file);
                if (fileType != DetectedFileType.AssetsFile)
                    continue;

                fileCount++;
                Log(options, $"Processing assets file: {file}");

                CliOptions singleOptions = CloneOptionsWithPath(options, assetsPath: file);
                ExportAssets(singleOptions);
            }

            if (fileCount == 0)
                Console.WriteLine($"No assets files found in {dir}");
            else
                Log(options, $"Processed {fileCount} assets file(s).");
        }

        /// <summary>
        /// Clone options but override a specific path for single-file operations.
        /// </summary>
        private static CliOptions CloneOptionsWithPath(CliOptions src, string filePath = "", string bundlePath = "", string assetsPath = "")
        {
            string resolvedBundle = !string.IsNullOrEmpty(bundlePath) ? bundlePath : src.BundlePath;
            string resolvedAssets = !string.IsNullOrEmpty(assetsPath) ? assetsPath : src.AssetsPath;
            // FilePath: 优先使用显式传入的 filePath，其次 bundlePath/assetsPath，最后保留原来的
            string resolvedFile = !string.IsNullOrEmpty(filePath) ? filePath
                                : !string.IsNullOrEmpty(bundlePath) ? bundlePath
                                : !string.IsNullOrEmpty(assetsPath) ? assetsPath
                                : src.FilePath;

            return new CliOptions
            {
                Verb = src.Verb,
                Target = src.Target,
                FilePath = resolvedFile,
                BundlePath = resolvedBundle,
                AssetsPath = resolvedAssets,
                DirectoryPath = src.DirectoryPath,
                OutputDir = src.OutputDir,
                InputDir = src.InputDir,
                EmipPath = src.EmipPath,
                FilterTypes = src.FilterTypes,
                FilterPathIds = src.FilterPathIds,
                FilterName = src.FilterName,
                Format = src.Format,
                TextureFormatOverride = src.TextureFormatOverride,
                CompressMethod = src.CompressMethod,
                KeepNames = src.KeepNames,
                KeepDecomp = src.KeepDecomp,
                ForceDecomp = src.ForceDecomp,
                MemoryDecomp = src.MemoryDecomp,
                Backup = src.Backup,
                NoBackup = src.NoBackup,
                Recursive = src.Recursive,
                DryRun = src.DryRun,
                Verbose = src.Verbose,
                Quiet = src.Quiet,
            };
        }

        #endregion

        #region Import Implementations

        /// <summary>
        /// 單文件模式: 自動偵測 bundle vs assets，派發到對應 Import 方法。
        /// </summary>
        private static void ImportFile(CliOptions options)
        {
            string file = options.FilePath;
            DetectedFileType ft = FileTypeDetector.DetectFileType(file);
            if (ft == DetectedFileType.BundleFile)
                ImportBundle(CloneOptionsWithPath(options, bundlePath: file));
            else if (ft == DetectedFileType.AssetsFile)
                ImportAssets(CloneOptionsWithPath(options, assetsPath: file));
            else
                Console.WriteLine($"Cannot determine file type (not a bundle or assets file): {file}");
        }

        /// <summary>
        /// 目錄批量模式: 掃描目錄，自動偵測每個文件並派發。
        /// 合併了原先的 ImportBundleDir + ImportAssetsDir。
        /// </summary>
        private static void ImportDir(CliOptions options)
        {
            string dir = options.DirectoryPath;
            if (!Directory.Exists(dir))
            {
                Console.WriteLine($"Directory not found: {dir}");
                return;
            }

            string inputDir = options.InputDir;
            if (!Directory.Exists(inputDir))
            {
                Console.WriteLine($"Input directory not found: {inputDir}");
                return;
            }

            SearchOption searchOpt = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            int fileCount = 0;

            foreach (string file in Directory.EnumerateFiles(dir, "*", searchOpt))
            {
                DetectedFileType ft = FileTypeDetector.DetectFileType(file);
                if (ft == DetectedFileType.BundleFile)
                {
                    fileCount++;
                    Log(options, $"Processing bundle: {file}");
                    ImportBundle(CloneOptionsWithPath(options, bundlePath: file));
                }
                else if (ft == DetectedFileType.AssetsFile)
                {
                    fileCount++;
                    Log(options, $"Processing assets: {file}");
                    ImportAssets(CloneOptionsWithPath(options, assetsPath: file));
                }
            }

            if (fileCount == 0)
                Console.WriteLine($"No bundle or assets files found in {dir}");
            else
                Log(options, $"Processed {fileCount} file(s).");
        }

        /// <summary>
        /// Try to find an import file in the input directory that matches a given asset.
        /// Matching pattern: the file ends with "-{assetsFileName}-{PathID}.{ext}"
        /// This mirrors the GUI's ImportBatch matching logic.
        /// </summary>
        private static string? FindMatchingImportFile(string inputDir, AssetContainer cont, string assetsFileName)
        {
            string suffix = $"-{assetsFileName}-{cont.PathId}";

            foreach (string file in Directory.EnumerateFiles(inputDir))
            {
                string nameNoExt = Path.GetFileNameWithoutExtension(file);
                if (nameNoExt.EndsWith(suffix))
                    return file;
            }
            return null;
        }

        /// <summary>
        /// Represents a streaming range in a .resS entry that has been freed (texture converted from streaming to inline).
        /// </summary>
        private struct FreedStreamingRange
        {
            public string ResEntryName; // e.g., "CAB-xxx.resS"
            public long Offset;
            public long Size;
        }

        /// <summary>
        /// Import a single file into an asset, returning the replacer. Supports raw/dump/json based on file extension.
        /// </summary>
        private static AssetsReplacer? ImportSingleAsset(
            AssetWorkspace workspace, AssetContainer cont, string importFilePath, CliOptions options,
            List<FreedStreamingRange>? freedRanges = null)
        {
            try
            {
                AssetImportExport importer = new AssetImportExport();
                string ext = Path.GetExtension(importFilePath).ToLowerInvariant();

                byte[]? bytes;

                if (ext == ".dat")
                {
                    // Raw import
                    using FileStream fs = File.OpenRead(importFilePath);
                    bytes = importer.ImportRawAsset(fs);
                }
                else if (ext == ".json")
                {
                    // JSON import
                    AssetTypeTemplateField tempField = workspace.GetTemplateField(cont);
                    using FileStream fs = File.OpenRead(importFilePath);
                    using StreamReader sr = new StreamReader(fs);
                    bytes = importer.ImportJsonAsset(tempField, sr, out string? exceptionMessage);
                    if (bytes == null)
                    {
                        Console.WriteLine($"  Error importing {Path.GetFileName(importFilePath)}: {exceptionMessage}");
                        return null;
                    }
                }
                else if (ext == ".txt")
                {
                    // Could be dump format or TextAsset raw data - try dump first
                    using FileStream fs = File.OpenRead(importFilePath);
                    using StreamReader sr = new StreamReader(fs);

                    // Peek first line to check if it looks like dump format (starts with "0 " or "1 ")
                    string? firstLine = sr.ReadLine();
                    fs.Position = 0;
                    sr.DiscardBufferedData();

                    if (firstLine != null && firstLine.Length >= 2 && (firstLine[0] == '0' || firstLine[0] == '1') && firstLine[1] == ' ')
                    {
                        bytes = importer.ImportTextAsset(new StreamReader(fs), out string? exceptionMessage);
                        if (bytes == null)
                        {
                            Console.WriteLine($"  Error importing dump {Path.GetFileName(importFilePath)}: {exceptionMessage}");
                            return null;
                        }
                    }
                    else
                    {
                        // Treat as raw TextAsset data
                        bytes = File.ReadAllBytes(importFilePath);
                        if (cont.ClassId == (int)AssetClassID.TextAsset)
                        {
                            // For TextAsset: wrap bytes into the m_Script field
                            AssetTypeValueField? baseField = workspace.GetBaseField(cont);
                            if (baseField != null)
                            {
                                baseField["m_Script"].AsByteArray = bytes;
                                bytes = baseField.WriteToByteArray();
                            }
                        }
                    }
                }
                else if (ext == ".png" || ext == ".tga")
                {
                    // PNG/TGA import for Texture2D: encode with original format (or --tex-format override)
                    if (cont.ClassId != (int)AssetClassID.Texture2D)
                    {
                        Console.WriteLine($"  Error: {Path.GetFileName(importFilePath)} is an image but PathID {cont.PathId} is not a Texture2D asset");
                        return null;
                    }

                    AssetTypeTemplateField textureTemp = workspace.GetTemplateField(cont);
                    AssetTypeTemplateField? imageDataTemp = textureTemp.Children.FirstOrDefault(f => f.Name == "image data");
                    if (imageDataTemp != null)
                        imageDataTemp.ValueType = AssetValueType.ByteArray;

                    AssetTypeTemplateField? platformBlobTemp = textureTemp.Children.FirstOrDefault(f => f.Name == "m_PlatformBlob");
                    if (platformBlobTemp != null)
                        platformBlobTemp.Children[0].ValueType = AssetValueType.ByteArray;

                    AssetTypeValueField baseField = textureTemp.MakeValue(cont.FileReader, cont.FilePosition);

                    // Determine target texture format: --tex-format override, or keep original
                    TextureFormat origFmt = (TextureFormat)baseField["m_TextureFormat"].AsInt;
                    TextureFormat targetFmt = origFmt;

                    if (!string.IsNullOrEmpty(options.TextureFormatOverride))
                    {
                        if (Enum.TryParse<TextureFormat>(options.TextureFormatOverride, true, out TextureFormat parsedFmt))
                        {
                            targetFmt = parsedFmt;
                        }
                        else
                        {
                            Console.WriteLine($"  Warning: Unknown texture format '{options.TextureFormatOverride}', keeping original {origFmt}");
                        }
                    }

                    using Image<Rgba32> image = Image.Load<Rgba32>(importFilePath);
                    image.Mutate(i => i.Flip(FlipMode.Vertical));

                    int width = image.Width;
                    int height = image.Height;

                    // Calculate mip count (same logic as GUI)
                    int origWidth = baseField["m_Width"].AsInt;
                    int origHeight = baseField["m_Height"].AsInt;
                    int mips = 1;
                    if (width == origWidth && height == origHeight)
                    {
                        mips = baseField["m_MipCount"].IsDummy ? 1 : baseField["m_MipCount"].AsInt;
                    }

                    // Get platform blob for Switch deswizzle
                    byte[]? platformBlob = null;
                    AssetTypeValueField pbField = baseField["m_PlatformBlob"];
                    if (!pbField.IsDummy)
                        platformBlob = pbField["Array"].AsByteArray;

                    uint platform = cont.FileInstance.file.Metadata.TargetPlatform;

                    // Try encoding via TexturePlugin.dll (reflection) — supports all formats
                    byte[]? encData = TryEncodeViaTexturePlugin(
                        importFilePath, image, targetFmt, width, height, ref mips, platform, platformBlob, options);

                    if (encData == null)
                    {
                        // Fallback: use RGBA32 uncompressed
                        LogVerbose(options, $"  Encoding failed for {targetFmt}, falling back to RGBA32");
                        targetFmt = TextureFormat.RGBA32;
                        mips = 1;
                        encData = new byte[width * height * 4];
                        image.CopyPixelDataTo(encData);
                    }

                    // Update texture metadata
                    baseField["m_Width"].AsInt = width;
                    baseField["m_Height"].AsInt = height;
                    baseField["m_TextureFormat"].AsInt = (int)targetFmt;
                    baseField["m_CompleteImageSize"].AsInt = encData.Length;

                    if (!baseField["m_MipCount"].IsDummy)
                        baseField["m_MipCount"].AsInt = mips;

                    // Record old streaming data before clearing (for .resS cleanup)
                    AssetTypeValueField m_StreamData = baseField["m_StreamData"];
                    string oldStreamPath = m_StreamData["path"].AsString;
                    long oldStreamSize = m_StreamData["size"].AsUInt;
                    long oldStreamOffset = m_StreamData["offset"].AsLong;

                    if (freedRanges != null && !string.IsNullOrEmpty(oldStreamPath) && oldStreamSize > 0)
                    {
                        // Extract the .resS entry name from the archive path
                        // Format: "archive:/CAB-xxx/CAB-xxx.resS" -> "CAB-xxx.resS"
                        string resEntryName = oldStreamPath;
                        int lastSlash = oldStreamPath.LastIndexOf('/');
                        if (lastSlash >= 0)
                            resEntryName = oldStreamPath.Substring(lastSlash + 1);

                        freedRanges.Add(new FreedStreamingRange
                        {
                            ResEntryName = resEntryName,
                            Offset = oldStreamOffset,
                            Size = oldStreamSize
                        });
                    }

                    // Clear streaming data so the image data is stored inline
                    m_StreamData["offset"].AsInt = 0;
                    m_StreamData["size"].AsInt = 0;
                    m_StreamData["path"].AsString = "";

                    // Set image data
                    AssetTypeValueField imageDataField = baseField["image data"];
                    imageDataField.Value.ValueType = AssetValueType.ByteArray;
                    imageDataField.TemplateField.ValueType = AssetValueType.ByteArray;
                    imageDataField.AsByteArray = encData;

                    bytes = baseField.WriteToByteArray();

                    LogVerbose(options, $"  Texture2D import: {width}x{height} {targetFmt} ({encData.Length} bytes)");
                }
                else if (ext == ".otf" || ext == ".ttf")
                {
                    // Font import: replace m_FontData in the Font asset
                    if (cont.ClassId != (int)AssetClassID.Font)
                    {
                        Console.WriteLine($"  Error: {Path.GetFileName(importFilePath)} is a font file but PathID {cont.PathId} is not a Font asset");
                        return null;
                    }

                    AssetTypeTemplateField fontTemp = workspace.GetTemplateField(cont);
                    AssetTypeTemplateField? fontData = fontTemp.Children.FirstOrDefault(f => f.Name == "m_FontData");
                    if (fontData != null)
                        fontData.Children[0].ValueType = AssetValueType.ByteArray;

                    AssetTypeValueField baseField = fontTemp.MakeValue(cont.FileReader, cont.FilePosition);
                    byte[] fontBytes = File.ReadAllBytes(importFilePath);
                    baseField["m_FontData.Array"].AsByteArray = fontBytes;
                    bytes = baseField.WriteToByteArray();
                }
                else
                {
                    // Unknown extension — for TextAsset, treat as raw text data (like .txt);
                    // for other types, treat as raw binary dump.
                    if (cont.ClassId == (int)AssetClassID.TextAsset)
                    {
                        byte[] rawBytes = File.ReadAllBytes(importFilePath);
                        AssetTypeValueField? baseField = workspace.GetBaseField(cont);
                        if (baseField != null)
                        {
                            baseField["m_Script"].AsByteArray = rawBytes;
                            bytes = baseField.WriteToByteArray();
                        }
                        else
                        {
                            using FileStream fs = File.OpenRead(importFilePath);
                            bytes = importer.ImportRawAsset(fs);
                        }
                    }
                    else
                    {
                        // Unknown extension, unknown type - treat as raw
                        using FileStream fs = File.OpenRead(importFilePath);
                        bytes = importer.ImportRawAsset(fs);
                    }
                }

                if (bytes != null)
                {
                    return AssetImportExport.CreateAssetReplacer(cont, bytes);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  Error importing {Path.GetFileName(importFilePath)}: {ex.Message}");
                LogVerbose(options, $"  Stack: {ex.StackTrace}");
            }
            return null;
        }

        /// <summary>
        /// Core import logic: scan input directory for files matching assets in the given AssetsFileInstance,
        /// create replacers for each match, and write the modified assets file.
        /// Returns (matchCount, replacersList) for use by both assets and bundle import.
        /// </summary>
        private static (int matchCount, List<AssetsReplacer> replacers, List<FreedStreamingRange> freedRanges) ImportIntoAssetsFile(
            AssetWorkspace workspace,
            AssetsFileInstance fileInst,
            string inputDir,
            CliOptions options)
        {
            List<AssetContainer> allAssets = workspace.LoadedAssets.Values
                .Where(c => c.FileInstance == fileInst)
                .ToList();

            List<AssetContainer> filtered = FilterAssets(workspace, allAssets, options);
            string assetsFileName = Path.GetFileName(fileInst.path);

            int matchCount = 0;
            List<AssetsReplacer> replacers = new List<AssetsReplacer>();
            List<FreedStreamingRange> freedRanges = new List<FreedStreamingRange>();

            foreach (AssetContainer cont in filtered)
            {
                // GUI-compatible matching: file ends with -{assetsFileName}-{PathID}.{ext}
                string matchSuffix = $"-{assetsFileName}-{cont.PathId}";
                string? importFile = null;

                foreach (string file in Directory.EnumerateFiles(inputDir))
                {
                    string fileNameNoExt = Path.GetFileNameWithoutExtension(file);
                    if (fileNameNoExt.EndsWith(matchSuffix))
                    {
                        importFile = file;
                        break;
                    }
                }

                if (importFile == null)
                    continue;

                if (options.DryRun)
                {
                    Log(options, $"  [dry-run] Would import: {Path.GetFileName(importFile)} -> PathID {cont.PathId}");
                    matchCount++;
                    continue;
                }

                LogVerbose(options, $"  Importing {Path.GetFileName(importFile)} -> PathID {cont.PathId}...");
                AssetsReplacer? replacer = ImportSingleAsset(workspace, cont, importFile, options, freedRanges);
                if (replacer != null)
                {
                    replacers.Add(replacer);
                    workspace.AddReplacer(fileInst, replacer, new MemoryStream(GetReplacerBytes(replacer)));
                    matchCount++;
                }
            }

            return (matchCount, replacers, freedRanges);
        }

        /// <summary>
        /// Extract bytes from an AssetsReplacer for use as preview data.
        /// </summary>
        private static byte[] GetReplacerBytes(AssetsReplacer replacer)
        {
            using MemoryStream ms = new MemoryStream();
            AssetsFileWriter w = new AssetsFileWriter(ms);
            replacer.Write(w);
            return ms.ToArray();
        }

        /// <summary>
        /// Write the modified assets file to disk, handling backup logic.
        /// </summary>
        private static void WriteModifiedAssetsFile(
            AssetsFileInstance fileInst, List<AssetsReplacer> replacers, CliOptions options)
        {
            string origPath = fileInst.path;

            // Backup
            if (options.Backup)
            {
                string? bakFile = GetNextBackup(origPath);
                if (bakFile != null)
                {
                    File.Copy(origPath, bakFile);
                    Log(options, $"  Backup: {Path.GetFileName(bakFile)}");
                }
            }

            // Write to temp file, then swap
            string tempFile = origPath + ".tmp";
            try
            {
                using (FileStream fs = File.Open(tempFile, FileMode.Create))
                using (AssetsFileWriter w = new AssetsFileWriter(fs))
                {
                    fileInst.file.Write(w, 0, replacers);
                }

                // Close original reader before overwriting
                fileInst.file.Reader.Close();
                File.Delete(origPath);
                File.Move(tempFile, origPath);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  Error writing {origPath}: {ex.Message}");
                LogVerbose(options, $"  Stack: {ex.StackTrace}");
                // Try to clean up temp file
                if (File.Exists(tempFile))
                    File.Delete(tempFile);
            }
        }

        private static void ImportAssets(CliOptions options)
        {
            string file = options.AssetsPath;
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return;
            }

            string inputDir = options.InputDir;
            if (!Directory.Exists(inputDir))
            {
                Console.WriteLine($"Input directory not found: {inputDir}");
                return;
            }

            AssetsManager am = assetsManager!;
            AssetsFileInstance fileInst = am.LoadAssetsFile(file, true);
            LoadClassDatabase(am, fileInst, options);

            AssetWorkspace workspace = new AssetWorkspace(am, false);
            workspace.LoadAssetsFile(fileInst, false);

            var (matchCount, replacers, _) = ImportIntoAssetsFile(workspace, fileInst, inputDir, options);

            if (matchCount == 0)
            {
                Console.WriteLine($"No matching import files found for {Path.GetFileName(file)}.");
                return;
            }

            if (!options.DryRun)
            {
                WriteModifiedAssetsFile(fileInst, replacers, options);
                Log(options, $"Done. Imported {matchCount} asset(s) into {Path.GetFileName(file)}.");
            }
            else
            {
                Log(options, $"[dry-run] Would import {matchCount} asset(s) into {Path.GetFileName(file)}.");
            }
        }

        private static void ImportAssetsDir(CliOptions options)
        {
            string dir = options.DirectoryPath;
            if (!Directory.Exists(dir))
            {
                Console.WriteLine($"Directory not found: {dir}");
                return;
            }

            string inputDir = options.InputDir;
            if (!Directory.Exists(inputDir))
            {
                Console.WriteLine($"Input directory not found: {inputDir}");
                return;
            }

            SearchOption searchOpt = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            int fileCount = 0;
            int totalImported = 0;

            foreach (string file in Directory.EnumerateFiles(dir, "*", searchOpt))
            {
                DetectedFileType fileType = FileTypeDetector.DetectFileType(file);
                if (fileType != DetectedFileType.AssetsFile)
                    continue;

                fileCount++;
                Log(options, $"Processing assets file: {file}");

                CliOptions singleOptions = CloneOptionsWithPath(options, assetsPath: file);
                ImportAssets(singleOptions);
            }

            if (fileCount == 0)
                Console.WriteLine($"No assets files found in {dir}");
            else
                Log(options, $"Processed {fileCount} assets file(s).");
        }

        private static void ImportBundle(CliOptions options)
        {
            string file = options.BundlePath;
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return;
            }

            string inputDir = options.InputDir;
            if (!Directory.Exists(inputDir))
            {
                Console.WriteLine($"Input directory not found: {inputDir}");
                return;
            }

            // Backup before modifying
            if (options.Backup)
            {
                string? bakFile = GetNextBackup(file);
                if (bakFile != null)
                {
                    File.Copy(file, bakFile);
                    Log(options, $"Backup: {Path.GetFileName(bakFile)}");
                }
            }

            string? decompFile = GetDecompFilePath(file, options);

            AssetsManager am = assetsManager!;

            // Load bundle via AssetsManager for proper parentBundle linkage
            BundleFileInstance bundleInst;
            AssetBundleFile bun;

            // Check if cached .decomp already exists (reuse unless --fd)
            if (decompFile != null && File.Exists(decompFile))
            {
                LogVerbose(options, $"Reusing cached decomp: {decompFile}");
                Stream cachedStream = File.Open(decompFile, FileMode.Open, FileAccess.Read);
                bundleInst = am.LoadBundleFile(cachedStream, file, false);
                bun = bundleInst.file;
            }
            else
            {
                Log(options, $"Decompressing {Path.GetFileName(file)}...");
                bundleInst = am.LoadBundleFile(file, false);
                bun = bundleInst.file;

                // Decompress if needed
                if (AssetBundleUtil.IsBundleDataCompressed(bun))
                {
                    Stream decompStream;
                    if (decompFile != null)
                        decompStream = File.Open(decompFile, FileMode.Create, FileAccess.ReadWrite);
                    else
                        decompStream = new MemoryStream();

                    AssetsFileWriter dw = new AssetsFileWriter(decompStream);
                    bun.Unpack(dw);
                    decompStream.Position = 0;

                    am.UnloadBundleFile(bundleInst);
                    bundleInst = am.LoadBundleFile(decompStream, file, false);
                    bun = bundleInst.file;
                }
            }

            List<BundleReplacer> bundleReplacers = new List<BundleReplacer>();
            List<Stream> openStreams = new List<Stream>();
            List<FreedStreamingRange> allFreedRanges = new List<FreedStreamingRange>();
            int totalImported = 0;

            int entryCount = bun.BlockAndDirInfo.DirectoryInfos.Length;
            for (int i = 0; i < entryCount; i++)
            {
                string entryName = bun.BlockAndDirInfo.DirectoryInfos[i].Name;

                // Load entry as assets file with parentBundle
                AssetsFileInstance? fileInst;
                try
                {
                    fileInst = am.LoadAssetsFileFromBundle(bundleInst, i, false);
                    if (fileInst.file.AssetInfos == null || fileInst.file.AssetInfos.Count == 0)
                    {
                        LogVerbose(options, $"  Skipping non-assets entry: {entryName}");
                        continue;
                    }
                }
                catch
                {
                    LogVerbose(options, $"  Skipping non-assets entry: {entryName}");
                    continue;
                }

                LoadClassDatabase(am, fileInst, options);

                AssetWorkspace workspace = new AssetWorkspace(am, true);
                workspace.LoadAssetsFile(fileInst, false);

                var (matchCount, replacers, freedRanges) = ImportIntoAssetsFile(workspace, fileInst, inputDir, options);
                allFreedRanges.AddRange(freedRanges);

                if (matchCount > 0 && !options.DryRun)
                {
                    // Write modified assets data to memory
                    MemoryStream modifiedStream = new MemoryStream();
                    AssetsFileWriter writer = new AssetsFileWriter(modifiedStream);
                    fileInst.file.Write(writer, 0, replacers);
                    modifiedStream.Position = 0;

                    // Create bundle replacer from the modified entry
                    BundleReplacer bundleReplacer = new BundleReplacerFromStream(
                        entryName, entryName, true, modifiedStream, 0, modifiedStream.Length);
                    bundleReplacers.Add(bundleReplacer);
                    openStreams.Add(modifiedStream);

                    totalImported += matchCount;
                }
                else if (matchCount > 0)
                {
                    totalImported += matchCount;
                }
            }

            // Clean up .resS entries: zero out freed streaming ranges so they compress away
            if (allFreedRanges.Count > 0 && !options.DryRun)
            {
                // Group freed ranges by .resS entry name
                var rangesByEntry = allFreedRanges
                    .GroupBy(r => r.ResEntryName)
                    .ToDictionary(g => g.Key, g => g.ToList());

                for (int i = 0; i < entryCount; i++)
                {
                    string entryName = bun.BlockAndDirInfo.DirectoryInfos[i].Name;
                    if (!rangesByEntry.ContainsKey(entryName))
                        continue;

                    var ranges = rangesByEntry[entryName];

                    // Read the .resS entry data from the decompressed bundle
                    long entryOffset = bun.BlockAndDirInfo.DirectoryInfos[i].Offset;
                    long entrySize = bun.BlockAndDirInfo.DirectoryInfos[i].DecompressedSize;

                    byte[] resSData = new byte[entrySize];
                    var dataReader = bun.DataReader;
                    dataReader.Position = entryOffset;
                    dataReader.Read(resSData, 0, (int)entrySize);

                    // Zero out all freed ranges
                    long totalZeroed = 0;
                    foreach (var range in ranges)
                    {
                        long start = range.Offset;
                        long end = Math.Min(start + range.Size, entrySize);
                        if (start < entrySize && start >= 0)
                        {
                            Array.Clear(resSData, (int)start, (int)(end - start));
                            totalZeroed += end - start;
                        }
                    }

                    if (totalZeroed > 0)
                    {
                        LogVerbose(options, $"  Zeroed {totalZeroed} bytes of freed streaming data in {entryName}");
                        MemoryStream resSStream = new MemoryStream(resSData);
                        BundleReplacer resSReplacer = new BundleReplacerFromStream(
                            entryName, entryName, true, resSStream, 0, resSStream.Length);
                        bundleReplacers.Add(resSReplacer);
                        openStreams.Add(resSStream);
                    }
                }
            }

            if (totalImported == 0)
            {
                Console.WriteLine($"No matching import files found for {Path.GetFileName(file)}.");
                am.UnloadBundleFile(bundleInst);
                CleanupDecomp(decompFile, options);
                return;
            }

            if (!options.DryRun)
            {
                // Write modified bundle (uncompressed first), then recompress
                string tempFile = file + ".tmp";
                string tempUncompressed = file + ".tmp.uncompressed";
                try
                {
                    // Step 1: Write uncompressed bundle with replacers
                    using (FileStream fs = File.Open(tempUncompressed, FileMode.Create))
                    using (AssetsFileWriter w = new AssetsFileWriter(fs))
                    {
                        bun.Write(w, bundleReplacers);
                    }

                    // Close everything before recompression
                    foreach (Stream s in openStreams)
                        s.Close();
                    am.UnloadBundleFile(bundleInst);

                    // Step 2: Recompress the bundle (default LZ4, or user-specified --compress)
                    AssetBundleCompressionType compType = options.CompressMethod switch
                    {
                        CliCompressMethod.Lzma => AssetBundleCompressionType.LZMA,
                        CliCompressMethod.None => AssetBundleCompressionType.LZ4,  // default to LZ4
                        _ => AssetBundleCompressionType.LZ4,
                    };

                    Log(options, $"Recompressing with {compType}...");
                    AssetBundleFile uncompressedBun = new AssetBundleFile();
                    using (FileStream readFs = File.OpenRead(tempUncompressed))
                    {
                        AssetsFileReader reader = new AssetsFileReader(readFs);
                        uncompressedBun.Read(reader);

                        using (FileStream writeFs = File.Open(tempFile, FileMode.Create))
                        using (AssetsFileWriter compWriter = new AssetsFileWriter(writeFs))
                        {
                            uncompressedBun.Pack(uncompressedBun.Reader, compWriter, compType);
                        }
                    }
                    uncompressedBun.Close();

                    // Step 3: Swap files
                    File.Delete(tempUncompressed);
                    File.Delete(file);
                    File.Move(tempFile, file);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error writing bundle: {ex.Message}");
                    LogVerbose(options, $"Stack: {ex.StackTrace}");
                    foreach (Stream s in openStreams)
                        s.Close();
                    am.UnloadBundleFile(bundleInst);
                    if (File.Exists(tempFile))
                        File.Delete(tempFile);
                    if (File.Exists(tempUncompressed))
                        File.Delete(tempUncompressed);
                }

                Log(options, $"Done. Imported {totalImported} asset(s) into {Path.GetFileName(file)}.");
            }
            else
            {
                am.UnloadBundleFile(bundleInst);
                Log(options, $"[dry-run] Would import {totalImported} asset(s) into {Path.GetFileName(file)}.");
            }

            CleanupDecomp(decompFile, options);
        }

        private static void ImportBundleDir(CliOptions options)
        {
            string dir = options.DirectoryPath;
            if (!Directory.Exists(dir))
            {
                Console.WriteLine($"Directory not found: {dir}");
                return;
            }

            string inputDir = options.InputDir;
            if (!Directory.Exists(inputDir))
            {
                Console.WriteLine($"Input directory not found: {inputDir}");
                return;
            }

            SearchOption searchOpt = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            int bundleCount = 0;

            foreach (string file in Directory.EnumerateFiles(dir, "*", searchOpt))
            {
                DetectedFileType fileType = FileTypeDetector.DetectFileType(file);
                if (fileType != DetectedFileType.BundleFile)
                    continue;

                bundleCount++;
                Log(options, $"Processing bundle: {file}");

                CliOptions singleOptions = CloneOptionsWithPath(options, bundlePath: file);
                ImportBundle(singleOptions);
            }

            if (bundleCount == 0)
                Console.WriteLine($"No bundle files found in {dir}");
            else
                Log(options, $"Processed {bundleCount} bundle(s).");
        }

        #endregion

        #region Apply / List / Info Implementations

        private static void ApplyEmip(CliOptions options)
        {
            string emipFile = options.EmipPath;
            string rootDir = options.DirectoryPath;

            if (string.IsNullOrEmpty(emipFile))
            {
                Console.WriteLine("Error: -e/--emip is required for apply emip.");
                return;
            }
            if (!File.Exists(emipFile))
            {
                Console.WriteLine($"File not found: {emipFile}");
                return;
            }
            if (string.IsNullOrEmpty(rootDir))
            {
                Console.WriteLine("Error: -d/--directory is required for apply emip.");
                return;
            }
            if (!Directory.Exists(rootDir))
            {
                Console.WriteLine($"Directory not found: {rootDir}");
                return;
            }

            InstallerPackageFile instPkg = new InstallerPackageFile();
            FileStream fs = File.OpenRead(emipFile);
            AssetsFileReader r = new AssetsFileReader(fs);
            instPkg.Read(r, true);

            Log(options, $"Installing emip...");
            Log(options, $"  {instPkg.modName} by {instPkg.modCreators}");
            Log(options, $"  {instPkg.modDescription}");

            foreach (var affectedFile in instPkg.affectedFiles)
            {
                string affectedFileName = Path.GetFileName(affectedFile.path);
                string affectedFilePath = Path.Combine(rootDir, affectedFile.path);

                if (!File.Exists(affectedFilePath))
                {
                    Console.WriteLine($"  Warning: {affectedFilePath} not found, skipping.");
                    continue;
                }

                if (affectedFile.isBundle)
                {
                    string? decompFile = GetDecompFilePath(affectedFilePath, options);
                    string modFile = $"{affectedFilePath}.mod";
                    string? bakFile = GetNextBackup(affectedFilePath);

                    if (bakFile == null)
                        return;

                    Log(options, $"  Decompressing {affectedFileName}...");
                    AssetBundleFile bun = DecompressBundle(affectedFilePath, decompFile);
                    List<BundleReplacer> reps = new List<BundleReplacer>();

                    foreach (var rep in affectedFile.replacers)
                    {
                        var bunRep = (BundleReplacer)rep;
                        if (bunRep is BundleReplacerFromAssets)
                        {
                            string assetName = bunRep.GetOriginalEntryName();
                            var bunRepInf = BundleHelper.GetDirInfo(bun, assetName);
                            long pos = bunRepInf.Offset;
                            bunRep.Init(bun.DataReader, pos, bunRepInf.DecompressedSize);
                        }
                        reps.Add(bunRep);
                    }

                    Log(options, $"  Writing {modFile}...");
                    FileStream mfs = File.Open(modFile, FileMode.Create);
                    AssetsFileWriter mw = new AssetsFileWriter(mfs);
                    bun.Write(mw, reps, instPkg.addedTypes);

                    mfs.Close();
                    bun.Close();

                    Log(options, $"  Swapping mod file...");
                    File.Move(affectedFilePath, bakFile);
                    File.Move(modFile, affectedFilePath);

                    CleanupDecomp(decompFile, options);
                    Log(options, $"  Done: {affectedFileName}");
                }
                else
                {
                    string modFile = $"{affectedFilePath}.mod";
                    string? bakFile = GetNextBackup(affectedFilePath);

                    if (bakFile == null)
                        return;

                    FileStream afs = File.OpenRead(affectedFilePath);
                    AssetsFileReader ar = new AssetsFileReader(afs);
                    AssetsFile assets = new AssetsFile();
                    assets.Read(ar);
                    List<AssetsReplacer> reps = new List<AssetsReplacer>();

                    foreach (var rep in affectedFile.replacers)
                    {
                        var assetsReplacer = (AssetsReplacer)rep;
                        reps.Add(assetsReplacer);
                    }

                    Log(options, $"  Writing {modFile}...");
                    FileStream mfs = File.Open(modFile, FileMode.Create);
                    AssetsFileWriter mw = new AssetsFileWriter(mfs);
                    assets.Write(mw, 0, reps, instPkg.addedTypes);

                    mfs.Close();
                    ar.Close();

                    Log(options, $"  Swapping mod file...");
                    File.Move(affectedFilePath, bakFile);
                    File.Move(modFile, affectedFilePath);

                    Log(options, $"  Done: {affectedFileName}");
                }
            }

            fs.Close();
            Log(options, "EMIP applied successfully.");
        }

        private static int ListBundle(CliOptions options)
        {
            string file = options.BundlePath;
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return 0;
            }

            bool hasAnyFilter = !string.IsNullOrEmpty(options.FilterName)
                             || options.FilterTypes.Count > 0
                             || options.FilterPathIds.Count > 0;

            string? decompFile = GetDecompFilePath(file, options);
            AssetsManager am = assetsManager!;

            BundleFileInstance bundleInst;
            AssetBundleFile bun;

            // Check if cached .decomp already exists (reuse unless --fd)
            if (decompFile != null && File.Exists(decompFile))
            {
                Stream cachedStream = File.Open(decompFile, FileMode.Open, FileAccess.Read);
                bundleInst = am.LoadBundleFile(cachedStream, file, false);
                bun = bundleInst.file;
            }
            else
            {
                bundleInst = am.LoadBundleFile(file, false);
                bun = bundleInst.file;

                if (AssetBundleUtil.IsBundleDataCompressed(bun))
                {
                    Stream decompStream;
                    if (decompFile != null)
                        decompStream = File.Open(decompFile, FileMode.Create, FileAccess.ReadWrite);
                    else
                        decompStream = new MemoryStream();
                    AssetsFileWriter dw = new AssetsFileWriter(decompStream);
                    bun.Unpack(dw);
                    decompStream.Position = 0;
                    am.UnloadBundleFile(bundleInst);
                    bundleInst = am.LoadBundleFile(decompStream, file, false);
                    bun = bundleInst.file;
                }
            }

            int entryCount = bun.BlockAndDirInfo.DirectoryInfos.Length;

            // 先收集所有要输出的行，过滤后整体打印（避免无匹配时打印空标题）
            var rows = new List<string>();
            int totalMatched = 0;

            for (int i = 0; i < entryCount; i++)
            {
                string entryName = bun.BlockAndDirInfo.DirectoryInfos[i].Name;

                AssetsFileInstance? fileInst;
                try
                {
                    fileInst = am.LoadAssetsFileFromBundle(bundleInst, i, false);
                    if (fileInst.file.AssetInfos == null || fileInst.file.AssetInfos.Count == 0)
                        continue;
                }
                catch { continue; }

                LoadClassDatabase(am, fileInst, options);

                AssetWorkspace workspace = new AssetWorkspace(am, true);
                workspace.LoadAssetsFile(fileInst, false);

                List<AssetContainer> allAssets = workspace.LoadedAssets.Values.ToList();
                List<AssetContainer> filtered = FilterAssets(workspace, allAssets, options);

                if (filtered.Count == 0 && hasAnyFilter)
                    continue;

                foreach (AssetContainer cont in filtered.OrderBy(c => c.PathId))
                {
                    AssetNameUtils.GetDisplayNameFast(workspace, cont, false, out string assetName, out string typeName);
                    rows.Add($"{cont.PathId,-12} {entryName,-35} {typeName,-20} {cont.Size,8:N0} {assetName}");
                    totalMatched++;
                }
            }

            am.UnloadBundleFile(bundleInst);
            CleanupDecomp(decompFile, options);

            if (rows.Count > 0)
            {
                Console.WriteLine($"Bundle: {file}");
                Console.WriteLine($"{"PathID",-12} {"Entry",-35} {"Type",-20} {"Size",8} Name");
                Console.WriteLine(new string('-', 100));
                foreach (string row in rows)
                    Console.WriteLine(row);
            }
            else if (!hasAnyFilter)
            {
                Console.WriteLine($"Bundle: {file} (no loadable asset entries)");
            }

            return totalMatched;
        }

        private static int ListAssets(CliOptions options)
        {
            string file = options.AssetsPath;
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return 0;
            }

            bool hasAnyFilter = !string.IsNullOrEmpty(options.FilterName)
                             || options.FilterTypes.Count > 0
                             || options.FilterPathIds.Count > 0;

            AssetsManager am = assetsManager!;
            AssetsFileInstance fileInst = am.LoadAssetsFile(file, true);

            LoadClassDatabase(am, fileInst, options);

            AssetWorkspace workspace = new AssetWorkspace(am, false);
            workspace.LoadAssetsFile(fileInst, false);

            List<AssetContainer> allAssets = workspace.LoadedAssets.Values.ToList();
            List<AssetContainer> filtered = FilterAssets(workspace, allAssets, options);

            // 有过滤且无匹配时静默跳过
            if (filtered.Count == 0 && hasAnyFilter)
                return 0;

            Console.WriteLine($"Assets File: {file} ({filtered.Count} assets)");
            Console.WriteLine($"{"PathID",-12} {"Type",-25} {"Size",10} Name");
            Console.WriteLine(new string('-', 80));

            foreach (AssetContainer cont in filtered.OrderBy(c => c.PathId))
            {
                AssetNameUtils.GetDisplayNameFast(workspace, cont, false, out string assetName, out string typeName);
                Console.WriteLine($"{cont.PathId,-12} {typeName,-25} {cont.Size,10:N0} {assetName}");
            }

            return filtered.Count;
        }

        /// <summary>目录批量 list：自动检测每个文件类型并列出资源。</summary>
        private static void ListDir(CliOptions options)
        {
            string dir = options.DirectoryPath;
            if (!Directory.Exists(dir))
            {
                Console.WriteLine($"Directory not found: {dir}");
                return;
            }

            bool hasFilter = !string.IsNullOrEmpty(options.FilterName)
                          || options.FilterTypes.Count > 0
                          || options.FilterPathIds.Count > 0;

            SearchOption searchOpt = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            int fileCount = 0;
            int matchCount = 0;

            foreach (string file in Directory.EnumerateFiles(dir, "*", searchOpt))
            {
                DetectedFileType ft = FileTypeDetector.DetectFileType(file);
                if (ft == DetectedFileType.BundleFile)
                {
                    var singleOpt = CloneOptionsWithPath(options, bundlePath: file);
                    int n = ListBundle(singleOpt);
                    if (n > 0 || !hasFilter)
                    {
                        fileCount++;
                        matchCount += n;
                        if (n > 0) Console.WriteLine();
                    }
                }
                else if (ft == DetectedFileType.AssetsFile)
                {
                    var singleOpt = CloneOptionsWithPath(options, assetsPath: file);
                    int n = ListAssets(singleOpt);
                    if (n > 0 || !hasFilter)
                    {
                        fileCount++;
                        matchCount += n;
                        Console.WriteLine();
                    }
                }
            }

            if (fileCount == 0)
                Console.WriteLine($"No bundle or assets files{(hasFilter ? " matching filter" : "")} found in {dir}");
            else if (hasFilter)
                Console.WriteLine($"Total: {matchCount} matching asset(s) across {fileCount} file(s).");
        }

        private static void InfoBundle(CliOptions options)
        {
            string file = options.BundlePath;
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return;
            }

            AssetBundleFile bun = new AssetBundleFile();
            using Stream fs = File.OpenRead(file);
            AssetsFileReader r = new AssetsFileReader(fs);
            bun.Read(r);

            Console.WriteLine($"Bundle File: {Path.GetFileName(file)}");
            Console.WriteLine($"  Signature:    {bun.Header.Signature}");
            Console.WriteLine($"  Version:      {bun.Header.Version}");
            Console.WriteLine($"  Engine:       {bun.Header.EngineVersion}");
            Console.WriteLine($"  Compression:  {bun.Header.GetCompressionType()}");
            Console.WriteLine($"  File Size:    {new FileInfo(file).Length:N0} bytes");
            Console.WriteLine($"  Entries:      {bun.BlockAndDirInfo.DirectoryInfos.Length}");

            bun.Close();
        }

        private static void InfoAssets(CliOptions options)
        {
            string file = options.AssetsPath;
            if (!File.Exists(file))
            {
                Console.WriteLine($"File not found: {file}");
                return;
            }

            AssetsManager am = assetsManager!;
            AssetsFileInstance fileInst = am.LoadAssetsFile(file, true);

            LoadClassDatabase(am, fileInst, options);

            AssetsFile af = fileInst.file;
            Console.WriteLine($"Assets File: {Path.GetFileName(file)}");
            Console.WriteLine($"  Unity Version:  {af.Metadata.UnityVersion}");
            Console.WriteLine($"  Format Version: {af.Header.Version}");
            Console.WriteLine($"  File Size:      {af.Header.FileSize:N0} bytes");
            Console.WriteLine($"  Asset Count:    {af.AssetInfos.Count}");
            Console.WriteLine($"  TypeTree:       {(af.Metadata.TypeTreeEnabled ? "Yes" : "No")}");
            Console.WriteLine($"  Externals:      {af.Metadata.Externals.Count}");

            if (af.Metadata.Externals.Count > 0 && options.Verbose)
            {
                Console.WriteLine("  Dependencies:");
                for (int i = 0; i < af.Metadata.Externals.Count; i++)
                {
                    Console.WriteLine($"    [{i}] {af.Metadata.Externals[i].PathName}");
                }
            }
        }

        /// <summary>目录批量 info：自动检测每个文件类型并打印概要信息。</summary>
        private static void InfoDir(CliOptions options)
        {
            string dir = options.DirectoryPath;
            if (!Directory.Exists(dir))
            {
                Console.WriteLine($"Directory not found: {dir}");
                return;
            }

            SearchOption searchOpt = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            int fileCount = 0;

            foreach (string file in Directory.EnumerateFiles(dir, "*", searchOpt))
            {
                DetectedFileType ft = FileTypeDetector.DetectFileType(file);
                if (ft == DetectedFileType.BundleFile)
                {
                    fileCount++;
                    InfoBundle(CloneOptionsWithPath(options, bundlePath: file));
                    Console.WriteLine();
                }
                else if (ft == DetectedFileType.AssetsFile)
                {
                    fileCount++;
                    InfoAssets(CloneOptionsWithPath(options, assetsPath: file));
                    Console.WriteLine();
                }
            }

            if (fileCount == 0)
                Console.WriteLine($"No bundle or assets files found in {dir}");
        }

        #endregion

        #region Legacy Commands (backward compat)

        /// <summary>
        /// 旧版命令实现，保持完全兼容。
        /// 旧版命令使用位置参数和 -flag 风格，不经过 CliOptions 的新式验证。
        /// </summary>
        internal static class LegacyCommands
        {
            private static string GetMainFileName(string[] args)
            {
                for (int i = 1; i < args.Length; i++)
                {
                    if (!args[i].StartsWith("-"))
                        return args[i];
                }
                return string.Empty;
            }

            private static HashSet<string> GetFlags(string[] args)
            {
                HashSet<string> flags = new HashSet<string>();
                for (int i = 1; i < args.Length; i++)
                {
                    if (args[i].StartsWith("-"))
                        flags.Add(args[i]);
                }
                return flags;
            }

            public static void BatchExportBundle(string[] args, CliOptions options)
            {
                string exportDirectory = GetMainFileName(args);
                if (!Directory.Exists(exportDirectory))
                {
                    Console.WriteLine("Directory does not exist!");
                    return;
                }

                HashSet<string> flags = GetFlags(args);
                foreach (string file in Directory.EnumerateFiles(exportDirectory))
                {
                    string decompFile = $"{file}.decomp";

                    if (flags.Contains("-md"))
                        decompFile = null;

                    if (!File.Exists(file))
                    {
                        Console.WriteLine($"File {file} does not exist!");
                        return;
                    }

                    DetectedFileType fileType = FileTypeDetector.DetectFileType(file);
                    if (fileType != DetectedFileType.BundleFile)
                    {
                        continue;
                    }

                    Console.WriteLine($"Decompressing {file}...");
                    AssetBundleFile bun = DecompressBundle(file, decompFile);

                    int entryCount = bun.BlockAndDirInfo.DirectoryInfos.Length;
                    for (int i = 0; i < entryCount; i++)
                    {
                        string name = bun.BlockAndDirInfo.DirectoryInfos[i].Name;
                        byte[] data = BundleHelper.LoadAssetDataFromBundle(bun, i);
                        string outName;
                        if (flags.Contains("-keepnames"))
                            outName = Path.Combine(exportDirectory, name);
                        else
                            outName = Path.Combine(exportDirectory, $"{Path.GetFileName(file)}_{name}");
                        Console.WriteLine($"Exporting {outName}...");
                        File.WriteAllBytes(outName, data);
                    }

                    bun.Close();

                    if (!flags.Contains("-kd") && !flags.Contains("-md") && File.Exists(decompFile))
                        File.Delete(decompFile);

                    Console.WriteLine("Done.");
                }
            }

            public static void BatchImportBundle(string[] args, CliOptions options)
            {
                string importDirectory = GetMainFileName(args);
                if (!Directory.Exists(importDirectory))
                {
                    Console.WriteLine("Directory does not exist!");
                    return;
                }

                HashSet<string> flags = GetFlags(args);
                foreach (string file in Directory.EnumerateFiles(importDirectory))
                {
                    string decompFile = $"{file}.decomp";

                    if (flags.Contains("-md"))
                        decompFile = null;

                    if (!File.Exists(file))
                    {
                        Console.WriteLine($"File {file} does not exist!");
                        return;
                    }

                    DetectedFileType fileType = FileTypeDetector.DetectFileType(file);
                    if (fileType != DetectedFileType.BundleFile)
                    {
                        continue;
                    }

                    Console.WriteLine($"Decompressing {file} to {decompFile}...");
                    AssetBundleFile bun = DecompressBundle(file, decompFile);

                    List<BundleReplacer> reps = new List<BundleReplacer>();
                    List<Stream> streams = new List<Stream>();

                    int entryCount = bun.BlockAndDirInfo.DirectoryInfos.Length;
                    for (int i = 0; i < entryCount; i++)
                    {
                        string name = bun.BlockAndDirInfo.DirectoryInfos[i].Name;
                        string matchName = Path.Combine(importDirectory, $"{Path.GetFileName(file)}_{name}");

                        if (File.Exists(matchName))
                        {
                            FileStream fs = File.OpenRead(matchName);
                            long length = fs.Length;
                            reps.Add(new BundleReplacerFromStream(name, name, true, fs, 0, length));
                            streams.Add(fs);
                            Console.WriteLine($"Importing {matchName}...");
                        }
                    }

                    byte[] data;
                    using (MemoryStream ms = new MemoryStream())
                    using (AssetsFileWriter w = new AssetsFileWriter(ms))
                    {
                        bun.Write(w, reps);
                        data = ms.ToArray();
                    }
                    Console.WriteLine($"Writing changes to {file}...");

                    foreach (Stream stream in streams)
                        stream.Close();

                    bun.Close();

                    File.WriteAllBytes(file, data);

                    if (!flags.Contains("-kd") && !flags.Contains("-md") && File.Exists(decompFile))
                        File.Delete(decompFile);

                    Console.WriteLine("Done.");
                }
            }

            public static void ApplyEmip(string[] args, CliOptions options)
            {
                HashSet<string> flags = GetFlags(args);
                string emipFile = args[1];
                string rootDir = args[2];

                if (!File.Exists(emipFile))
                {
                    Console.WriteLine($"File {emipFile} does not exist!");
                    return;
                }

                InstallerPackageFile instPkg = new InstallerPackageFile();
                FileStream fs = File.OpenRead(emipFile);
                AssetsFileReader r = new AssetsFileReader(fs);
                instPkg.Read(r, true);

                Console.WriteLine($"Installing emip...");
                Console.WriteLine($"{instPkg.modName} by {instPkg.modCreators}");
                Console.WriteLine(instPkg.modDescription);

                foreach (var affectedFile in instPkg.affectedFiles)
                {
                    string affectedFileName = Path.GetFileName(affectedFile.path);
                    string affectedFilePath = Path.Combine(rootDir, affectedFile.path);

                    if (affectedFile.isBundle)
                    {
                        string decompFile = $"{affectedFilePath}.decomp";
                        string modFile = $"{affectedFilePath}.mod";
                        string bakFile = GetNextBackup(affectedFilePath);

                        if (bakFile == null)
                            return;

                        if (flags.Contains("-md"))
                            decompFile = null;

                        Console.WriteLine($"Decompressing {affectedFileName} to {decompFile ?? "memory"}...");
                        AssetBundleFile bun = DecompressBundle(affectedFilePath, decompFile);
                        List<BundleReplacer> reps = new List<BundleReplacer>();

                        foreach (var rep in affectedFile.replacers)
                        {
                            var bunRep = (BundleReplacer)rep;
                            if (bunRep is BundleReplacerFromAssets)
                            {
                                string assetName = bunRep.GetOriginalEntryName();
                                var bunRepInf = BundleHelper.GetDirInfo(bun, assetName);
                                long pos = bunRepInf.Offset;
                                bunRep.Init(bun.DataReader, pos, bunRepInf.DecompressedSize);
                            }
                            reps.Add(bunRep);
                        }

                        Console.WriteLine($"Writing {modFile}...");
                        FileStream mfs = File.Open(modFile, FileMode.Create);
                        AssetsFileWriter mw = new AssetsFileWriter(mfs);
                        bun.Write(mw, reps, instPkg.addedTypes);

                        mfs.Close();
                        bun.Close();

                        Console.WriteLine($"Swapping mod file...");
                        File.Move(affectedFilePath, bakFile);
                        File.Move(modFile, affectedFilePath);

                        if (!flags.Contains("-kd") && !flags.Contains("-md") && File.Exists(decompFile))
                            File.Delete(decompFile);

                        Console.WriteLine($"Done.");
                    }
                    else
                    {
                        string modFile = $"{affectedFilePath}.mod";
                        string bakFile = GetNextBackup(affectedFilePath);

                        if (bakFile == null)
                            return;

                        FileStream afs = File.OpenRead(affectedFilePath);
                        AssetsFileReader ar = new AssetsFileReader(afs);
                        AssetsFile assets = new AssetsFile();
                        assets.Read(ar);
                        List<AssetsReplacer> reps = new List<AssetsReplacer>();

                        foreach (var rep in affectedFile.replacers)
                        {
                            var assetsReplacer = (AssetsReplacer)rep;
                            reps.Add(assetsReplacer);
                        }

                        Console.WriteLine($"Writing {modFile}...");
                        FileStream mfs = File.Open(modFile, FileMode.Create);
                        AssetsFileWriter mw = new AssetsFileWriter(mfs);
                        assets.Write(mw, 0, reps, instPkg.addedTypes);

                        mfs.Close();
                        ar.Close();

                        Console.WriteLine($"Swapping mod file...");
                        File.Move(affectedFilePath, bakFile);
                        File.Move(modFile, affectedFilePath);

                        Console.WriteLine($"Done.");
                    }
                }
            }
        }

        #endregion
    }
}