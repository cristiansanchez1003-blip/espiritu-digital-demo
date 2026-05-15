import sqlite3
import os

DB_FILE = "sabores_del_sur.db"

def check_schema():
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(productos)")
    columns = cursor.fetchall()
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()
