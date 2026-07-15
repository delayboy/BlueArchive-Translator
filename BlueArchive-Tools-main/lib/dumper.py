"""Dump il2cpp file to csharp file."""
from utils.util import CommandUtils, ToolManager
from lib.compiler import CompileToPython, CSParser

def compile_python(dump_cs_path, extract_dir) -> None:
    """Compile python callable module from dump file"""
    print("Parsing dump.cs...")
    parser = CSParser(dump_cs_path)
    enums = parser.parse_enum()
    structs = parser.parse_struct()
    
    print("Generating flatbuffer python dump files...")
    compiler = CompileToPython(enums, structs, extract_dir)
    compiler.create_enum_files()
    compiler.create_struct_files()
    compiler.create_module_file()
    compiler.create_dump_dict_file()
    compiler.create_repack_dict_file()

class IL2CppDumper(ToolManager):
    def dump_il2cpp(self, server: str, il2cpp_path: str, metadata_path: str, output_path: str) -> None:
        bin_path = self.ensure_tool()
        success, err = CommandUtils.run_command(
            bin_path, "dump", server.lower(), il2cpp_path, metadata_path, output_path,
            cwd=self.install_dir
        )
        if not success:
            raise RuntimeError(f"IL2CPP dump failed: {err}")

