"""Connect to encrypted ExcelDB.db and list all tables."""
import os
import sys
import sqlcipher3
import hashlib

PROJECT_ROOT = os.path.dirname(os.path.abspath("."))
DB_PATH = os.path.join(PROJECT_ROOT, r"BlueArchive_Data\StreamingAssets\PUB\Resource\Preload\TableBundles\ExcelDB.db")
KEY_HEX = "efa143094711b6563ec2132d4d6bbe8533d4e291ed4820bdb515b26bb57bb3f0"


def format_row(row, blob_index=None):
    """格式化行数据，将Blob字段显示为MD5"""
    formatted = []
    for i, value in enumerate(row):
        if blob_index is not None and i == blob_index:
            # 如果是Blob字段，计算MD5
            if value is not None:
                md5_hash = hashlib.md5(value).hexdigest()
                formatted.append(f"<MD5: {md5_hash}>")
            else:
                formatted.append("NULL")
        else:
            formatted.append(value)
    return tuple(formatted)


def connect():
    if not os.path.exists(DB_PATH):
        print(f"[!] DB not found: {DB_PATH}")
        sys.exit(1)

    print(f"[*] Opening {DB_PATH}")
    print(f"[*] File size: {os.path.getsize(DB_PATH):,} bytes")
    print(f"[*] Key: x'{KEY_HEX}'")
    print(f"[*] sqlcipher3 v{sqlcipher3.version}, SQLite v{sqlcipher3.sqlite_version}")

    conn = sqlcipher3.connect(DB_PATH)
    cur = conn.cursor()
    # Hex key format - SQLCipher treats this as a raw 32-byte key (no KDF)
    cur.execute(f"PRAGMA key = \"x'{KEY_HEX}'\";")

    # Verify the key by reading sqlite_master (will raise if key is wrong)
    try:
        cur.execute("SELECT count(*) FROM sqlite_master")
        count = cur.fetchone()[0]
        print(f"[+] Key valid. sqlite_master has {count} rows.")
    except sqlcipher3.DatabaseError as e:
        print(f"[-] Key verification failed: {e}")
        print("    Possible causes:")
        print("    - Wrong key bytes")
        print("    - SQLCipher version mismatch (try PRAGMA cipher_compatibility = 3 or 4)")
        conn.close()
        sys.exit(1)

    return conn


def list_tables(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT name, type FROM sqlite_master "
        "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    tables = cur.fetchall()

    print(f"\n[*] Found {len(tables)} tables/views:")
    print(f"    {'NAME':<55} {'TYPE':<6} {'ROWS':>10}")
    print(f"    {'-' * 55} {'-' * 6} {'-' * 10}")

    for name, type_ in tables:
        try:
            cur.execute(f'SELECT count(*) FROM "{name}"')
            rows = cur.fetchone()[0]
        except sqlcipher3.DatabaseError as e:
            rows = f"ERR ({e})"
        print(f"    {name:<55} {type_:<6} {str(rows):>10}")

    # Show CREATE statement for the first table as a sanity check
    if tables:
        first = tables[0][0]
        cur.execute(f"SELECT sql FROM sqlite_master WHERE name = ?", (first,))
        create_sql = cur.fetchone()[0]
        print(f"\n[*] Schema preview ({first}):")
        for line in create_sql.split("\n"):
            print(f"    {line}")

        cur.execute(f"SELECT * FROM CharacterDialogEventDBSchema LIMIT 1 ")
        results = cur.fetchall()

        # 获取列信息，找到Blob类型的列
        blob_columns = []
        for idx, desc in enumerate(cur.description):
            # 根据数据库类型判断是否为Blob
            # SQLite: desc[1] 可能是 bytes 或其他
            # MySQL: desc[1] 可能是 252 (BLOB)
            if desc[1] in (bytes, memoryview) or 'blob' in str(desc[1]).lower():
                blob_columns.append(idx)

        # 打印结果
        for row in results:
            formatted_row = list(row)
            for idx in blob_columns:
                if formatted_row[idx] is not None:
                    md5_hash = hashlib.md5(formatted_row[idx]).hexdigest()
                    print(formatted_row[idx])
                    formatted_row[idx] = f"<MD5: {md5_hash}>"
            print(tuple(formatted_row))

    return tables


def main():
    print("=" * 75)
    print("ExcelDB.db SQLCipher Connection Test")
    print("=" * 75)

    conn = connect()
    list_tables(conn)
    conn.close()
    print("\n[+] Done.")


if __name__ == "__main__":
    main()
