from datetime import datetime
import sqlite3


def init_db():
  conn = sqlite3.connect("apex_security.db")
  cursor = conn.cursor()

  # دروستکردنی خشتەی بەکارهێنەران
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            sector TEXT
        )
    """)

  # دروستکردنی خشتەی لۆگ و چالاکییەکان
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            action_type TEXT,
            details TEXT
        )
    """)

  # پڕکردنەوەی داتای سەرەتایی ئەگەر خشتەکە خاڵی بێت
  cursor.execute("SELECT COUNT(*) FROM users")
  if cursor.fetchone()[0] == 0:
    default_users = [
        ("admin", "1234", "گشتی"),
        ("home_user", "1111", "ماڵەوە"),
        ("business_user", "2222", "بازرگانی"),
        ("gov_user", "9999", "حکومی و ئەمنی"),
    ]
    cursor.executemany(
        "INSERT INTO users (username, password, sector) VALUES (?, ?, ?)",
        default_users,
    )

  conn.commit()
  conn.close()


def verify_user_db(username, password):
  conn = sqlite3.connect("apex_security.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT sector FROM users WHERE username = ? AND password = ?",
      (username, password),
  )
  result = cursor.fetchone()
  conn.close()
  return result


def log_activity_db(action_type, details):
  try:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("apex_security.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (timestamp, action_type, details) VALUES (?, ?, ?)",
        (now, action_type, details),
    )
    conn.commit()
    conn.close()
  except:
    pass