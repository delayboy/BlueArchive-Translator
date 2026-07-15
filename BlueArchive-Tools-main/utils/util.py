import os
import subprocess
import re
import tempfile
import stat
import platform

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Generator, Iterable, Literal, Protocol, Tuple
from queue import Queue
from threading import Thread, Lock, Event
from time import sleep
from keyword import kwlist
from zipfile import ZipFile, ZIP_DEFLATED
from lib.console import ProgressBar, notice
from lib.downloader import FileDownloader
import pyminizip
class TemplateString:
    """
    Template string generator.

    :Example:
    .. code-block:: python
        CONSTANT = TemplateString("What%s a %s %s.")
        CONSTANT("", "fast", "fox")
        "What a fast fox."
    """

    def __init__(self, template: str) -> None:
        self.template = template

    def __call__(self, *args: Any) -> str:
        return self.template % args

class Utils:
    @staticmethod
    def convert_name_to_available(variable_name: str) -> str:
        """Convert varaible name to suitable with python.

        Args:
            variable_name (str): Name.

        Returns:
            str: Available string in python.
        """
        if not variable_name:
            return "_"
        if variable_name[0].isdigit():
            variable_name = "_" + variable_name
        if variable_name in kwlist:
            variable_name = f"{variable_name}_"
        return variable_name
        
class TaskManagerWorkerProtocol(Protocol):
    def __call__(
        self, task_manager: "TaskManager", *args: Any, **kwargs: Any
    ) -> None: ...


class TaskManager:
    def __init__(
        self,
        target_workers: int,
        max_workers: int,
        worker: TaskManagerWorkerProtocol,
        tasks: Queue[Any] = Queue(),
    ) -> None:
        """A simplified thread pool manager.

        Args:
            max_workers (int): Maximum number of threads to use.
            worker (Callable[..., None]): The worker function executed by each thread.
        """
        self.target_workers = target_workers
        self.max_workers = max_workers
        self.worker = worker
        self.tasks = tasks
        self.stop_task = False
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures: list[concurrent.futures.Future] = []
        self.lock = Lock()
        self.event = Event()
        self.__cancel_callback: tuple[Callable, tuple] | None = None
        self.__pool_condition: Callable = lambda: self.tasks.empty() or self.stop_task
        self.__force_exit = False

    def __enter__(self) -> "TaskManager":
        """Start the worker pool."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Shutdown the worker pool."""
        is_force = self.stop_task or self.__force_exit
        self.executor.shutdown(wait=not is_force, cancel_futures=is_force)

    def __set_conditions(self, func: Callable | None = None) -> None:
        if not func:
            self.__pool_condition = lambda: self.tasks.empty() or self.stop_task
        else:
            self.__pool_condition = func

    def add_worker(self, *args: Any) -> None:
        """Add a task to the worker queue."""
        future = self.executor.submit(self.worker, *args)
        self.futures.append(future)

    def increase_worker(self, num: int = 1) -> None:
        """Increase worker with exsist worker parameters."""
        self.target_workers += num

    def set_cancel_callback(self, callback: Callable[..., None], *args) -> None:
        """Set a callback for task canceled."""
        self.__cancel_callback = (callback, args)

    def set_force_shutdown(self, force: bool = True) -> None:
        """Set is or not shutdown without wait."""
        self.__force_exit = force

    def set_relate(
        self, mode: Literal["event"], related_manager: "TaskManager"
    ) -> None:
        """Set a relation to another task by a flag."""
        if mode == "event":
            self.event = related_manager.event
            self.__set_conditions(
                lambda: self.stop_task or (self.tasks.empty() and self.event.is_set())
            )

    def import_tasks(self, tasks: Iterable[Any]) -> None:
        """Import tasks from iterable sequency and set to instance task

        Args:
            tasks (Iterable[Any]): Any iterable elements.
        """
        queue_tasks: Queue[Any] = Queue()
        for task in tasks:
            queue_tasks.put(task)
        self.tasks = queue_tasks

    def run_without_block(self, *worker_args: Any) -> Thread:
        """Same as run and without block."""
        thread = Thread(target=self.run, args=worker_args, daemon=True)
        thread.start()
        return thread

    def run(self, *worker_args: Any) -> None:
        """Start worker and give parameters to worker."""
        try:
            while not self.__pool_condition():
                while len(self.futures) < self.target_workers:
                    self.add_worker(*worker_args)
                self.futures = [f for f in self.futures if not f.done()]
                sleep(0.1)

        except KeyboardInterrupt:
            if self.__cancel_callback:
                self.__cancel_callback[0](*self.__cancel_callback[1])
            self.stop_task = True
            while not self.tasks.empty():
                self.tasks.get()
                self.tasks.task_done()
            self.executor.shutdown(wait=False, cancel_futures=True)
        finally:
            self.event.set()
            if not self.__force_exit:
                for future in self.futures:
                    future.result()

    def done(self) -> None:
        """Finish thread pool manually."""
        self.__exit__(None, None, None)

class ZipUtils:
    @staticmethod
    def extract_zip(
        zip_path: str | list[str],
        dest_dir: str,
        *,
        keywords: list[str] | None = None,
        zips_dir: str = "",
        password: bytes = bytes(),
        progress_bar: bool = True,
    ) -> list[str]:
        """Extracts specific files from a zip archive(s) to a destination directory.

        Args:
            zip_path (str | list[str]): Path(s) to the zip file(s).
            dest_dir (str): Directory where files will be extracted.
            keywords (list[str], optional): List of keywords to filter files for extraction. Defaults to None.
            zips_dir (str, optional): Base directory for relative paths when zip_path is a list. Defaults to "".
            progress_bar (str, optional): Create a progress bar during extract. Defaults to False.


        Returns:
            list[str]: List of extracted file paths.
        """
        if progress_bar:
            print(f"Extracting files from {zip_path} to {dest_dir}...")
        extract_list: list[str] = []
        zip_files = []

        if isinstance(zip_path, str):
            zip_files = [zip_path]
        elif isinstance(zip_path, list):
            zip_files = [os.path.join(zips_dir, p) for p in zip_path]

        os.makedirs(dest_dir, exist_ok=True)

        if progress_bar:
            bar = ProgressBar(len(extract_list), "Extract...", "items")
        for zip_file in zip_files:
            try:
                with ZipFile(zip_file, "r") as z:
                    z.setpassword(password)
                    if keywords:
                        extract_list = [
                            item for k in keywords for item in z.namelist() if k in item
                        ]
                        for item in extract_list:
                            try:
                                z.extract(item, dest_dir)
                            except Exception as e:
                                notice(str(e))
                            if progress_bar:
                                bar.increase()
                    else:
                        z.extractall(dest_dir)

            except Exception as e:
                notice(f"Error processing file '{zip_file}': {e}")
        if progress_bar:
            bar.stop()
        return extract_list

    @staticmethod
    def create_zip(
        file_paths: str | list[str],
        dest_zip: str,
        *,
        keywords: list[str] | None = None,
        base_dir: str = "",
        compression: int = ZIP_DEFLATED,
        password: bytes = bytes(),
        progress_bar: bool = False,
        verbose: bool = False,
    ) -> bool:
        """Compresses specific files into a zip archive.

        Args:
            file_paths (str | list[str]): Path(s) to the files or directories to compress.
            dest_zip (str): Path where the resulting zip file will be saved.
            keywords (list[str], optional): List of keywords to filter files for compression. Defaults to None.
            base_dir (str, optional): Base directory for relative paths in the zip. Defaults to "".
            compression (int, optional): Compression method. Defaults to ZIP_DEFLATED.
            password (bytes, optional): Password for the zip file. Defaults to bytes().
            progress_bar (bool, optional): Create a progress bar during compression. Defaults to True.
            verbose (bool, optional): Output verbose debugging logs.

        Returns:
            bool: True if compression was successful.
        """
        if progress_bar:
            print(f"Compressing files to {dest_zip}...")

        if verbose:
            print(f"[VERBOSE] Target ZIP: {dest_zip}")
            print(f"[VERBOSE] Password: {password.decode() if password else 'None'}")
            print(f"[VERBOSE] Base Directory: {base_dir}")

        input_paths = [file_paths] if isinstance(file_paths, str) else file_paths
        files_to_add = []

        for path in input_paths:
            full_path = os.path.join(base_dir, path) if base_dir else path
            if os.path.isfile(full_path):
                files_to_add.append(full_path)
            elif os.path.isdir(full_path):
                files_to_add.extend(
                    os.path.join(root, file)
                    for root, _, files in os.walk(full_path)
                    for file in files
                )

        if keywords:
            files_to_add = [f for f in files_to_add if any(k in f for k in keywords)]

        if not files_to_add:
            return False

        bar = ProgressBar(len(files_to_add), "Compress...", "items") if progress_bar else None

        try:
            os.makedirs(os.path.dirname(os.path.abspath(dest_zip)), exist_ok=True)

            # pyminizip 只以 CWD 为基准解析 src_path，prefix 参数不参与文件定位
            # 因此必须切到文件所在目录后传空 prefix + 相对路径
            if base_dir:
                work_dir = os.path.abspath(base_dir)
                src_paths = [os.path.relpath(os.path.abspath(f), work_dir) for f in files_to_add]
            else:
                work_dir = os.path.commonpath([os.path.abspath(f) for f in files_to_add])
                src_paths = [os.path.relpath(os.path.abspath(f), work_dir) for f in files_to_add]

            pwd_str = password.decode() if password else ""
            complevel = compression if isinstance(compression, int) and 1 <= compression <= 9 else 5

            cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                if len(src_paths) == 1:
                    pyminizip.compress(
                        src_paths[0], "", dest_zip, pwd_str, complevel
                    )
                else:
                    pyminizip.compress_multiple(
                        src_paths, ["" for _ in src_paths], dest_zip, pwd_str, complevel
                    )
            finally:
                os.chdir(cwd)

            if bar:
                for _ in files_to_add:
                    bar.increase()
                bar.stop()
            return True
        except Exception as e:
            notice(f"Error creating zip '{dest_zip}': {e}")
            if bar:
                bar.stop()
            return False



    # Used to parse the area where the EOCD (End of Central Directory) of the compressed file's central directory is located.
    @staticmethod
    def parse_eocd_area(data: bytes) -> tuple[int, int]:
        eocd_signature = b"\x50\x4b\x05\x06"
        eocd_offset = data.rfind(eocd_signature)
        if eocd_offset == -1:
            raise EOFError("Cannot read the eocd of file.")
        eocd = data[eocd_offset : eocd_offset + 22]
        _, _, _, _, _, cd_size, cd_offset, _ = struct.unpack("<IHHHHIIH", eocd)
        return cd_offset, cd_size

    # Used to parse the files contained in the central directory. Use for common apk.
    @staticmethod
    def parse_central_directory_data(data: bytes) -> list:
        file_headers = []
        offset = 0
        while offset < len(data):
            if data[offset : offset + 4] != b"\x50\x4b\x01\x02":
                raise BufferError("Cannot parse the central directory of file.")
            pack = struct.unpack("<IHHHHHHIIIHHHHHII", data[offset : offset + 46])

            uncomp_size = pack[9]
            file_name_length = pack[10]
            extra_field_length = pack[11]
            file_comment_length = pack[12]
            local_header_offset = pack[16]
            file_name = data[offset + 46 : offset + 46 + file_name_length].decode(
                "utf8"
            )

            file_headers.append(
                {"path": file_name, "offset": local_header_offset, "size": uncomp_size}
            )
            offset += 46 + file_name_length + extra_field_length + file_comment_length

        return file_headers

    @staticmethod
    def download_and_decompress_file(
        apk_url: str, target_path: str, header_part: bytes, start_offset: int
    ) -> bool:
        """Request partial data from an online compressed file and then decompress it."""
        try:
            header = struct.unpack("<IHHHHHIIIHH", header_part[:30])
            _, _, _, compression, _, _, _, comp_size, _, file_name_len, extra_len = (
                header
            )
            data_start = start_offset + 30 + file_name_len + extra_len
            data_end = data_start + comp_size
            compressed_data = FileDownloader(
                apk_url,
                headers={"Range": f"bytes={data_start}-{data_end - 1}"},
            )
            return ZipUtils.decompress_file_part(
                compressed_data, target_path, compression
            )
        except:
            return False

    @staticmethod
    def decompress_file_part(compressed_data_part, file_path, compress_method) -> bool:
        """Decompress pure compressed data. Return True if saved to path."""
        try:
            if compress_method == 8:  # Deflate compression
                decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
                decompressed_data = decompressor.decompress(compressed_data_part)
                decompressed_data += decompressor.flush()
            else:
                decompressed_data = compressed_data_part
            with open(file_path, "wb") as file:
                file.write(decompressed_data)
            return True
        except:
            return False

class FileUtils:
    @staticmethod
    def find_files(
        directory: str,
        keywords: list[str],
        absolute_match: bool = False,
        sequential_match: bool = False,
    ) -> list[str]:
        """Retrieve files from a given directory based on specified keywords of file name.

        Args:
            directory (str): The directory to search for files.
            keywords (list[str]): A list of keywords to match file names.
            absolute_match (bool, optional): If True, matches file names exactly with the keywords. If False, performs a partial match (i.e., checks if any keyword is a substring of the file name). Defaults to False.
            sequential_match (bool, optional): If True, the final list will be matched sequentially based on the order of the provided keywords. If a keyword has multiple values, only one will be retained. A keyword that no result to be retrieved will correspond to a None value. Defaults to False.
        Returns:
            list[str]: A list of file paths that match the specified criteria.
        """
        paths = []
        
        compiled_patterns = []
        for k in keywords:
            try:
                compiled_patterns.append(re.compile(k))
            except re.error:
                compiled_patterns.append(re.compile(re.escape(k)))

        for dir_path, _, files in os.walk(directory):
            for file in files:
                if absolute_match:
                    if any(pattern.fullmatch(file) for pattern in compiled_patterns):
                        paths.append(os.path.join(dir_path, file))
                else:
                    if any(pattern.search(file) for pattern in compiled_patterns):
                        paths.append(os.path.join(dir_path, file))

        if not sequential_match:
            return paths

        sorted_paths = []
        # Sequential match part.
        for pattern in compiled_patterns:
            for p in paths:
                file_name = os.path.basename(p)
                if (absolute_match and pattern.fullmatch(file_name)) or (not absolute_match and pattern.search(file_name)):
                    sorted_paths.append(p)
                    break

        return sorted_paths

class CommandUtils:
    @staticmethod
    def run_command(
        *commands: str,
        cwd: str | None = None,
    ) -> tuple[bool, str]:
        """
        Executes a shell command and returns whether it succeeded.

        Args:
            *commands (str): Command and its arguments as separate strings.

        Returns:
            tuple (bool, str): True if the command succeeded, False otherwise. And error string.
        """
        try:
            subprocess.run(
                list(commands),
                check=True,
                text=True,
                cwd=cwd,
                encoding="utf8",
            )
            return True, ""
        except Exception as e:
            return False, e

class AsarUtils:
    @staticmethod
    def extract_asar(asar_path: str, dest_dir: str) -> bool:
        """
        将 asar 文件解压到指定目录
        """
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        success, error = CommandUtils.run_command("asar", "extract", asar_path, dest_dir)
        if not success:
            print(f"解压 ASAR 失败: {error}")
        return success

    @staticmethod
    def pack_asar(src_dir: str, asar_path: str) -> bool:
        """
        将指定目录打包回 asar 文件
        """
        parent_dir = os.path.dirname(asar_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
            
        success, error = CommandUtils.run_command("asar", "pack", src_dir, asar_path)
        if not success:
            print(f"打包 ASAR 失败: {error}")
        return success

class ToolManager:
    def __init__(self, install_dir: str):
        self.install_dir = install_dir
        self.binary_name = "BlueArchiveTools.CLI"

    @classmethod
    def get_platform_identifier(cls) -> Tuple[str, str]:
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

    def ensure_tool(self) -> str:
        platform_id, os_name = self.get_platform_identifier()
        
        if not os.path.exists(self.install_dir):
            os.makedirs(self.install_dir, exist_ok=True)
            zip_url = f"https://github.com/beichen23333/BlueArchive-Tools-CLI/releases/latest/download/BlueArchiveTools.{platform_id}.zip"
            zip_path = os.path.join(self.install_dir, "tools.zip")

            FileDownloader(zip_url).save_file(zip_path)
            ZipUtils.extract_zip(zip_path, self.install_dir)
            os.remove(zip_path)

        binary_path = os.path.abspath(os.path.join(self.install_dir, self.binary_name))
        if os_name == "win":
            binary_path += ".exe"
        else:
            if not os.access(binary_path, os.X_OK):
                os.chmod(binary_path, os.stat(binary_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return binary_path
