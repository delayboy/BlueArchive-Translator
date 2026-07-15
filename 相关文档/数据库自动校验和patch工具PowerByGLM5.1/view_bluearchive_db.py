"""Connect to encrypted ExcelDB.db and list all tables."""
import os
import sys
import sqlcipher3

DB_PATH = r"ExcelDB.db"
KEY_HEX = "efa143094711b6563ec2132d4d6bbe8533d4e291ed4820bdb515b26bb57bb3f0"


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
    print(f"    {'-'*55} {'-'*6} {'-'*10}")

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
