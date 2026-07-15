import importlib
import json
import os
import shutil
from os import path
from types import ModuleType
from typing import Any, Union
from zipfile import ZipFile, ZIP_DEFLATED
import flatbuffers
from lib.console import notice
from lib.encryption import xor_with_key, zip_password
from lib.structure import DBTable, SQLiteDataType
from utils.database import TableDatabase
from utils.config import Config
from utils.util import ZipUtils


class TableProcess:
    def __init__(
            self, table_file_folder: str, extract_folder: str, flat_data_module_name: str
    ) -> None:
        """Extract files in table folder.

        Args:
            table_file_folder (str): Folder own table files.
            extract_folder (str): Folder to store the extracted/repack data.
            flat_data_module_name (str): Name path to import flat data module. Most like "Extracted.FlatData".
        """
        self.table_file_folder = table_file_folder
        self.extract_folder = extract_folder
        self.flat_data_module_name = flat_data_module_name

        self.lower_fb_name_modules: dict[str, type] = {}
        self.dump_wrapper_lib: ModuleType
        self.repack_wrapper_lib: ModuleType

        self.__import_modules()

    def __import_modules(self):
        try:
            flat_data_lib = importlib.import_module(self.flat_data_module_name)
            self.dump_wrapper_lib = importlib.import_module(
                f"{self.flat_data_module_name}.dump_wrapper"
            )
            self.repack_wrapper_lib = importlib.import_module(
                f"{self.flat_data_module_name}.repack_wrapper"
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

    def _process_bytes_file(
            self, file_name: str, data: bytes, use_pure=False
    ) -> tuple[dict[str, Any], str]:
        """Extract flatbuffer bytes file to dict

        Args:
            file_name (str): Schema name of data.
            data (bytes): Flatbuffer data to extract.

        Returns:
            tuple[dict[str, Any], str]: Tuple with extracted dict and file name. Always have file name if success extract.
        """
        if not (
                flatbuffer_class := self.lower_fb_name_modules.get(
                    file_name.removesuffix(".bytes").lower(), None
                )
        ):
            return {}, ""

        obj = None
        try:
            if flatbuffer_class.__name__.endswith("Table"):
                try:
                    if not file_name.endswith(
                            ".bytes") or Config.server != "CN":  # CN does not encrypt its Excel.zip (but does encrypt tables in sqlite3 databases such as ExcelDB.db)
                        data = xor_with_key(flatbuffer_class.__name__, data)
                    flat_buffer = getattr(flatbuffer_class, "GetRootAs")(data)
                    obj = getattr(self.dump_wrapper_lib, "dump_table")(flat_buffer, b"", use_pure)
                except:
                    pass

            if not obj:
                flat_buffer = getattr(flatbuffer_class, "GetRootAs")(data)
                obj = getattr(
                    self.dump_wrapper_lib, f"dump_{flatbuffer_class.__name__}"
                )(flat_buffer, b"", use_pure)
            return (obj, f"{flatbuffer_class.__name__}.json")
        except:
            # if json_data := self.__process_json_file(file_name, data):
            #     return json.loads(json_data), f"{file_name}.json"
            return {}, ""

    def _repack_bytes_file(
            self, file_name: str, json_data: Union[dict, list], encrypt=True, xor_encrypt=True, use_pure=False
    ) -> tuple[bytes, str]:
        """Repack dict to encrypted flatbuffer bytes

        Args:
            file_name (str): File name of json.
            json_data (dict | list): Content to repack.

        Returns:
            tuple[bytes, str]: Tuple with encrypted bytes and original bytes file name.
        """
        base_name = file_name.removesuffix(".json").lower()
        if not (
                flatbuffer_class := self.lower_fb_name_modules.get(base_name, None)
        ):
            return b"", ""

        try:
            # 逻辑如下
            # 先使用pack_{class_name} 进行序列化（序列化后需要进行xor字段加密，repack_wrapper已写应对方式），xor密钥为字段名
            # 随后进行xor加密（密钥为FlatData表名）
            class_name = flatbuffer_class.__name__
            pack_func_name = f"pack_{class_name}"
            pack_func = getattr(self.repack_wrapper_lib, pack_func_name, None)

            if not pack_func:
                return b"", ""

            builder = flatbuffers.Builder(4096)
            offset = pack_func(builder, json_data, encrypt, use_pure)
            builder.Finish(offset)
            bytes_output = bytes(builder.Output())

            # 与解压同流程加密
            if not (file_name.endswith(".bytes") and Config.server == "CN") and xor_encrypt:
                bytes_output = xor_with_key(class_name, bytes_output)

            return bytes_output, f"{base_name}.bytes"
        except:
            return b"", ""

    def _process_json_file(self, data: bytes) -> bytes:
        """Extract json file in zip.

        Args:
            file_name (str): File name.
            data (bytes): Data of file.

        Returns:
            bytes: Bytes of json data.
        """
        try:
            data.decode("utf8")
            return data
        except:
            return bytes()

    def _process_db_file(self, file_path: str, table_name: str = "", use_pure=False) -> list[DBTable]:
        """Extract sqlite database file.

        Args:
            file_path (str): Database path.
            table_name (str): Specify table to extract.

        Returns:
            list[DBTable]: A list of DBTables.
        """
        with TableDatabase(file_path) as db:
            tables = []

            table_list = [table_name] if table_name else db.get_table_list()

            for table in table_list:
                columns = db.get_table_column_structure(table)
                rows: list[tuple] = db.get_table_data(table)[1]
                table_data = []
                for row in rows:
                    row_data: list[Any] = []
                    for col, value in zip(columns, row):
                        col_type = SQLiteDataType[col.data_type].value
                        if col_type == bytes:
                            data, _ = self._process_bytes_file(
                                table.replace("DBSchema", "Excel"), value, use_pure
                            )
                            row_data.append(data)
                        elif col_type == bool:
                            row_data.append(bool(value))
                        else:
                            row_data.append(value)

                    table_data.append(row_data)
                tables.append(DBTable(table, columns, table_data))
            return tables

    def _process_zip_file(
            self,
            file_name: str,
            file_data: bytes,
            detect_type: bool = False,
    ) -> tuple[bytes, str, bool]:
        data = bytes()
        if (detect_type or file_name.endswith(".json")) and (
                data := self._process_json_file(file_data)
        ):
            return data, "", True

        if detect_type or file_name.endswith(".bytes"):
            b_data = self._process_bytes_file(file_name, file_data)
            file_dict, file_name = b_data
            if file_name:
                return (
                    json.dumps(file_dict, indent=4, ensure_ascii=False).encode("utf8"),
                    file_name,
                    True,
                )
        return data, "", False

    def extract_db_file(self, file_path: str, use_pure=False) -> bool:
        """Extract db file."""
        try:
            if db_tables := self._process_db_file(
                    path.join(self.table_file_folder, file_path), "", use_pure
            ):
                db_name = file_path.removesuffix(".db")
                for table in db_tables:
                    db_extract_folder = path.join(self.extract_folder, db_name)
                    os.makedirs(db_extract_folder, exist_ok=True)
                    with open(
                            path.join(db_extract_folder, f"{table.name.replace('DBSchema', 'Excel')}.json"),
                            "wt",
                            encoding="utf8",
                    ) as f:
                        json.dump(
                            TableDatabase.convert_to_list_dict(table),
                            f,
                            indent=4,
                            ensure_ascii=False,
                        )
                return True
            return False
        except Exception as e:
            print(f"Error when process {file_path}: {e}")
            return False

    def extract_zip_file(self, file_name: str) -> None:
        """Extract zip file."""
        try:
            zip_extract_folder = path.join(
                self.extract_folder, file_name.removesuffix(".zip")
            )
            os.makedirs(zip_extract_folder, exist_ok=True)

            password = zip_password(path.basename(file_name))
            with ZipFile(path.join(self.table_file_folder, file_name), "r") as zip:
                zip.setpassword(password)
                for item_name in zip.namelist():
                    item_data = zip.read(item_name)

                    data, name, success = bytes(), "", False
                    if item_name.endswith((".json", ".bytes")):
                        if "RootMotion" in file_name:
                            data, name, success = self._process_zip_file(
                                f"{file_name.removesuffix('.zip')}Flat", item_data, True
                            )
                            name = item_name
                        else:
                            data, name, success = self._process_zip_file(
                                item_name, item_data
                            )

                    if not success:
                        data, name, success = self._process_zip_file(
                            item_name, item_data, True
                        )
                    if success:
                        item_name = name if name else item_name
                        item_data = data
                    else:
                        notice(
                            f"The file {item_name} in {file_name} is not be implementate or cannot process."
                        )
                        continue

                    with open(path.join(zip_extract_folder, item_name), "wb") as f:
                        f.write(item_data)
        except Exception as e:
            notice(f"Error when process {file_name}: {e}")

    def repack_to_zip(self, file_name: str) -> None:
        """Repack JSON files back to original zip file."""
        try:
            zip_path = path.join(self.table_file_folder, file_name)
            password = zip_password(path.basename(file_name)) if Config.server != "CN" else None
            print(f"repack的压缩包密码:{password}")
            # 解压到临时目录，extract_zip_file不是我写的懒得改
            os.makedirs("Temp", exist_ok=True)
            ZipUtils.extract_zip(
                zip_path=zip_path,
                dest_dir="Temp",
                password=password,
                progress_bar=False
            )
            # self.extract_folder/Excel路径即为需打包的json路径，Replacement需要大改
            # 检查文件在不在写回目录
            for root, _, files in os.walk(path.join(self.extract_folder, "Excel")):
                for file in files:
                    if file.endswith(".json"):
                        with open(path.join(root, file), 'r', encoding='utf8') as f:
                            json_data = json.load(f)

                        item_data, new_name = self._repack_bytes_file(file, json_data, False)

                        if new_name:
                            # 将修改后的数据写回临时目录以备重新打包
                            target_file_path = path.join("Temp", new_name)  # 命中单个文件
                            with open(target_file_path, "wb") as f:
                                f.write(item_data)

            # 重新打包
            print(f"repack重新打包的压缩包密码:{password}")
            success = ZipUtils.create_zip(
                file_paths=os.listdir("Temp"),
                dest_zip=zip_path,
                base_dir="Temp",
                password=password,
                progress_bar=True
            )

            if success:
                notice(f"Successfully repacked {file_name}")

            shutil.rmtree("Temp", ignore_errors=True)

        except Exception as e:
            notice(f"Error when repack {file_name}: {e}")

    def repack_to_db(self, file_name: str, use_pure=False) -> None:
        """Repack JSON files back to original sqlite database."""
        try:
            db_name = file_name.removesuffix(".db")
            db_extract_folder = path.join(self.extract_folder, db_name)

            db_path = path.join(self.table_file_folder, file_name)

            with TableDatabase(db_path) as db:
                json_files = [f for f in os.listdir(db_extract_folder) if f.endswith(".json")]
                total_files = len(json_files)

                for index, file in enumerate(json_files):
                    # if not file.__contains__("ScenarioScriptExcel"):
                    #     continue
                    table_name = file.removesuffix(".json").replace("Excel", "DBSchema")
                    print(f"[{index + 1}/{total_files}] 正在转换数据表: {table_name} ...", end="\r")

                    with open(path.join(db_extract_folder, file), 'r', encoding='utf8') as f:
                        json_data = json.load(f)

                    columns = db.get_table_column_structure(table_name)
                    column_names = [col.name for col in columns]
                    column_names_real, rows = db.get_table_data(table_name)
                    dic_rows = []
                    for each_row in rows:
                        each_dic = {}
                        for i, row_ele in enumerate(each_row):
                            each_dic[column_names_real[i]] = row_ele
                        dic_rows.append(each_dic)

                    new_rows = []
                    for item in json_data:
                        row = []
                        find = True
                        byte_data, _ = self._repack_bytes_file(file, item, False, False, use_pure)
                        if table_name.__contains__("CharacterDialogEvent") and not use_pure:
                            item, _ = self._process_bytes_file(file.removesuffix(".json"), byte_data, True)
                            find = True
                        for col in columns:
                            if col.name == "Bytes":
                                if table_name.__contains__("CharacterDialogEvent"):
                                    for each_row in dic_rows:
                                        if each_row['Bytes'] == byte_data:
                                            find = True
                                            break
                                row.append(byte_data)
                            else:
                                row.append(item.get(col.name))
                        if not find:
                            print(item)
                            print(row)
                            print("\n".join(
                                [str(each_dic) for each_dic in dic_rows if each_dic['CostumeUniqueId'] == 1900901801]))
                            raise RuntimeError("bytes流从未存在，此json存在打包bug")
                        new_rows.append(row)

                    print(f"正在写入数据库 {table_name} ({len(new_rows)} 行)...")
                    db.update_table_data(table_name, column_names, new_rows)
                    print(f"{table_name} 写入完成。")

                print("正在优化数据库文件大小...")
                db.execute("VACUUM")

                notice(f"Successfully repacked {file_name}")
        except Exception as e:
            notice(f"Error when repack {file_name}: {e}", "error")

    def process_table(self, file_path: str, type: str = "Extract", use_pure=False) -> None:
        """Extract or Repack a table by file path.

        Args:
            file_path (str): Relative path of .zip or .db.
            repack (bool): If True, repack data from extract folder back to file_path.
        """
        if not file_path.endswith((".zip", ".db")):
            notice(f"The file {file_path} is not supported in current implementation.")
            return

        if file_path.endswith(".zip"):
            if type == "Repack":
                self.repack_to_zip(file_path)
            else:
                self.extract_zip_file(file_path)

        if file_path.endswith(".db"):
            if type == "Repack":
                self.repack_to_db(file_path, use_pure)
            else:
                self.extract_db_file(file_path, use_pure)
