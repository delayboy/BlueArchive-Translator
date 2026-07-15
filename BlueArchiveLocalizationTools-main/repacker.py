import os
import importlib
from lib.console import notice
from pathlib import Path
import json
import flatbuffers
from lib.encryption import xor_with_key, create_key
from utils.config import Config
import sqlite3

class TableRepackerImpl:
    def __init__(self, flat_data_module_name):
        try:
            self.flat_data_lib = importlib.import_module(flat_data_module_name)
            self.repack_wrapper_lib = importlib.import_module(
                f"{flat_data_module_name}.repack_wrapper"
            )
        except Exception as e:
            notice(
                f"Cannot import FlatData module. Make sure FlatData is available in Extracted folder. {e}",
                "error",
            )
            
    def repackExcelZipJson(self, json_path: Path):
        table_type = json_path.stem
        if not table_type:
            raise ValueError("JSON data must include a 'table' key indicating the table type.")
        pack_func_name = f"pack_{table_type}"
        pack_func = getattr(self.repack_wrapper_lib, pack_func_name, None)
        if not pack_func:
            raise ValueError(f"No pack function found for table type: {table_type}.")
        with open(json_path, 'r', encoding = 'utf-8') as f:
            json_data = json.loads(f.read())
            builder = flatbuffers.Builder(4096)
            offset = pack_func(builder, json_data)
            builder.Finish(offset)
            bytes_output = bytes(builder.Output())
            if not Config.is_cn: # CN does not encrypt its Excel.zip (but does encrypt tables in sqlite3 databases such as ExcelDB.db)
                bytes_output = xor_with_key(table_type, bytes_output)
            return bytes_output
    def repackjson2db(self, json_path: Path, db_path: Path) -> None:
        table_type = json_path.stem
        table_name = table_type.replace("Excel", "DBSchema")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check table existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Table '{table_name}' not found")

        # Get columns and validate Bytes column
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]

        # Read JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Clear existing data (MATCH C# BEHAVIOR)
        cursor.execute(f"DELETE FROM {table_name};")

        # Prepare insert statement (MATCH C# PARAMETER BINDING)
        placeholders = ', '.join(['?'] * len(columns))
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Start transaction (MATCH C# BEHAVIOR)
        #cursor.execute("BEGIN TRANSACTION;")

        try:
            # Process each entry
            for entry in json_data:
                # Serialize FlatBuffers (MATCH C# IMPLEMENTATION)
                builder = flatbuffers.Builder(4096)
                
                pack_func = getattr(self.repack_wrapper_lib, f"pack_{table_type}", None)
                if not pack_func:
                    raise ValueError(f"Pack function for {table_type} not found")
                
                # Pack data
                #print(entry['Path'])
                offset = pack_func(builder, entry, False)
                builder.Finish(offset)
                bytes_output = bytes(builder.Output())
                flatbuffer_class = self.flat_data_lib.__dict__[table_type]
                flatbuffer_obj = getattr(flatbuffer_class, "GetRootAs")(bytes_output)
                #bytes_output = xor_with_key(table_type, bytes_output)

                # Build parameters in COLUMN ORDER
                row_values = []
                for col in columns:
                    if col == "Bytes":
                        row_values.append(bytes_output)
                    else:
                        # Match C# property binding
                        if col not in entry:
                            raise ValueError(f"Missing field {col} in JSON entry")
                        length_accessor = getattr(flatbuffer_obj, f"{col}Length", None)
                        item_accessor = getattr(flatbuffer_obj, col, None)

                        if callable(item_accessor):
                            row_values.append([item_accessor(i) for i in range(length_accessor())] if callable(length_accessor) else item_accessor())
                        else:
                            raise ValueError(f"No valid accessor found for field '{col}'")


                # Execute insert
                cursor.execute(insert_query, row_values)

            # Final commit
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Repacking failed: {str(e)}") from e
        finally:
            conn.close()
