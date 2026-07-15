import os
from os import path

EXTRACT_DIR = "Extracted"
DUMP_PATH = "Dumps"
if not path.exists(path.join(EXTRACT_DIR, "FlatData")):
    # import setup_apk
    from lib.dumper import IL2CppDumper
    from lib.console import notice
    from utils.util import FileUtils
    from extractor import compile_python

    IL2CPP_NAME = "GameAssembly.dll"
    METADATA_NAME = "global-metadata.dat"

    TEMP_DIR = "Temp"

    save_path = TEMP_DIR
    dumper = IL2CppDumper()
    dumper.get_il2cpp_dumper(save_path)

    il2cpp_path = FileUtils.find_files(TEMP_DIR, [IL2CPP_NAME], True)
    metadata_path = FileUtils.find_files(
        TEMP_DIR, [METADATA_NAME], True
    )

    if not (il2cpp_path and metadata_path):
        raise FileNotFoundError(
            "Cannot find il2cpp binary file or global-metadata file. Make sure exist."
        )
    abs_il2cpp_path = path.abspath(il2cpp_path[0])
    abs_metadata_path = path.abspath(metadata_path[0])

    extract_path = path.abspath(path.join(EXTRACT_DIR, DUMP_PATH))
    if not os.path.exists(extract_path):
        print("Try to dump il2cpp...")
        dumper.dump_il2cpp(
            extract_path, abs_il2cpp_path, abs_metadata_path, 5
        )
        notice("Dump il2cpp binary file successfully.")
    compile_python(path.join(extract_path, "dump.cs"), EXTRACT_DIR)
    notice("Generated FlatData to dir: " + EXTRACT_DIR)
