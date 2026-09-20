import sqlite3
from typing import Union

DB_NAME = "apex_security.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alpr_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_name TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def log_alpr_event(plate_number: str, confidence: float = 0.0):
    """پاشەکەوتکردنی تابلۆ بە شێوازی دەق (String)"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO alpr_logs (plate_number, confidence) VALUES (?, ?)",
            (str(plate_number), float(confidence)),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging ALPR: {e}")


def log_face_event(target_name: str, status: str = "MATCHED"):
    """پاشەکەوتکردنی ناوی ڕووخسار بە شێوازی دەق"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO face_logs (target_name, status) VALUES (?, ?)",
            (str(target_name), str(status)),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging Face: {e}")


if __name__ == "__main__":
    init_db()
