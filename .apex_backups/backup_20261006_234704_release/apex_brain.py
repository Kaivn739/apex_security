import os
import time
import psutil
import sqlite3
from datetime import datetime


class APEXBrainCore:
    def __init__(self, db_path="apex_security.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """دروستکردنی داتابەیسی سەربەخۆی APEX بۆ کۆکردنەوەی داتاکان"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # خشتەی داتای تارگێتەکان
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                target_type TEXT,
                status TEXT,
                plate_or_id TEXT,
                created_at TEXT
            )
        """)

        # خشتەی ئەرشیفی ئاگادارییەکان
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_or_id TEXT,
                target_name TEXT,
                status TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

    def get_system_health(self):
        """چاودێریکردنی ڕاستەوخۆی سەرچاوەکانی CPU و RAM"""
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram_usage = psutil.virtual_memory().percent
        return {"cpu": cpu_usage, "ram": ram_usage}

    def log_alert(self, plate_or_id, name, status):
        """تۆمارکردنی ئاگاداریی نوێ لە داتابەیسدا"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO alert_logs (plate_or_id, target_name, status, timestamp)
            VALUES (?, ?, ?, ?)
        """,
            (plate_or_id, name, status, now),
        )
        conn.commit()
        conn.close()

    def get_all_data_summary(self):
        """کۆکردنەوەی گشت داتاکان بۆ نیشاندانی لە شاشەی APEX DATA"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM targets")
        total_targets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM alert_logs")
        total_alerts = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM alert_logs ORDER BY id DESC LIMIT 10")
        recent_logs = cursor.fetchall()

        conn.close()
        return {
            "total_targets": total_targets,
            "total_alerts": total_alerts,
            "recent_logs": recent_logs,
        }