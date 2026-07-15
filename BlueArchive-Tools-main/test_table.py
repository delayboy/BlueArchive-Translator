# -*- coding: utf-8 -*-
"""
SQLite3 测试脚本
功能：读取当前目录下的 ExcelDB.db，打印数据库内所有表名
"""

import sqlite3
import os
import sys


def list_tables(db_path: str) -> list:
    """查询 SQLite 数据库中的所有表名"""
    # 检查文件是否存在
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"数据库文件不存在：{db_path}")

    # 连接数据库
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        # sqlite_master 是 SQLite 的系统表，存储数据库结构信息
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name;"
        )
        # 取出每个表名（结果第一列）
        tables = [row[0] for row in cursor.fetchall()]
        return tables
    finally:
        conn.close()


def main():
    # 数据库文件路径：当前脚本所在目录下的 ExcelDB.db
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ExcelDB.db")

    print(f"数据库文件路径：{db_path}")
    print("-" * 50)

    try:
        tables = list_tables(db_path)
        if tables:
            print(f"共找到 {len(tables)} 个表：\n")
            for idx, name in enumerate(tables, start=1):
                print(f"  {idx:>3}. {name}")
        else:
            print("数据库中没有用户表。")
    except Exception as e:
        print(f"发生错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
