import multiprocessing
import multiprocessing.context
import multiprocessing.queues
import multiprocessing.synchronize
import os
import time
from multiprocessing import Queue, freeze_support
from os import path

from lib.compiler import CompileToPython, CSParser
from lib.console import ProgressBar, bar_increase, bar_text, notice
from utils.util import TaskManager
from xtractor.bundle import BundleExtractor
from xtractor.table import TableExtractor
import importlib
from lib.encryption import xor_with_key
from utils.config import Config

class BundlesExtractor:
    @staticmethod
    def extract(EXTRACT_DIR, BUNDLE_FOLDER) -> None:
        freeze_support()
        extractor = BundleExtractor(EXTRACT_DIR, BUNDLE_FOLDER)
        queue: multiprocessing.queues.Queue = Queue()
        bundles = os.listdir(extractor.BUNDLE_FOLDER)
        for bundle in bundles:
            queue.put(path.join(extractor.BUNDLE_FOLDER, bundle))
        with ProgressBar(len(bundles), "Extracting bundle...", "items") as bar:
            processes = [
                multiprocessing.Process(
                    target=extractor.multiprocess_extract_worker,
                    args=(queue, extractor.MAIN_EXTRACT_TYPES),
                )
                for _ in range(5)
            ]
            for p in processes:
                p.start()
            try:
                while not queue.empty():
                    bar.set_progress_value(bar.total - queue.qsize())
                    time.sleep(0.1)
                notice("Extract bundles successfully.")
            except KeyboardInterrupt:
                notice("Bundle extract task has been canceled.", "error")
                for p in processes:
                    p.kill()

class TablesExtractor(TableExtractor):
    def __init__(self, EXTRACT_DIR, TABLE_FOLDER) -> None:
        self.TABLE_FOLDER = TABLE_FOLDER
        self.TABLE_EXTRACT_FOLDER = path.join(EXTRACT_DIR, "Table")
        super().__init__(
            self.TABLE_FOLDER,
            self.TABLE_EXTRACT_FOLDER,
            f"{EXTRACT_DIR}.FlatData",
        )

    def __extract_worker(self, task_manager: TaskManager) -> None:
        while not (task_manager.stop_task or task_manager.tasks.empty()):
            table_file = task_manager.tasks.get()
            ProgressBar.item_text(table_file)
            self.extract_table(table_file)
            table_file = task_manager.tasks.task_done()
            ProgressBar.increase()

    def extract_tables(self) -> None:
        """Extract table with multi-thread"""
        if not path.exists(self.TABLE_FOLDER):
            return
        os.makedirs(self.TABLE_EXTRACT_FOLDER, exist_ok=True)
        table_files = os.listdir(self.TABLE_FOLDER)
        with ProgressBar(len(table_files), "Extracting Table file...", "items"):
            with TaskManager(
                Config.threads, Config.max_threads, self.__extract_worker
            ) as e_task:
                e_task.set_cancel_callback(
                    notice, "Table extract task has been canceled.", "error"
                )
                e_task.import_tasks(table_files)
                e_task.run(e_task)

def compile_python(DUMP_CS_FILE_PATH, EXTRACT_DIR) -> None:
    """Compile python callable module from dump file"""
    print("Parsing dump.cs...")
    parser = CSParser(DUMP_CS_FILE_PATH)
    enums = parser.parse_enum()
    structs = parser.parse_struct()
    
    print("Generating flatbuffer python dump files...")
    compiler = CompileToPython(enums, structs, path.join(EXTRACT_DIR, "FlatData"))
    compiler.create_enum_files()
    compiler.create_struct_files()
    compiler.create_module_file()
    compiler.create_dump_dict_file()
    compiler.create_repack_dict_file()
class TableExtractorImpl:
    def __init__(self, flat_data_module_name):
        try:
            flat_data_lib = importlib.import_module(flat_data_module_name)
            self.dump_wrapper_lib = importlib.import_module(
                f"{flat_data_module_name}.dump_wrapper"
            )
            self.lower_fb_name_modules = {
            t_name.lower(): t_class
            for t_name, t_class in flat_data_lib.__dict__.items()
            }
        except Exception as e:
            notice(
                f"Cannot import FlatData module. Make sure FlatData is available in Extracted folder. {e}",
                "error",
            )
    def bytes2json(self, file_path):
        if not (
        flatbuffer_class := self.lower_fb_name_modules.get(
            file_path.stem.lower(), None
            )
        ):
            print(f"class {file_path.stem.lower()} not found")
            return
        with open(file_path, 'rb') as f:
            data = f.read()
        obj = None
        try:
            if flatbuffer_class.__name__.endswith("Table"):
                try:
                    if not Config.is_cn: # CN does not encrypt its Excel.zip (but does encrypt tables in sqlite3 databases such as ExcelDB.db)
                        data = xor_with_key(flatbuffer_class.__name__, data)
                    flat_buffer = getattr(flatbuffer_class, "GetRootAs")(data)
                    obj = getattr(self.dump_wrapper_lib, "dump_table")(flat_buffer)
                except Exception as e:
                    pass
            if not obj:
                flat_buffer = getattr(flatbuffer_class, "GetRootAs")(data)
                obj = getattr(
                    self.dump_wrapper_lib, f"dump_{flatbuffer_class.__name__}"
                )(flat_buffer)
            return obj
        except Exception as e:
            print(e)