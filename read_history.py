import sqlite3
import config

def get_history():
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_history ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        print("--- LAST 10 TRADES ---")
        for r in rows:
            print(r)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_history()
