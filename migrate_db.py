import sqlite3
import os
from datetime import datetime, timedelta

DB_FILE = "sabores_del_sur.db"

def migrate():
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Add fecha_vencimiento column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE productos ADD COLUMN fecha_vencimiento TEXT")
        print("Column fecha_vencimiento added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column fecha_vencimiento already exists.")
        else:
            raise e

    # Update products with some dates
    # Set most to 30 days from now, and 6 to 5 days ago (expired)
    cursor.execute("SELECT id FROM productos")
    product_ids = [row[0] for row in cursor.fetchall()]
    
    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    expired_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    
    for i, pid in enumerate(product_ids):
        # Mark 6 products as expired
        if i < 6:
            cursor.execute("UPDATE productos SET fecha_vencimiento = ? WHERE id = ?", (expired_date, pid))
        else:
            cursor.execute("UPDATE productos SET fecha_vencimiento = ? WHERE id = ?", (future_date, pid))
            
    conn.commit()
    print(f"Updated {len(product_ids)} products with expiration dates.")
    conn.close()

if __name__ == "__main__":
    migrate()
