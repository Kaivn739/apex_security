import sqlite3

DB_NAME = "apex_security.db"

def get_connection():
    """دابینکردنی پەیوەندی لەگەڵ داتا بەیسی لۆکاڵی"""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    """دروستکردنی خشتە بنەڕەتییەکان ئەگەر نەبن"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # خشتەی بەکارهێنەران بۆ سیستمی چوونەژوورەوە
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # خشتەی لۆگەکانی ئەمنی و ناسینەوەی ڕوخسار
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT
        )
    """)
    
    # دروستکردنی ئەکاونتێکی سەرەتایی (Admin) بە شێوازی ڕاستی SQL
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, username, password, role)
        VALUES (1, 'admin', 'admin123', 'administrator')
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database and tables initialized successfully.")