import sqlite3
from pathlib import Path
import shutil

def rebuild_database(db_path=Path("ExcelDB.db")):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    new_conn = sqlite3.connect(db_path.with_suffix(".tmp"))
    new_cursor = new_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    for table_name in tables:
        table_name = table_name[0]
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table_name}'")
        create_sql = cursor.fetchone()[0]
        new_cursor.execute(create_sql)
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        if rows:
            placeholders = ', '.join(['?'] * len(rows[0]))
            new_cursor.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
    new_conn.commit()
    new_conn.close()
    shutil.move(db_path.with_suffix(".tmp"), db_path)
    print("Optimization complete!")

if __name__ == "__main__":
    rebuild_database()
