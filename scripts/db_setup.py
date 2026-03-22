import sqlite3
import config
import os

def setup():
    # Buat direktori data jika belum ada
    data_dir = os.path.dirname(config.DB_FILE)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir)

    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()

    # Tabel History Trading
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trade_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        ticket INTEGER,
        type TEXT,
        price REAL,
        result TEXT,
        ai_reason TEXT
    )
    ''')

    # Tabel Insight Jangka Panjang
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS long_term_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_time TEXT,
        win_rate TEXT,
        total_evaluated INTEGER,
        insight TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {config.DB_FILE}")

if __name__ == "__main__":
    setup()
