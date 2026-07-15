using System;
using System.Collections.Generic;
using System.IO;
using AssetsTools.NET.Texture;

namespace UABEAvalonia.Cli
{
    /// <summary>
    /// CLI 参数解析器，将 string[] args 转换为 CliOptions
    /// 支持新版二级命令 (export bundle -b ...) 和旧版命令 (batchexportbundle ...)
    /// </summary>
    public static class CliParser
    {
        public static CliOptions Parse(string[] args)
        {
            var options = new CliOptions();

            if (args.Length == 0)
            {
                options.Verb = CliVerb.Help;
                return options;
            }

            string firstArg = args[0].ToLowerInvariant();

            // 检查旧版命令兼容性
            if (TryParseLegacyCommand(firstArg, args, options))
            {
                return options;
            }

            // 检查 --help / --version
            if (firstArg == "--help" || firstArg == "-h" || firstArg == "help")
            {
                options.Verb = CliVerb.Help;
                return options;
            }

            // 解析新版命令: verb [target] [options]
            options.Verb = ParseVerb(firstArg);
            if (options.Verb == CliVerb.None)
            {
                options.Errors.Add($"Unknown command: '{args[0]}'");
                return options;
            }

            int nextIndex = 1;

            // 解析 target (如果命令需要, 如 apply emip)
            if (VerbNeedsTarget(options.Verb) && args.Length > 1)
            {
                string targetStr = args[1].ToLowerInvariant();
                options.Target = ParseTarget(targetStr);
                if (options.Target == CliTarget.None)
                {
                    options.Errors.Add($"Unknown target: '{args[1]}' for command '{args[0]}'");
                    return options;
                }
                nextIndex = 2;
            }
            // 兼容旧版语法: export bundle / export assets / export bundle-dir / export assets-dir 等
            // 新版不需要 target，但如果用户仍然传递了旧的 target 关键字，跳过并给出提示
            else if (args.Length > 1 && !args[1].StartsWith("-") && IsLegacyTarget(args[1]))
            {
                Console.WriteLine($"[Info] Target '{args[1]}' is no longer required. File type is auto-detected. See --help for new syntax.");
                nextIndex = 2;
            }

            // 解析剩余的选项和 flags
            ParseOptionsAndFlags(args, nextIndex, options);

            // 验证必需参数
            ValidateOptions(options);

            return options;
        }

        private static bool TryParseLegacyCommand(string command, string[] args, CliOptions options)
        {
            switch (command)
            {
                case "batchexportbundle":
                    options.Verb = CliVerb.LegacyBatchExportBundle;
                    ParseLegacyArgs(args, options);
                    return true;

                case "batchimportbundle":
                    options.Verb = CliVerb.LegacyBatchImportBundle;
                    ParseLegacyArgs(args, options);
                    return true;

                case "applyemip":
                    options.Verb = CliVerb.LegacyApplyEmip;
                    if (args.Length > 1) options.LegacyPositionalArg = args[1];
                    if (args.Length > 2) options.LegacyPositionalArg2 = args[2];
                    ParseLegacyFlags(args, options);
                    return true;

                default:
                    return false;
            }
        }

        private static void ParseLegacyArgs(string[] args, CliOptions options)
        {
            // 旧版命令: batchexportbundle <directory> [-flags]
            for (int i = 1; i < args.Length; i++)
            {
                string arg = args[i];
                if (arg.StartsWith("-"))
                {
                    continue; // flags 在下面处理
                }

                if (string.IsNullOrEmpty(options.LegacyPositionalArg))
                    options.LegacyPositionalArg = arg;
                else if (string.IsNullOrEmpty(options.LegacyPositionalArg2))
                    options.LegacyPositionalArg2 = arg;
            }
            ParseLegacyFlags(args, options);
        }

        private static void ParseLegacyFlags(string[] args, CliOptions options)
        {
            for (int i = 1; i < args.Length; i++)
            {
                string arg = args[i];
                if (!arg.StartsWith("-"))
                    continue;

                switch (arg.ToLowerInvariant())
                {
                    case "-keepnames": options.KeepNames = true; break;
                    case "-kd": options.KeepDecomp = true; break;
                    case "-fd": options.ForceDecomp = true; break;
                    case "-md": options.MemoryDecomp = true; break;
                }
            }
        }

        private static CliVerb ParseVerb(string verb)
        {
            return verb switch
            {
                "export" => CliVerb.Export,
                "import" => CliVerb.Import,
                "apply" => CliVerb.Apply,
                "list" => CliVerb.List,
                "info" => CliVerb.Info,
                "decompress" => CliVerb.Decompress,
                "compress" => CliVerb.Compress,
                _ => CliVerb.None,
            };
        }

        private static bool VerbNeedsTarget(CliVerb verb)
        {
            return verb switch
            {
                CliVerb.Apply => true,   // apply emip
                _ => false,              // export/import/list/info/decompress/compress: 不需要 target
            };
        }

        private static bool IsLegacyTarget(string s)
        {
            return s switch
            {
                "bundle" => true,
                "assets" => true,
                "bundle-dir" => true,
                "assets-dir" => true,
                _ => false,
            };
        }

        private static CliTarget ParseTarget(string target)
        {
            return target switch
            {
                "bundle" => CliTarget.Bundle,
                "bundle-dir" => CliTarget.BundleDir,
                "assets" => CliTarget.Assets,
                "assets-dir" => CliTarget.AssetsDir,
                "emip" => CliTarget.Emip,
                _ => CliTarget.None,
            };
        }

        private static void ParseOptionsAndFlags(string[] args, int startIndex, CliOptions options)
        {
            for (int i = startIndex; i < args.Length; i++)
            {
                string arg = args[i];

                // 处理带值的选项 (需要消费下一个参数)
                if (IsValueOption(arg))
                {
                    if (i + 1 >= args.Length)
                    {
                        options.Errors.Add($"Option '{arg}' requires a value");
                        continue;
                    }

                    string value = args[++i];
                    SetOptionValue(arg, value, options);
                }
                // 处理布尔 flags
                else if (arg.StartsWith("-"))
                {
                    SetFlag(arg, options);
                }
                else
                {
                    // 意外的位置参数
                    options.Errors.Add($"Unexpected argument: '{arg}'");
                }
            }
        }

        private static bool IsValueOption(string arg)
        {
            string lower = arg.ToLowerInvariant();
            return lower switch
            {
                "-f" or "--file" => true,
                "-b" or "--bundle" => true,
                "-a" or "--assets" => true,
                "-d" or "--directory" => true,
                "-o" or "--output" => true,
                "-i" or "--input" => true,
                "-e" or "--emip" => true,
                "-t" or "--type" => true,
                "-p" or "--pathid" => true,
                "-n" or "--name" => true,
                "--format" => true,
                "--compress" => true,
                "--method" => true,
                "--author" => true,
                "--mod-name" => true,
                "--tex-format" => true,
                _ => false,
            };
        }

        private static void SetOptionValue(string option, string value, CliOptions options)
        {
            switch (option.ToLowerInvariant())
            {
                case "-f":
                case "--file":
                    options.FilePath = value;
                    break;

                case "-b":
                case "--bundle":
                    options.BundlePath = value;
                    // 同时更新 FilePath (export/import/list/info 的统一路径)
                    if (string.IsNullOrEmpty(options.FilePath))
                        options.FilePath = value;
                    break;

                case "-a":
                case "--assets":
                    options.AssetsPath = value;
                    // 同时更新 FilePath
                    if (string.IsNullOrEmpty(options.FilePath))
                        options.FilePath = value;
                    break;

                case "-d":
                case "--directory":
                    options.DirectoryPath = value;
                    break;

                case "-o":
                case "--output":
                    options.OutputDir = value;
                    break;

                case "-i":
                case "--input":
                    options.InputDir = value;
                    break;

                case "-e":
                case "--emip":
                    options.EmipPath = value;
                    break;

                case "-t":
                case "--type":
                    ParseCommaSeparated(value, options.FilterTypes);
                    break;

                case "-p":
                case "--pathid":
                    ParsePathIds(value, options);
                    break;

                case "-n":
                case "--name":
                    options.FilterName = value;
                    break;

                case "--format":
                    options.Format = ParseFormat(value, options);
                    break;

                case "--compress":
                case "--method":
                    options.CompressMethod = ParseCompressMethod(value, options);
                    break;

                case "--author":
                    options.ModAuthor = value;
                    break;

                case "--mod-name":
                    options.ModName = value;
                    break;

                case "--tex-format":
                    options.TextureFormatOverride = value;
                    break;
            }
        }

        private static void SetFlag(string flag, CliOptions options)
        {
            switch (flag.ToLowerInvariant())
            {
                case "--keepnames":
                case "-keepnames":
                    options.KeepNames = true;
                    break;
                case "--kd":
                case "-kd":
                    options.KeepDecomp = true;
                    break;
                case "--fd":
                case "-fd":
                    options.ForceDecomp = true;
                    break;
                case "--md":
                case "-md":
                    options.MemoryDecomp = true;
                    break;
                case "--backup":
                    options.Backup = true;
                    break;
                case "--no-backup":
                    options.NoBackup = true;
                    break;
                case "--recursive":
                    options.Recursive = true;
                    break;
                case "--dry-run":
                    options.DryRun = true;
                    break;
                case "-v":
                case "--verbose":
                    options.Verbose = true;
                    break;
                case "-q":
                case "--quiet":
                    options.Quiet = true;
                    break;
                default:
                    options.Errors.Add($"Unknown flag: '{flag}'");
                    break;
            }
        }

        private static void ParseCommaSeparated(string value, List<string> target)
        {
            string[] parts = value.Split(',', StringSplitOptions.RemoveEmptyEntries);
            foreach (string part in parts)
            {
                target.Add(part.Trim());
            }
        }

        private static void ParsePathIds(string value, CliOptions options)
        {
            string[] parts = value.Split(',', StringSplitOptions.RemoveEmptyEntries);
            foreach (string part in parts)
            {
                if (long.TryParse(part.Trim(), out long id))
                {
                    options.FilterPathIds.Add(id);
                }
                else
                {
                    options.Errors.Add($"Invalid PathID: '{part.Trim()}'");
                }
            }
        }

        private static CliExportFormat ParseFormat(string value, CliOptions options)
        {
            return value.ToLowerInvariant() switch
            {
                "raw" => CliExportFormat.Raw,
                "dump" => CliExportFormat.Dump,
                "json" => CliExportFormat.Json,
                "png" => CliExportFormat.Png,
                "wav" => CliExportFormat.Wav,
                "txt" => CliExportFormat.Txt,
                _ => ReportInvalidAndDefault(options, $"Unknown format: '{value}', defaulting to raw", CliExportFormat.Raw),
            };
        }

        private static CliCompressMethod ParseCompressMethod(string value, CliOptions options)
        {
            return value.ToLowerInvariant() switch
            {
                "lz4" => CliCompressMethod.Lz4,
                "lzma" => CliCompressMethod.Lzma,
                "none" => CliCompressMethod.None,
                _ => ReportInvalidAndDefault(options, $"Unknown compress method: '{value}', defaulting to none", CliCompressMethod.None),
            };
        }

        private static T ReportInvalidAndDefault<T>(CliOptions options, string message, T defaultValue)
        {
            options.Errors.Add(message);
            return defaultValue;
        }

        private static void ValidateOptions(CliOptions options)
        {
            if (options.HasErrors)
                return;

            switch (options.Verb)
            {
                case CliVerb.Export:
                    ValidateExport(options);
                    break;
                case CliVerb.Import:
                    ValidateImport(options);
                    break;
                case CliVerb.Apply:
                    ValidateApply(options);
                    break;
                case CliVerb.Decompress:
                case CliVerb.Compress:
                    if (string.IsNullOrEmpty(options.BundlePath))
                        options.Errors.Add("Bundle path (-b) is required");
                    if (string.IsNullOrEmpty(options.OutputDir))
                        options.Errors.Add("Output path (-o) is required");
                    break;
                case CliVerb.List:
                case CliVerb.Info:
                    ValidateListInfo(options);
                    break;
            }
        }

        private static void ValidateExport(CliOptions options)
        {
            bool hasFile = !string.IsNullOrEmpty(options.FilePath);
            bool hasDir  = !string.IsNullOrEmpty(options.DirectoryPath);

            if (!hasFile && !hasDir)
            {
                options.Errors.Add("'export' requires -f <file> (single file) or -d <dir> (directory batch)");
                return;
            }

            if (string.IsNullOrEmpty(options.OutputDir))
                options.Errors.Add("Output directory (-o) is required for 'export'");

            if (hasFile && !File.Exists(options.FilePath))
                options.Errors.Add($"File not found: {options.FilePath}");

            if (hasDir && !Directory.Exists(options.DirectoryPath))
                options.Errors.Add($"Directory not found: {options.DirectoryPath}");
        }

        private static void ValidateImport(CliOptions options)
        {
            bool hasFile = !string.IsNullOrEmpty(options.FilePath);
            bool hasDir  = !string.IsNullOrEmpty(options.DirectoryPath);

            if (!hasFile && !hasDir)
            {
                options.Errors.Add("'import' requires -f <file> (single file) or -d <dir> (directory batch)");
                return;
            }

            if (string.IsNullOrEmpty(options.InputDir))
                options.Errors.Add("Input directory (-i) is required for 'import'");

            if (hasFile && !File.Exists(options.FilePath))
                options.Errors.Add($"File not found: {options.FilePath}");

            if (hasDir && !Directory.Exists(options.DirectoryPath))
                options.Errors.Add($"Directory not found: {options.DirectoryPath}");
        }

        private static void ValidateApply(CliOptions options)
        {
            if (options.Target == CliTarget.Emip)
            {
                if (string.IsNullOrEmpty(options.EmipPath))
                    options.Errors.Add("EMIP file (-e) is required for 'apply emip'");
                if (string.IsNullOrEmpty(options.DirectoryPath))
                    options.Errors.Add("Game directory (-d) is required for 'apply emip'");
            }
        }

        private static void ValidateListInfo(CliOptions options)
        {
            bool hasFile = !string.IsNullOrEmpty(options.FilePath);
            bool hasDir  = !string.IsNullOrEmpty(options.DirectoryPath);

            if (!hasFile && !hasDir)
                options.Errors.Add($"'{options.Verb.ToString().ToLower()}' requires -f <file> or -d <dir>");

            if (hasFile && !File.Exists(options.FilePath))
                options.Errors.Add($"File not found: {options.FilePath}");

            if (hasDir && !Directory.Exists(options.DirectoryPath))
                options.Errors.Add($"Directory not found: {options.DirectoryPath}");
        }
    }
}
