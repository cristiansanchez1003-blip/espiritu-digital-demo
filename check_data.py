import sqlite3
import os

DB_FILE = "sabores_del_sur.db"

def check_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, fecha_vencimiento FROM productos LIMIT 10")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    conn.close()

if __name__ == "__main__":
    check_data()
