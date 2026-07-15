# UABEA CLI Commands Reference

## Command Format

```bash
UABEAvalonia <command> <options> [flags]
```

> **Automatic File Type Detection**: The `export`, `import`, `list`, and `info` commands automatically determine if the file provided via `-f <file>` is a Bundle or an Assets file. You do not need to manually specify `bundle` or `assets` subcommands.

---

## 1. Export Resources

**Syntax:**
```bash
# Single file (Auto-detect Bundle or Assets)
UABEAvalonia export -f <file_path> -o <output_dir> [flags]

# Batch directory (Auto-detect for each file)
UABEAvalonia export -d <directory> -o <output_dir> [flags]
```

**Examples:**
```bash
# Export all assets from a Bundle or Assets file
UABEAvalonia export -f game.bundle -o ./out/
UABEAvalonia export -f sharedassets0.assets -o ./out/

# Export only Texture2D assets as PNG
UABEAvalonia export -f game.bundle -o ./out/ -t Texture2D --format png

# Batch process a directory (handles mixed bundles/assets)
UABEAvalonia export -d ./GameData/ -o ./out/ --recursive

# Filter by specific PathIDs
UABEAvalonia export -f sharedassets0.assets -o ./out/ -p 3,7,42
```

### Export File Naming
The CLI uses a naming format consistent with the GUI to allow easy re-importing by filename matching:
- **Format**: `{AssetName}-{AssetsFileName}-{PathID}.{Extension}`
- **Example**: `Arial-sharedassets0-123.dat`, `Texture_Bg-level0-45.png`

---

## 2. Import Resources (Write Back)

**Syntax:**
```bash
# Single file (Auto-detect Bundle or Assets)
UABEAvalonia import -f <file_path> -i <input_dir> [flags]

# Batch directory (Auto-detect for each file)
UABEAvalonia import -d <directory> -i <input_dir> [flags]
```

**Examples:**
```bash
# Import assets back into a single file
UABEAvalonia import -f game.bundle -i ./import/
UABEAvalonia import -f sharedassets0.assets -i ./import/

# Backup original file before importing
UABEAvalonia import -f game.bundle -i ./import/ --backup

# Specify texture format for lookup (Default keeps original format)
UABEAvalonia import -f game.bundle -i ./import/ --tex-format RGBA32

# Batch import
UABEAvalonia import -d ./GameData/ -i ./import/ --recursive
```

### Import Matching Rules
The tool automatically searches the input directory (`-i`) for files ending in `-{AssetsFileName}-{PathID}.{ext}`.
- The prefix (Asset Name) does not need to match perfectly; only the suffix is strictly checked.
- When importing `.png`/`.tga` images into Texture2D, **original texture formats are preserved by default** (e.g., ETC2, ASTC, DXT) using `TexturePlugin.dll`. If the plugin is unavailable, it falls back to RGBA32. You can force a specific format using `--tex-format <format>`.

---

## 3. Query Resources (list / info)

### 3.1 List Assets (list)

Lists all assets within a file, supporting filtering and keyword search.

**Syntax:**
```bash
# Single file
UABEAvalonia list -f <file_path> [filters]

# Batch directory
UABEAvalonia list -d <directory> [filters] [--recursive]
```

**Filters (Can be combined):**

| Option | Description |
|--------|-------------|
| `-n <pattern>` | Filter by asset name (supports multiple matching modes, see below) |
| `-t <type>` | Filter by asset type (e.g., `-t Texture2D`) |
| `-p <pathid>` | Filter by PathID (comma separated) |

**`-n` Name Filtering Syntax:**

| Syntax | Mode | Example | Description |
|--------|------|---------|-------------|
| `keyword` | Substring | `-n hero` | Matches if name contains `hero` (Default, case-insensitive) |
| `=name` | Exact | `-n "=hero_icon"` | Name must be exactly `hero_icon` |
| `~regex` | Regex | `-n "~hero_\d+"` | Matches using Regular Expression |
| `*`/`?` | Wildcard | `-n "hero_*"` | `*` matches any sequence, `?` matches single char |
| `!pattern` | Negation | `-n "!villain"` | Exclude assets containing `villain` |
| `a,b,c` | OR Logic | `-n "hero,warrior"` | Matches if any pattern is found |
| `!=name` | Combined | `-n "!=bg_dark"` | Negation + Exact: Exclude if name is exactly `bg_dark` |
| `!~regex` | Combined | `-n "!~bad_\d+"` | Negation + Regex: Exclude if regex matches |

**Matching Logic:**
- **Positive matches** (without `!`) use **OR** logic: if any match, the asset is included.
- **Negative matches** (with `!`) use **AND** logic: the asset must pass ALL negative checks.
- Can be mixed: `-n "hero,warrior,!hero_bg"` means "Contains hero OR warrior, BUT must NOT contain hero_bg".

**Output Format (Bundle):**
```
Bundle: /path/to/game.bundle
PathID       Entry                               Type                 Size Name
----------------------------------------------------------------------------------------------------
3            level0                              Font                 7680 Arial
45           level0                              Texture2D           65536 sprite_bg
```

**Output Format (Assets):**
```
Assets File: /path/to/sharedassets0.assets (12 assets)
PathID       Type                         Size Name
--------------------------------------------------------------------------------
3            Font                        12345 Arial
```

**Search Examples:**
```bash
# Substring: Find Texture2Ds with "bg" in the name
UABEAvalonia list -d ./bundles/ -n bg -t Texture2D

# Exact: Find asset named exactly "hero_icon"
UABEAvalonia list -f game.bundle -n "=hero_icon"

# Regex: Find names matching hero_\d+
UABEAvalonia list -f game.bundle -n "~hero_\d+"

# Wildcard: Find assets starting with bg_
UABEAvalonia list -f game.bundle -n "bg_*"

# OR: Find assets containing hero OR warrior
UABEAvalonia list -d ./GameData/ -n "hero,warrior" --recursive

# Negation: Find all Texture2Ds except those containing "shadow"
UABEAvalonia list -f game.bundle -t Texture2D -n "!shadow"

# Mixed: Find hero OR warrior, but exclude _disabled
UABEAvalonia list -f game.bundle -n "hero,warrior,!_disabled"
```

The output will **only show files with matches** and provide a summary at the end:
```
Bundle: ./bundles/level1.bundle
PathID       Entry     Type         Size Name
...
45           level1    Texture2D   65536 hero_idle

Bundle: ./bundles/ui.bundle
...

Total: 3 matching asset(s) across 2 file(s).
```

### 3.2 View File Info (info)

Prints file metadata summary (does not enumerate internal assets).

**Syntax:**
```bash
# Single file
UABEAvalonia info -f <file_path>

# Batch directory
UABEAvalonia info -d <directory> [--recursive]
```

---

## 4. Compress / Decompress

```bash
# Decompress Bundle
UABEAvalonia decompress -b <bundle_path> -o <output_path>

# Compress Bundle
UABEAvalonia compress -b <bundle_path> -o <output_path> --method lz4|lzma
```

---

## 5. Apply EMIP Patch

```bash
UABEAvalonia apply emip -e <emip_file> -d <game_dir>
```

---

## 6. Parameters

### 6.1 Path Options

| Option | Long Flag | Description |
|--------|-----------|-------------|
| `-f` | `--file` | File path (Auto-detects type, recommended) |
| `-b` | `--bundle` | Alias for `-f`, for legacy compatibility and compress/decompress |
| `-a` | `--assets` | Alias for `-f`, for legacy compatibility |
| `-d` | `--directory` | Directory path for batch operations |
| `-o` | `--output` | Output directory or file path |
| `-i` | `--input` | Input directory path (for import) |

### 6.2 Filter Options

| Option | Long Flag | Description |
|--------|-----------|-------------|
| `-t` | `--type` | Filter by Asset Type (comma separated, e.g., `-t Texture2D,Font`) |
| `-p` | `--pathid` | Filter by PathID (comma separated) |
| `-n` | `--name` | Filter by Asset Name (supports substring, exact `=`, regex `~`, wildcard `*?`, negation `!`) |

### 6.3 General Flags

| Flag | Description |
|------|-------------|
| `--format` | Export format: `raw` (default), `png`, `txt`, `wav`, `dump`, `json` |
| `--method` | Compression method: `lz4`, `lzma`, `none` |
| `--tex-format` | Override texture import format (e.g., `RGBA32`, `DXT5`, `ETC2_RGBA8`, `BC7`). Keeps original if unspecified. |
| `--backup` | Create a backup of the original file before importing |
| `--no-backup` | Do not create a backup |
| `--recursive` | Process subdirectories recursively in directory mode |
| `--dry-run` | Preview mode, does not write changes to disk |
| `--keepnames` | Keep original file names during export |
| `--kd` | Keep `.decomp` cache files after operation |
| `--fd` | Force overwrite existing `.decomp` cache files |
| `--md` | Decompress to memory (do not write `.decomp` files) |
| `-v, --verbose` | Verbose output |
| `-q, --quiet` | Quiet mode |

---

## 7. Supported Asset Types (-t)

`Texture2D`, `TextAsset`, `AudioClip`, `Font`, `Mesh`, `Shader`, `MonoBehaviour`, `GameObject`, `AssetBundle`, and more.

**Special Format Support:**
| Asset Type | Export Format | Import Format |
|------------|---------------|---------------|
| Texture2D | `.png` (`-format png`) or `.dat` | `.png` (Encodes to original format by default) or `.dat` |
| TextAsset | `.txt` (`-format txt`) or `.dat` | `.txt` or `.dat` |
| AudioClip | `.wav` (`-format wav`) or `.dat` | `.dat` |
| Font | `.dat` (raw data) | `.otf` or `.ttf` (Replaces font data) |

---

## 8. Full Examples

### 8.1 Font Replacement Workflow

```bash
# 1. Export Font assets
UABEAvalonia export -f sharedassets0.assets -o ./export/ -t Font

# 2. Exported filename example: Arial-sharedassets0-123.dat
#    Rename your new font file to match this suffix: Arial-sharedassets0-123.otf

# 3. Import new font
UABEAvalonia import -f sharedassets0.assets -i ./export/
```

### 8.2 Batch Search: Find Bundles containing "bg" Texture2Ds

```bash
# 1. Scan all bundles using filters
UABEAvalonia list -d ./GameData/ -n bg -t Texture2D --recursive

# Output example:
# Bundle: ./GameData/ui.bundle
# PathID       Entry     Type                  Size Name
# ---...
# 45           ui        Texture2D            65536 bg_main_menu
#
# Total: 1 matching asset(s) across 1 file(s).

# 2. Use the found bundle path to import changes
UABEAvalonia import -f ./GameData/ui.bundle -i ./replace/
```

### 8.3 Batch Export Texture2D to PNG

```bash
UABEAvalonia export -d ./GameData/ -o ./Textures/ -t Texture2D --format png
```

### 8.4 Bundle Decompress & Recompress

```bash
UABEAvalonia decompress -b resources.bundle -o resources.unpacked
# Modify decompressed files...
UABEAvalonia compress -b resources.unpacked -o resources.bundle --method lz4
```

### 8.5 Legacy Command Compatibility

Older syntax is still supported but may show an info message:
```bash
# Legacy syntax
UABEAvalonia export bundle -b game.bundle -o ./out/
UABEAvalonia import assets -a sharedassets0.assets -i ./import/
```
