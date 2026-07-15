"""Dump il2cpp file to csharp file."""

import json
import os
import platform
import shutil
from os import path

from lib.downloader import FileDownloader
from utils.util import CommandUtils, FileUtils, ZipUtils


def get_platform_identifier():
    os_map = {
        "linux": "linux",
        "darwin": "osx",
        "windows": "win"
    }

    arch_map = {
        "x86_64": "x64",
        "amd64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64"
    }

    os_name = os_map.get(platform.system().lower())
    arch = arch_map.get(platform.machine().lower())

    if not os_name or not arch:
        raise RuntimeError(f"Unsupported OS or architecture: {platform.system()} {platform.machine()}")

    return f"{os_name}-{arch}", os_name


class IL2CppDumper:
    def __init__(self) -> None:
        self.project_dir = ""
        self.binary_name = "Il2CppInspector"

    def get_il2cpp_dumper(self, save_path: str) -> None:
        platform_id, os_name = get_platform_identifier()
        il2cpp_zip_url = f"https://github.com/asfu222/Il2CppInspectorRedux/releases/latest/download/Il2CppInspectorRedux.CLI-{platform_id}.zip"

        zip_path = path.join(save_path, "Il2CppInspectorRedux.CLI.zip")
        if not os.path.exists(zip_path):
            FileDownloader(il2cpp_zip_url).save_file(zip_path)

        extract_path = path.join(save_path, "Il2CppInspector")
        ZipUtils.extract_zip(zip_path, extract_path)
        self.project_dir = extract_path

        if os_name == "win":
            self.binary_name += ".exe"
        else:
            # Make the binary executable on Unix systems
            CommandUtils.run_command(
                "chmod",
                "+x",
                f"./{self.binary_name}",
                cwd=self.project_dir
            )

    def dump_il2cpp(
            self,
            extract_path: str,
            il2cpp_path: str,
            global_metadata_path: str,
            max_retries: int = 1,
    ) -> None:
        """Dump il2cpp using Il2CppInspector."""
        os.makedirs(extract_path, exist_ok=True)

        binary_path = f"./{self.binary_name}"
        cs_out = path.join(extract_path, "dump.cs")

        success, err = CommandUtils.run_command(
            os.path.abspath(os.path.join(self.project_dir, binary_path)),
            "--bin", il2cpp_path,
            "--metadata", global_metadata_path,
            "--select-outputs",
            "--cs-out", cs_out,
            "--must-compile",
            cwd=self.project_dir
        )

        if not success:
            raise RuntimeError(f"IL2CPP dump failed: {err}")

        return None
