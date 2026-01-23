# db.py
import sqlite3
from pathlib import Path



DB_PATH = "./services.db"

def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Global monitor settings (singleton row)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitor_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            auto_restart INTEGER NOT NULL DEFAULT 0,
            alerts_enabled INTEGER NOT NULL DEFAULT 1,
            whatsapp_enabled INTEGER NOT NULL DEFAULT 0,
            whatsapp_number TEXT,  -- store WhatsApp info as JSON
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
# db_helpers.py (add this)

import json
from db import get_connection

def upsert_monitor_settings(
    auto_restart=None,
    alerts_enabled=None,
    whatsapp_enabled=None,
    whatsapp_number=None,  # can be dict
    email_enabled=None,
    primary_email=None,
    secondary_email=None
):
    conn = get_connection()
    cursor = conn.cursor()

    # convert whatsapp_number dict to JSON string
    if isinstance(whatsapp_number, dict):
        whatsapp_number_str = json.dumps(whatsapp_number)
    else:
        whatsapp_number_str = whatsapp_number or ''

    # check if row exists
    cursor.execute("SELECT COUNT(*) FROM monitor_settings WHERE id = 1")
    exists = cursor.fetchone()[0]

    if exists == 0:
        # Insert default row
        cursor.execute("""
            INSERT INTO monitor_settings (
                id, auto_restart, alerts_enabled, whatsapp_enabled, whatsapp_number,
                email_enabled, primary_email, secondary_email
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (
            auto_restart or 0,
            alerts_enabled if alerts_enabled is not None else 1,
            whatsapp_enabled or 0,
            whatsapp_number_str,
            email_enabled or 0,
            primary_email or '',
            secondary_email or ''
        ))
    else:
        # Update existing row
        cursor.execute("""
            UPDATE monitor_settings
            SET auto_restart = ?,
                alerts_enabled = ?,
                whatsapp_enabled = ?,
                whatsapp_number = ?,
                email_enabled = ?,
                primary_email = ?,
                secondary_email = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (
            auto_restart if auto_restart is not None else 0,
            alerts_enabled if alerts_enabled is not None else 1,
            whatsapp_enabled if whatsapp_enabled is not None else 0,
            whatsapp_number_str,
            email_enabled if email_enabled is not None else 0,
            primary_email or '',
            secondary_email or ''
        ))

    conn.commit()
    conn.close()


# ----------------------------
# Monitor Settings (singleton)
# ----------------------------
def get_monitor_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitor_settings WHERE id = 1")
    row = cursor.fetchone()

    # grab column names before closing connection
    keys = [desc[0] for desc in cursor.description]
    conn.close()

    if row:
        data = dict(zip(keys, row))
        # convert whatsapp_number back to dict if it's JSON
        try:
            data["whatsapp_number"] = json.loads(data.get("whatsapp_number") or "{}")
        except json.JSONDecodeError:
            data["whatsapp_number"] = {}
        return data

    return None


# ----------------------------
# Monitored Services
# ----------------------------
def get_monitored_services():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitored_services")
    rows = cursor.fetchall()
    keys = [desc[0] for desc in cursor.description]
    services = [dict(zip(keys, row)) for row in rows]
    conn.close()
    return services


def add_monitored_service(service_name, notify_on_fail=True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO monitored_services (service_name, notify_on_fail)
        VALUES (?, ?)
    """, (service_name, 1 if notify_on_fail else 0))
    conn.commit()
    conn.close()
if __name__ == "__main__":
    init_db()
    print("✅ Database initialized")
