import sqlite3
import json
import os
from datetime import datetime
import random
import config

DB_NAME = "whitebot.db"


# --- Database Connection & Initialization ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT,
        username TEXT,
        balance REAL DEFAULT 0.0,
        banned INTEGER DEFAULT 0,
        total_deposited REAL DEFAULT 0.0,
        is_admin INTEGER DEFAULT 0,
        joined_at TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_orders (
        uuid TEXT PRIMARY KEY,
        user_id INTEGER,
        order_id TEXT,
        product_name TEXT,
        price REAL,
        status TEXT DEFAULT 'pending',
        notified INTEGER DEFAULT 0,
        code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Orders Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        product_json TEXT,
        qty INTEGER,
        inputs_json TEXT,
        params_json TEXT,
        status TEXT,
        date TEXT,
        order_source TEXT DEFAULT 'LOCAL',
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    # Deposits Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deposits (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        method TEXT,
        txn_id TEXT,
        amount REAL,
        proof_image_id TEXT,
        date TEXT,
        status TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    # Reports Metadata Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reports_meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    # Remote Orders (UUIDs) Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS remote_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        order_uuid TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    
    # Run migrations
    _migrate_add_order_source_field()
    
    conn.close()


def _migrate_add_order_source_field():
    """Migrate: Add order_source field to orders table if it doesn't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(orders)")
        columns = {col[1] for col in cursor.fetchall()}
        
        if 'order_source' not in columns:
            # Add the column
            cursor.execute('ALTER TABLE orders ADD COLUMN order_source TEXT DEFAULT "LOCAL"')
            conn.commit()
            print("✅ Migration: Added order_source column to orders table")
        
        conn.close()
    except Exception as e:
        print(f"⚠️  Migration warning: {e}")


# --- Helper Functions ---

def _dict_factory_order(row):
    d = dict(row)
    d['product'] = json.loads(d['product_json']) if d.get('product_json') else {}
    d['inputs'] = json.loads(d['inputs_json']) if d.get('inputs_json') else {}
    d['params'] = json.loads(d['params_json']) if d.get('params_json') else {}
    return d


# --- User Management ---
def ensure_user_exists(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = str(user_id)

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    user = cursor.fetchone()

    if not user:
        cursor.execute('''
            INSERT INTO users (user_id, balance, banned, total_deposited)
            VALUES (?, 0.0, 0, 0.0)
        ''', (uid,))
        conn.commit()
        data = {uid: {"balance": 0.0, "banned": False, "total_deposited": 0.0}}
    else:
        data = {uid: dict(user)}
        data[uid]['banned'] = bool(data[uid]['banned'])

    conn.close()
    return data


def get_user_data(user_id):
    ensure_user_exists(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    conn.close()

    if row:
        d = dict(row)
        d['banned'] = bool(d['banned'])
        d['is_admin'] = bool(d.get('is_admin', 0))
        return d
    return None


def get_balance(user_id):
    ensure_user_exists(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    conn.close()
    return row['balance'] if row else 0.0


def add_balance(user_id, amount, is_deposit=False):
    ensure_user_exists(user_id)
    uid = str(user_id)
    amount_float = float(amount)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount_float, uid))

    if is_deposit:
        cursor.execute("UPDATE users SET total_deposited = total_deposited + ? WHERE user_id = ?", (amount_float, uid))

    conn.commit()

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
    new_bal = cursor.fetchone()['balance']
    conn.close()
    return new_bal


def get_total_deposited(user_id):
    ensure_user_exists(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_deposited FROM users WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    conn.close()
    return row['total_deposited'] if row else 0.0


def deduct_balance(user_id, amount):
    ensure_user_exists(user_id)
    uid = str(user_id)
    try:
        cost = float(amount)
    except:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    current = row['balance']
    if round(current, 4) >= round(cost, 4):
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, uid))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


# --- Ban System ---
def ban_user(user_id, status=True):
    ensure_user_exists(user_id)
    conn = get_db_connection()
    conn.execute("UPDATE users SET banned = ? WHERE user_id = ?", (1 if status else 0, str(user_id)))
    conn.commit()
    conn.close()


def is_banned(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT banned FROM users WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    conn.close()
    return bool(row['banned']) if row else False


# --- Pending Orders ---

def save_pending_order(user_id, product_data, qty, inputs, params):
    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    conn = get_db_connection()
    cursor = conn.cursor()

    while True:
        new_id = str(random.randint(10000, 99999))
        cursor.execute("SELECT 1 FROM orders WHERE id = ?", (new_id,))
        if not cursor.fetchone():
            break

    cursor.execute('''
        INSERT INTO orders (id, user_id, product_json, qty, inputs_json, params_json, status, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        new_id,
        str(user_id),
        json.dumps(product_data, ensure_ascii=False),
        qty,
        json.dumps(inputs, ensure_ascii=False),
        json.dumps(params, ensure_ascii=False),
        "pending",
        now
    ))
    conn.commit()
    conn.close()
    return new_id


def get_pending_orders():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return [_dict_factory_order(row) for row in rows]


def get_all_orders():
    """جلب كل الطلبات للأدمن"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders")
    rows = cursor.fetchall()
    conn.close()
    return [_dict_factory_order(row) for row in rows]


def get_user_local_orders(user_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ?", (str(user_id),))
    rows = cursor.fetchall()
    conn.close()
    return [_dict_factory_order(row) for row in rows]


def get_pending_order_by_id(order_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (str(order_id),))
    row = cursor.fetchone()
    conn.close()
    return _dict_factory_order(row) if row else None


def update_order_status(order_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, str(order_id)))
    changes = cursor.rowcount
    conn.commit()
    conn.close()
    return changes > 0


def remove_pending_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id = ?", (str(order_id),))
    conn.commit()
    conn.close()


# --- User Info Updates ---
def update_user_info(user_id, first_name, username):
    ensure_user_exists(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ?, username = ? WHERE user_id = ?",
                   (first_name, username if username else "No User", str(user_id)))
    conn.commit()
    conn.close()


def get_all_users_list():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    conn.close()

    users_list = []
    for row in rows:
        users_list.append({
            "id": row['user_id'],
            "name": row['name'] or "Unknown",
            "username": row['username'] or "",
            "balance": row['balance'],
            "banned": bool(row['banned'])
        })
    return users_list


def get_all_user_ids():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [row['user_id'] for row in rows]


def get_all_admin_ids():
    conn = get_db_connection()
    cursor = conn.cursor()

    admin_ids = set()
    for aid in config.ADMIN_IDS:
        admin_ids.add(int(aid))

    cursor.execute("SELECT user_id FROM users WHERE is_admin = 1")
    rows = cursor.fetchall()
    for row in rows:
        try:
            admin_ids.add(int(row['user_id']))
        except:
            continue

    conn.close()
    return list(admin_ids)


# --- Deposit Requests ---

def save_deposit_request(user_id, method, txn_id, amount, proof_image_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    while True:
        req_id = str(random.randint(10000, 99999))
        cursor.execute("SELECT 1 FROM deposits WHERE id = ?", (req_id,))
        if not cursor.fetchone():
            break

    date_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

    cursor.execute('''
        INSERT INTO deposits (id, user_id, method, txn_id, amount, proof_image_id, date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (req_id, str(user_id), method, txn_id, float(amount), proof_image_id, date_str, "pending"))

    conn.commit()
    conn.close()

    return {
        "id": req_id,
        "user_id": user_id,
        "method": method,
        "txn_id": txn_id,
        "amount": float(amount),
        "proof_image_id": proof_image_id,
        "date": date_str,
        "status": "pending"
    }


def get_deposit_request(req_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deposits WHERE id = ?", (str(req_id),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_deposit_requests():
    """جلب كل طلبات الإيداع للأدمن"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deposits")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def remove_deposit_request(req_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deposits WHERE id = ?", (str(req_id),))
    conn.commit()
    conn.close()


# --- Reports Functions ---

def get_completed_orders():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE status = 'completed'")
    rows = cursor.fetchall()
    conn.close()
    return [_dict_factory_order(row) for row in rows]


def get_orders_by_date_range(start_date, end_date):
    completed_orders = get_completed_orders()
    filtered = []

    for order in completed_orders:
        order_date_str = order.get("date", "")
        if not order_date_str:
            continue
        try:
            order_date = datetime.strptime(order_date_str.split()[0], "%Y-%m-%d")
            if start_date.date() <= order_date.date() <= end_date.date():
                filtered.append(order)
        except (ValueError, IndexError):
            continue
    return filtered


def load_reports_metadata():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM reports_meta")
    rows = cursor.fetchall()
    conn.close()

    data = {
        "last_daily": None,
        "last_weekly": None,
        "last_monthly": None
    }
    for row in rows:
        data[row['key']] = row['value']
    return data


def save_reports_metadata(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    for k, v in data.items():
        cursor.execute("INSERT OR REPLACE INTO reports_meta (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()


def update_last_report_date(report_type, date_str):
    conn = get_db_connection()
    cursor = conn.cursor()
    key = f"last_{report_type}"
    cursor.execute("INSERT OR REPLACE INTO reports_meta (key, value) VALUES (?, ?)", (key, date_str))
    conn.commit()
    conn.close()


def get_last_report_date(report_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM reports_meta WHERE key = ?", (f"last_{report_type}",))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None


def register_user(user_id, name, username):
    ensure_user_exists(user_id)
    update_user_info(user_id, name, username)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT joined_at FROM users WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    if row and not row['joined_at']:
        cursor.execute("UPDATE users SET joined_at = ? WHERE user_id = ?", (str(datetime.now()), str(user_id)))
        conn.commit()
    conn.close()


def set_admin(user_id, is_admin=True):
    ensure_user_exists(user_id)
    conn = get_db_connection()
    conn.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (1 if is_admin else 0, str(user_id)))
    conn.commit()
    conn.close()


def is_user_admin(user_id):
    if user_id in config.ADMIN_IDS:
        return True

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    conn.close()
    return bool(row['is_admin']) if row else False


def is_super_admin(user_id):
    return user_id in config.ADMIN_IDS



def init_api_orders_table():
    """إنشاء جدول تتبع طلبات API إذا لم يكن موجوداً"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_orders (
        uuid TEXT PRIMARY KEY,
        user_id TEXT,
        order_id TEXT,
        product_name TEXT,
        price REAL,
        status TEXT,
        notified INTEGER DEFAULT 0,
        code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

def log_api_order(user_id, uuid, product_name, price, status="pending", order_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        init_api_orders_table()
        # هنا التعديل المهم: إضافة order_id
        cursor.execute('''
            INSERT OR IGNORE INTO api_orders (uuid, user_id, product_name, price, status, order_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(uuid), str(user_id), product_name, float(price), status, str(order_id) if order_id else None))
        conn.commit()
    except Exception as e:
        print(f"❌ DB Log Error: {e}")
    finally:
        conn.close()


def get_pending_api_orders():
    """جلب الطلبات المعلقة لفحصها"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # نجلب الطلبات التي لم تكتمل ولم يتم إلغاؤها
    cursor.execute("SELECT * FROM api_orders WHERE status NOT IN ('completed', 'Success', 'rejected', 'Canceled', 'Fail')")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_api_history(user_id, limit=20):
    """جلب سجل طلبات API لمستخدم معين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM api_orders 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT ?
    ''', (int(user_id), limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_pending_api_uuids():
    """جلب الطلبات التي لم تكتمل بعد لفحصها (للمجدول)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # نجلب الطلبات التي ليست مكتملة وليست ملغية/مرفوضة
    cursor.execute('''
        SELECT uuid, user_id FROM api_orders 
        WHERE status NOT IN ('completed', 'Success', 'accept', 'rejected', 'Canceled', 'Fail')
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_api_order_status(uuid, status, code=None, notified=0):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "UPDATE api_orders SET status = ?, notified = ?"
    params = [status, int(notified)]

    if code:
        query += ", code = ?"
        params.append(code)

    query += " WHERE uuid = ?"
    params.append(str(uuid))

    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()


def get_all_recent_api_orders(limit=50):
    """جلب أحدث طلبات API للوحة الأدمن"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM api_orders ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_api_orders(offset=0, limit=50, status: str | None = None):
    """Get ALL API orders with optional status filter and pagination."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    base_query = 'SELECT * FROM api_orders'
    params = []

    if status:
        base_query += ' WHERE status = ?'
        params.append(status)

    base_query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(base_query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def count_api_orders(status: str | None = None) -> int:
    """Count API orders with optional status filter."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute('SELECT COUNT(*) FROM api_orders WHERE status = ?', (status,))
    else:
        cursor.execute('SELECT COUNT(*) FROM api_orders')

    count = cursor.fetchone()[0]
    conn.close()
    return count


def search_api_orders_by_internal_or_provider_id(term: str):
    """Search API orders by internal uuid or provider order_id (exact match)."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        'SELECT * FROM api_orders WHERE uuid = ? OR order_id = ?',
        (term, term)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# --- Order Source Classification ---

def get_orders_by_status_and_source(status, source=None):
    """
    Get orders filtered by status and optional source.
    source: 'LOCAL', 'API', or None (all)
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if source:
        cursor.execute(
            "SELECT * FROM orders WHERE status = ? AND order_source = ?",
            (status, source)
        )
    else:
        cursor.execute(
            "SELECT * FROM orders WHERE status = ?",
            (status,)
        )
    
    rows = cursor.fetchall()
    conn.close()
    return [_dict_factory_order(row) for row in rows]


def get_all_orders_by_source(source=None):
    """
    Get all orders filtered by optional source.
    source: 'LOCAL', 'API', or None (all)
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if source:
        cursor.execute("SELECT * FROM orders WHERE order_source = ?", (source,))
    else:
        cursor.execute("SELECT * FROM orders")
    
    rows = cursor.fetchall()
    conn.close()
    return [_dict_factory_order(row) for row in rows]

def get_order_by_uuid(uuid):
    conn = get_db_connection()
    c = conn.cursor()
    # نبحث في جدول api_orders
    c.execute("SELECT * FROM api_orders WHERE uuid=?", (uuid,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def sync_products_from_api(products_list):
    """تحديث جدول المنتجات بناءً على بيانات API"""
    if not products_list: return

    conn = get_db_connection()
    c = conn.cursor()

    # التأكد من وجود الجدول بالحقول الصحيحة (للاحتياط)
    # ملاحظة: هذا يعتمد على هيكلية جدولك، هنا نفترض الحقول الأساسية
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT,
        price REAL,
        category_name TEXT,
        min_qty INTEGER DEFAULT 1,
        max_qty INTEGER DEFAULT 1000,
        description TEXT
    )''')

    for p in products_list:
        # استخراج البيانات
        pid = str(p.get('id'))
        name = p.get('name', 'Unknown')
        price = float(p.get('price', 0))  # السعر بعد إضافة النسبة
        category = p.get('category_name', 'General')
        min_q = int(p.get('min', 1))
        max_q = int(p.get('max', 1000))
        desc = p.get('description', '')

        # إدخال أو تحديث
        c.execute("""
            INSERT OR REPLACE INTO products 
            (id, name, price, category_name, min_qty, max_qty, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pid, name, price, category, min_q, max_q, desc))

    conn.commit()
    conn.close()
    print(f"💾 تم حفظ {len(products_list)} منتج في قاعدة البيانات.")