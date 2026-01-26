import json
import os
from datetime import datetime
import random

DB_FILE = "users_db.json"
PENDING_FILE = "pending_orders.json"
DEPOSITS_FILE = "deposit_requests.json"


# --- Helper Functions (الدوال المساعدة) ---
def load_json(file_path):
    if not os.path.exists(file_path): 
        # إذا الملف غير موجود، نرجع قاموس فارغ للداتا، وقائمة فارغة للطلبات
        return {} if file_path == DB_FILE else []
    try:
        with open(file_path, 'r', encoding='utf-8') as f: 
            return json.load(f)
    except: 
        return {} if file_path == DB_FILE else []

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- User Management (إدارة المستخدمين) ---
def ensure_user_exists(user_id):
    """التحقق من وجود المستخدم، وإنشاؤه إن لم يكن موجوداً"""
    data = load_json(DB_FILE)
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": 0.0, "banned": False, "total_deposited": 0.0}
        save_json(DB_FILE, data)
    # Migrate old users to include total_deposited
    elif "total_deposited" not in data[uid]:
        data[uid]["total_deposited"] = 0.0
        save_json(DB_FILE, data)
    return data

def get_user_data(user_id):
    ensure_user_exists(user_id)
    data = load_json(DB_FILE)
    return data.get(str(user_id))

def get_balance(user_id):
    ensure_user_exists(user_id)
    data = load_json(DB_FILE)
    return data[str(user_id)].get("balance", 0.0)

def add_balance(user_id, amount, is_deposit=False):
    """Add balance to user. If is_deposit=True, track in total_deposited."""
    data = ensure_user_exists(user_id)
    uid = str(user_id)
    current = float(data[uid].get("balance", 0.0))
    amount_float = float(amount)
    data[uid]["balance"] = current + amount_float
    
    # Track total deposited amount for statistics
    if is_deposit:
        current_deposited = data[uid].get("total_deposited", 0.0)
        data[uid]["total_deposited"] = current_deposited + amount_float
    
    save_json(DB_FILE, data)
    return data[uid]["balance"]

def get_total_deposited(user_id):
    """Get total lifetime deposited amount."""
    data = ensure_user_exists(user_id)
    return data[str(user_id)].get("total_deposited", 0.0)

def deduct_balance(user_id, amount):
    """خصم آمن مع معالجة الكسور العشرية"""
    data = ensure_user_exists(user_id)
    uid = str(user_id)
    
    try:
        current = float(data[uid].get("balance", 0.0))
        cost = float(amount)
    except: return False
    
    # استخدام التقريب لتفادي مشاكل الفواصل العائمة
    if round(current, 4) >= round(cost, 4):
        data[uid]["balance"] = current - cost
        save_json(DB_FILE, data)
        return True
    return False

# --- Ban System (نظام الحظر) ---
def ban_user(user_id, status=True):
    data = ensure_user_exists(user_id)
    data[str(user_id)]["banned"] = status
    save_json(DB_FILE, data)

def is_banned(user_id):
    data = load_json(DB_FILE)
    user = data.get(str(user_id), {})
    return user.get("banned", False)

# --- Pending Orders (الطلبات المعلقة) ---

def save_pending_order(user_id, product_data, qty, inputs, params):
    orders = load_json(PENDING_FILE)
    
    # تنسيق الوقت
    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    # 🔥 هنا الحل: توليد آيدي عشوائي والتأكد من عدم تكراره
    while True:
        # يولد رقم بين 10000 و 99999
        new_id = str(random.randint(10000, 99999))
        
        # يفحص هل هذا الرقم موجود مسبقاً في القائمة؟
        # إذا غير موجود (False)، يكسر الحلقة ويعتمده
        if not any(o['id'] == new_id for o in orders):
            break
    
    new_order = {
        "id": new_id, # ✅ الآيدي الجديد الفريد
        "user_id": user_id,
        "product": product_data,
        "qty": qty,
        "inputs": inputs,
        "params": params,
        "status": "pending",
        "date": now
    }
    orders.append(new_order)
    save_json(PENDING_FILE, orders)
    return new_order["id"]


def get_pending_orders():
    """للأدمن: جلب الطلبات التي حالتها pending فقط"""
    all_orders = load_json(PENDING_FILE)
    return [o for o in all_orders if o.get("status") == "pending"]

def get_user_local_orders(user_id):
    """للمستخدم: جلب كل الطلبات المحلية (معلقة + مكتملة يدوياً)"""
    all_orders = load_json(PENDING_FILE)
    # نعيد الطلبات الخاصة بالمستخدم سواء كانت pending أو completed
    return [o for o in all_orders if str(o["user_id"]) == str(user_id)]

def get_pending_order_by_id(order_id):
    orders = load_json(PENDING_FILE)
    for o in orders:
        if str(o['id']) == str(order_id): return o
    return None

def update_order_status(order_id, new_status):
    """تحديث حالة الطلب بدلاً من حذفه"""
    orders = load_json(PENDING_FILE)
    for o in orders:
        if str(o["id"]) == str(order_id):
            o["status"] = new_status
            save_json(PENDING_FILE, orders)
            return True
    return False

def remove_pending_order(order_id):
    """حذف نهائي (نستخدمه فقط عند الاسترجاع أو النقل للـ API)"""
    orders = load_json(PENDING_FILE)
    new_orders = [o for o in orders if str(o["id"]) != str(order_id)]
    save_json(PENDING_FILE, new_orders)
    

# 1. تحديث بيانات المستخدم (الاسم واليوزر)
def update_user_info(user_id, first_name, username):
    data = load_json(DB_FILE)
    uid = str(user_id)
    
    # إذا غير موجود ننشئه
    if uid not in data:
        data[uid] = {"balance": 0.0, "banned": False}
    
    # تحديث الاسم واليوزر
    data[uid]["name"] = first_name
    data[uid]["username"] = username if username else "No User"
    
    save_json(DB_FILE, data)

# 2. جلب قائمة كل المستخدمين (للأدمن)
def get_all_users_list():
    """ترجع قائمة بكل المستخدمين مع بياناتهم"""
    data = load_json(DB_FILE)
    users_list = []
    for uid, info in data.items():
        users_list.append({
            "id": uid,
            "name": info.get("name", "Unknown"),
            "username": info.get("username", ""),
            "balance": info.get("balance", 0.0),
            "banned": info.get("banned", False)
        })
    return users_list


def get_all_user_ids():
    """جلب قائمة بكل آيديات المستخدمين فقط"""
    data = load_json(DB_FILE)
    return list(data.keys())




# تأكد من وجود الملف
if not os.path.exists(DEPOSITS_FILE): save_json(DEPOSITS_FILE, [])


def save_deposit_request(user_id, method, txn_id, amount, proof_image_id=None):
    reqs = load_json(DEPOSITS_FILE)

    # توليد آيدي عشوائي للطلب
    import random
    req_id = str(random.randint(10000, 99999))

    new_req = {
        "id": req_id,
        "user_id": user_id,
        "method": method,
        "txn_id": txn_id,
        "amount": float(amount),
        "proof_image_id": proof_image_id,
        "date": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "status": "pending"
    }
    reqs.append(new_req)
    save_json(DEPOSITS_FILE, reqs)
    return new_req


def get_deposit_request(req_id):
    reqs = load_json(DEPOSITS_FILE)
    for r in reqs:
        if r['id'] == str(req_id): return r
    return None


def remove_deposit_request(req_id):
    reqs = load_json(DEPOSITS_FILE)
    new_reqs = [r for r in reqs if r['id'] != str(req_id)]
    save_json(DEPOSITS_FILE, new_reqs)


# --- Reports Functions (دوال التقارير) ---

REPORTS_METADATA_FILE = "reports_metadata.json"

def get_completed_orders():
    """Get all completed orders."""
    all_orders = load_json(PENDING_FILE)
    return [o for o in all_orders if o.get("status") == "completed"]


def get_orders_by_date_range(start_date, end_date):
    """
    Get completed orders within a date range.
    start_date and end_date should be datetime objects.
    """
    completed_orders = get_completed_orders()
    filtered = []
    
    for order in completed_orders:
        order_date_str = order.get("date", "")
        if not order_date_str:
            continue
            
        try:
            # Parse date string (format: "YYYY-MM-DD HH:MM AM/PM")
            order_date = datetime.strptime(order_date_str.split()[0], "%Y-%m-%d")
            
            # Check if order is within range (inclusive)
            if start_date.date() <= order_date.date() <= end_date.date():
                filtered.append(order)
        except (ValueError, IndexError):
            # Skip orders with invalid date format
            continue
    
    return filtered


def load_reports_metadata():
    """Load report metadata to track last generated reports."""
    if not os.path.exists(REPORTS_METADATA_FILE):
        default_data = {
            "last_daily": None,
            "last_weekly": None,
            "last_monthly": None
        }
        save_json(REPORTS_METADATA_FILE, default_data)
        return default_data
    return load_json(REPORTS_METADATA_FILE)


def save_reports_metadata(data):
    """Save report metadata."""
    save_json(REPORTS_METADATA_FILE, data)


def update_last_report_date(report_type, date_str):
    """Update last generated report date for a specific type."""
    metadata = load_reports_metadata()
    metadata[f"last_{report_type}"] = date_str
    save_reports_metadata(metadata)


def get_last_report_date(report_type):
    """Get last generated report date for a specific type."""
    metadata = load_reports_metadata()
    return metadata.get(f"last_{report_type}")
