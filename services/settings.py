import sqlite3
import json
import os

# reuse DB name from logic, but to keep files decoupled we redefine or import.
# importing from database avoids circular imports if database doesn't import settings.
# database imports config, but not settings. So it is safe to act independently or share const.
DB_NAME = "whitebot.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_settings_table():
    """Ensure settings table exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()


def load_settings():
    init_settings_table()  # Ensure table exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()

    # Default values logic
    data = {
        "exchange_rate": 15000,
        "deposit_commission": 0.0,
        "margins": {"default": 1.0},
        "category_names": {}
    }

    # Update with DB values
    for row in rows:
        try:
            # We store complex values (dicts) as JSON strings in the 'value' column
            # Simple values (int/float) are also stored as strings/JSON
            val = json.loads(row['value'])
            data[row['key']] = val
        except:
            continue

    return data


def save_settings(data):
    init_settings_table()
    conn = get_db_connection()
    cursor = conn.cursor()

    for key, value in data.items():
        val_json = json.dumps(value, ensure_ascii=False)
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val_json))

    conn.commit()
    conn.close()


def get_setting(key, default=None):
    data = load_settings()
    return data.get(key, default)


def update_setting(key, value):
    # Optimization: Direct DB update
    init_settings_table()
    conn = get_db_connection()
    cursor = conn.cursor()
    val_json = json.dumps(value, ensure_ascii=False)
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val_json))
    conn.commit()
    conn.close()


# --- دوال النسب الجديدة (Logic preserved) ---
def get_margin_for_category(category_name):
    margins = get_setting("margins", {})
    if category_name in margins:
        return float(margins[category_name])
    return float(margins.get("default", 1.0))


def set_category_margin(category_name, value):
    data = load_settings()
    if "margins" not in data: data["margins"] = {}
    data["margins"][category_name] = float(value)
    save_settings(data)


def get_deposit_commission():
    return float(get_setting("deposit_commission", 0.0))


def set_deposit_commission(percentage):
    update_setting("deposit_commission", float(percentage))


def get_category_name(category_key):
    category_names = get_setting("category_names", {})
    return category_names.get(category_key, category_key)


def set_category_name(category_key, custom_name):
    data = load_settings()
    if "category_names" not in data:
        data["category_names"] = {}
    data["category_names"][category_key] = custom_name
    save_settings(data)