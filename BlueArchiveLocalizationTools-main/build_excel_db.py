from build_excel_zip import apply_replacements
from repacker import TableRepackerImpl
from extractor import TablesExtractor
from pathlib import Path
import argparse
import shutil
from optimize_db import rebuild_database
import json
def main(voice_file_names_path: Path, excel_input_path: Path, repl_input_dir: Path, output_filepath: Path) -> None:
    try:
        with open(repl_input_dir / "config.json", "r") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        cfg = {}
    import setup_flatdata
    packer = TableRepackerImpl('Extracted.FlatData')
    source_dir = Path(f'Extracted/Table/{excel_input_path.stem}')
    if not source_dir.exists():
        print("Extracting source db JSONs...")
        TablesExtractor('Extracted', excel_input_path.parent).extract_table(excel_input_path.name)
    shutil.copy(excel_input_path, output_filepath)
    for jsonfile in source_dir.iterdir():
        repl_file = repl_input_dir / jsonfile.name
        if repl_file.exists():
            if cfg.get("applyvoicecn", False):
                out_file = apply_replacements(jsonfile, repl_file)
                if jsonfile.stem not in ["ScenarioScriptExcel", "VoiceExcel"]:
                    packer.repackjson2db(out_file, output_filepath)
            else:
                out_file = apply_replacements(jsonfile, repl_file, skip_fields=["VoiceId"])
                packer.repackjson2db(out_file, output_filepath)
    if cfg.get("applyvoicecn", False):
        temp_dir = source_dir / "temp"
        scenario_script_path = temp_dir / "ScenarioScriptExcel.json"
        voice_excel_path = temp_dir / "VoiceExcel.json"
        if not scenario_script_path.exists():
            shutil.copy(source_dir / "ScenarioScriptExcel.json", scenario_script_path)
        if not voice_excel_path.exists():
            shutil.copy(source_dir / "VoiceExcel.json", voice_excel_path)
        from voicecn import main as voice_build
        voice_build(voice_file_names_path, scenario_script_path, voice_excel_path)
        packer.repackjson2db(scenario_script_path, output_filepath)
        packer.repackjson2db(voice_excel_path, output_filepath)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    rebuild_database(output_filepath)
    print(f"Outputed modified DB to {output_filepath}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Excel files and apply replacements.")
    parser.add_argument("voice_file_names_path", type=Path, help="Path to voice_file_names.json for voice stuff.")
    parser.add_argument("excel_input_path", type=Path, help="Path to the ExcelDB.db file.")
    parser.add_argument("repl_input_dir", type=Path, help="Path to the directory with replacement files for ExcelDB.db.")
    parser.add_argument("output_filepath", type=Path, nargs="?", default=None, help="Path to save the modified ExcelDB.db. Defaults to the input file path.")
    args = parser.parse_args()

    output_filepath = args.output_filepath if args.output_filepath else args.excel_input_path
    main(args.voice_file_names_path, args.excel_input_path, args.repl_input_dir, output_filepath)
