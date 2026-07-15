import sqlcipher3 as sqlite3

from lib.structure import DBColumn, DBTable
from utils.config import Config
KEY_HEX = "efa143094711b6563ec2132d4d6bbe8533d4e291ed4820bdb515b26bb57bb3f0"
class TableDatabase:
    def __init__(self, database: str) -> None:
        self.database = database
        self.connection = sqlite3.connect(self.database)
        cursor = self.connection.cursor()
    # Hex key format - SQLCipher treats this as a raw 32-byte key (no KDF)
        cursor.execute(f"PRAGMA key = \"x'{KEY_HEX}'\";")
        try:
            cursor.execute("SELECT count(*) FROM sqlite_master;")
            print("数据库连接成功！")
        except Exception as e:
            print(f"连接失败，可能是密钥错误或格式不对: {e}")

    def __enter__(self) -> "TableDatabase":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.connection.close()

    def execute(self, sql: str) -> None:
        cursor = self.connection.cursor()
        cursor.execute(sql)
        self.connection.commit()

    def get_table_list(self) -> list[str]:
        """Get all table name in database as list.

        Returns:
            list[tuple]: Tables
        """
        cursor = self.connection.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

        return [table[0] for table in cursor.fetchall() if table]

    def get_table_column_structure(self, table: str) -> list[DBColumn]:
        """Get data structure of table.

        Args:
            table (str): table_name

        Returns:
            list[Column]: A list store all columns structure.
        """
        cursor = self.connection.cursor()

        cursor.execute(f"PRAGMA table_info({table});")

        return [DBColumn(name=col[1], data_type=col[2]) for col in cursor.fetchall()]

    def get_table_data(self, table: str) -> tuple[list, list]:
        """Get all rows and table structure in table.

        Args:
            table (str): table_name

        Returns:
            tuple[list, list]: First list store the column_names. Second list store the rows.
        """
        cursor = self.connection.cursor()

        cursor.execute(f"SELECT * FROM {table};")

        column_names = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        return column_names, rows

    def update_table_data(self, table: str, column: list[str], data: list[list]) -> None:
        cursor = self.connection.cursor()
        error_sql = ""
        try:
            cursor.execute("PRAGMA synchronous = OFF;")
            cursor.execute("PRAGMA journal_mode = MEMORY;") 
            
            cursor.execute("BEGIN TRANSACTION;")
            
            print(f"正在清空旧表 {table}...")
            error_sql = f"DELETE FROM {table};"
            cursor.execute(f"DELETE FROM {table};")
            
            placeholders = ", ".join(["?"] * len(column))
            format_col = []
            for col_name in column:
                if col_name.__eq__("Group"):
                    format_col.append('`Group`')
                else:
                    format_col.append(col_name)
            sql = f"INSERT INTO {table} ({', '.join(format_col)}) VALUES ({placeholders});"
            error_sql = sql
            print(f"正在批量插入 {len(data)} 行数据...")
            cursor.executemany(sql, data)
            
            self.connection.commit()
            print(f"表 {table} 更新成功！")
        except Exception as e:
            self.connection.rollback()
            print(f"数据库写入失败，已回滚: {error_sql}\n{e}")
            raise e

    @staticmethod
    def convert_to_list_dict(table: DBTable) -> list[dict]:
        """Convert table to list of json structure dict.

        Args:
            table (DBTable): Table to convert.

        Returns:
            list[dict]: A list include all the rows to key value pair.
        """
        table_rows = []
        for row in table.data:
            row_data = {}
            for col, value in zip(table.columns, row):
                row_data[col.name] = value
            if row_data:
                table_rows.append(row_data)
        table_rows = [struct["Bytes"] for struct in table_rows] # Do not serialize duplicate data; We can figure out which ones are keys while repacking...
        return table_rows