# db.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "services.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Global monitor settings (singleton row)
    cursor.execute("""
        CREATE TABLE monitor_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                auto_restart INTEGER NOT NULL DEFAULT 0,      
                alerts_enabled INTEGER NOT NULL DEFAULT 1,   
                whatsapp_enabled INTEGER NOT NULL DEFAULT 0,
                whatsapp_number TEXT,                        
                email_enabled INTEGER NOT NULL DEFAULT 0,
                primary_email TEXT,
                secondary_email TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
    """)

    # Ensure single row exists
    cursor.execute("""
        INSERT OR IGNORE INTO monitor_settings (id)
        VALUES (1);
    """)

    # Services being monitored
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitored_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL UNIQUE,
            notify_on_fail INTEGER NOT NULL DEFAULT 1,
            last_status TEXT DEFAULT 'unknown',
            last_checked_at TEXT,
            down_since TEXT,
            last_notified_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("✅ Database initialized")
