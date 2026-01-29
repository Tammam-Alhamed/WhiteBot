import sqlite3
import json
import os

DB_FILE_SQLITE = "bot_database.db"
# ملفات JSON القديمة
USERS_FILE = "users_db1.json"
PENDING_FILE = "pending_orders.json"
DEPOSITS_FILE = "deposit_requests.json"
REPORTS_FILE = "reports_metadata.json"


def create_tables(cursor):
    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            balance REAL DEFAULT 0.0,
            banned BOOLEAN DEFAULT 0,
            total_deposited REAL DEFAULT 0.0,
            joined_at TEXT,
            is_admin BOOLEAN DEFAULT 0
        )
    """)

    # جدول الطلبات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            product TEXT,
            qty INTEGER,
            inputs TEXT,
            params TEXT,
            status TEXT,
            date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # جدول الإيداعات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deposit_requests (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            method TEXT,
            txn_id TEXT,
            amount REAL,
            proof_image_id TEXT,
            date TEXT,
            status TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # جدول بيانات التقارير
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)


def migrate():
    print("🚀 جاري بدء عملية النقل إلى SQLite...")
    conn = sqlite3.connect(DB_FILE_SQLITE)
    cursor = conn.cursor()
    create_tables(cursor)

    # 1. نقل المستخدمين
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            for uid, data in users_data.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO users (id, name, username, balance, banned, total_deposited, joined_at, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(uid),
                    data.get("name", "Unknown"),
                    data.get("username"),
                    data.get("balance", 0.0),
                    data.get("banned", False),
                    data.get("total_deposited", 0.0),
                    data.get("joined_at"),
                    data.get("is_admin", False)
                ))
            print(f"✅ تم نقل {len(users_data)} مستخدم.")
        except Exception as e:
            print(f"❌ خطأ في نقل المستخدمين: {e}")

    # 2. نقل الطلبات
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                orders_data = json.load(f)
            for order in orders_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO orders (id, user_id, product, qty, inputs, params, status, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(order.get("id")),
                    int(order.get("user_id")),
                    json.dumps(order.get("product", {})),
                    int(order.get("qty", 1)),
                    json.dumps(order.get("inputs", {})),
                    json.dumps(order.get("params", {})),
                    order.get("status"),
                    order.get("date")
                ))
            print(f"✅ تم نقل {len(orders_data)} طلب.")
        except Exception as e:
            print(f"❌ خطأ في نقل الطلبات: {e}")

    # 3. نقل الإيداعات
    if os.path.exists(DEPOSITS_FILE):
        try:
            with open(DEPOSITS_FILE, 'r', encoding='utf-8') as f:
                deposits_data = json.load(f)
            for dep in deposits_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO deposit_requests (id, user_id, method, txn_id, amount, proof_image_id, date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(dep.get("id")),
                    int(dep.get("user_id")),
                    dep.get("method"),
                    dep.get("txn_id"),
                    float(dep.get("amount", 0.0)),
                    dep.get("proof_image_id"),
                    dep.get("date"),
                    dep.get("status")
                ))
            print(f"✅ تم نقل {len(deposits_data)} طلب إيداع.")
        except Exception as e:
            print(f"❌ خطأ في نقل الإيداعات: {e}")

    # 4. نقل بيانات التقارير
    if os.path.exists(REPORTS_FILE):
        try:
            with open(REPORTS_FILE, 'r', encoding='utf-8') as f:
                reports_data = json.load(f)
            for key, value in reports_data.items():
                cursor.execute("INSERT OR REPLACE INTO reports_metadata (key, value) VALUES (?, ?)", (key, str(value)))
            print(f"✅ تم نقل بيانات التقارير.")
        except Exception as e:
            print(f"❌ خطأ في نقل التقارير: {e}")

    conn.commit()
    conn.close()
    print("\n🎉 تمت عملية النقل بنجاح! قاعدة البيانات الجديدة: bot_database.db")


if __name__ == "__main__":
    migrate()