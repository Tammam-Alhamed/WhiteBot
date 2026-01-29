import requests
import config
import uuid
import asyncio
import zlib
import json
# import os  <-- لم يعد ضرورياً للتعامل مع الملفات

# ✅ الاستيرادات الضرورية
import services.settings as settings
import services.database as database  # 🔄 استيراد قاعدة البيانات
import data.mappings as mappings

_products_cache = []
_category_id_map = {}


# --- دالة تنظيف النصوص ---
def clean_str(text):
    if not text: return ""
    return str(text).strip()


def generate_stable_id(text):
    if not text: return "0"
    return str(zlib.crc32(clean_str(text).encode('utf-8')))


def refresh_data():
    global _products_cache, _category_id_map
    url = f"{config.API_BASE_URL}/products"
    headers = {"api-token": config.API_TOKEN}

    print("🔄 جاري الاتصال بالمزود لجلب المنتجات...")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):

                print("=" * 10 + " 📊 بدء معالجة الأسعار " + "=" * 10)

                for p in data:
                    # 🔍 (التصحيح هنا) نجلب السعر من price أو rate
                    raw_price = p.get('price', p.get('rate', 0))
                    original_rate = float(raw_price)

                    name = clean_str(p.get('name', ''))
                    cat_name = clean_str(p.get('category_name', '')).lower()

                    # 1. تحديد الفئة
                    category_key = "default"
                    all_maps = {**mappings.GAMES_MAP, **mappings.APPS_MAP}
                    search_text = (cat_name + " " + name.lower())

                    for key, keywords in all_maps.items():
                        if any(kw in search_text for kw in keywords):
                            category_key = key
                            break

                    # 2. جلب النسبة والحساب
                    margin = settings.get_margin_for_category(category_key)
                    new_rate = original_rate * margin

                    # 3. تحديث السعر في الذاكرة (نحدث الاثنين لضمان العمل)
                    p['rate'] = new_rate
                    p['price'] = new_rate

                    # طباعة للتأكد (فقط لمنتجات ببجي أو إذا كان السعر أكبر من 0)
                    if "شدة" in name or "uc" in name.lower() or original_rate > 0:
                        pass

                # طباعة عينة واحدة للتأكد أن السعر لم يعد صفراً
                sample = next((p for p in data if "شدة" in str(p.get('name'))), None)
                if sample:
                    print(f"✅ عينة ناجحة: {sample['name']}")
                    print(f"💰 السعر الأصلي: {sample.get('original_price_debug', raw_price)}")
                    print(f"💵 السعر الجديد: {sample['price']} (بعد ربح {(margin - 1) * 100:.0f}%)")

                print("=" * 40)

                _products_cache = data
                _category_id_map = {}
                for p in data:
                    cat_name = clean_str(p.get('category_name', ''))
                    if cat_name:
                        short_id = generate_stable_id(cat_name)
                        _category_id_map[short_id] = cat_name

                print(f"✅ تم التحديث بنجاح. عدد المنتجات: {len(data)}")
                return True
    except Exception as e:
        print(f"❌ خطأ فادح: {e}")
        import traceback
        traceback.print_exc()
    return False


def get_products_by_cat_id(short_id):
    if not _products_cache: refresh_data()

    full_name = _category_id_map.get(str(short_id))
    if not full_name:
        refresh_data()
        full_name = _category_id_map.get(str(short_id))
        if not full_name: return []

    filtered = []
    for p in _products_cache:
        p_cat = clean_str(p.get('category_name', ''))
        if p_cat == full_name:
            filtered.append(p)
    return filtered


def search_subcategories(keywords_list):
    if not _products_cache: refresh_data()
    found_cats_ids = set()
    results = []
    lower_keywords = [clean_str(k).lower() for k in keywords_list]

    for p in _products_cache:
        cat_name = clean_str(p.get('category_name', ''))
        lower_cat = cat_name.lower()

        for kw in lower_keywords:
            if kw in lower_cat:
                short_id = generate_stable_id(cat_name)
                if short_id not in found_cats_ids:
                    found_cats_ids.add(short_id)
                    results.append((short_id, cat_name))
                break
    return results


# --- باقي الدوال الأساسية ---
def get_product_details(pid):
    str_id = str(pid)
    for p in _products_cache:
        if str(p.get('id')) == str_id: return p
    return None


def get_profile():
    url = f"{config.API_BASE_URL}/profile"
    headers = {"api-token": config.API_TOKEN}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK":
                return {"balance": data.get("balance", "0"), "email": data.get("email", "")}
    except:
        pass
    return None


def check_orders_status(uuid_list):
    if not uuid_list: return []
    orders_param = json.dumps(uuid_list)
    url = f"{config.API_BASE_URL}/check"
    headers = {"api-token": config.API_TOKEN}
    params = {"orders": orders_param, "uuid": "1"}
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if data.get("status") == "OK": return data.get("data", [])
    except:
        pass
    return []


# 🔄 دالة مساعدة لضمان وجود جدول الطلبات الخارجية
def ensure_uuids_table():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS remote_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        order_uuid TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()


def save_uuid_locally(user_id, order_uuid):
    """حفظ UUID في قاعدة البيانات وحذف القديم ليبقى آخر 20 فقط."""
    ensure_uuids_table()
    conn = database.get_db_connection()
    cursor = conn.cursor()
    uid = str(user_id)

    # إضافة السجل الجديد
    cursor.execute("INSERT INTO remote_orders (user_id, order_uuid) VALUES (?, ?)", (uid, str(order_uuid)))

    # حذف السجلات الزائدة (الاحتفاظ بآخر 20)
    # نحذف أي سجل لهذا المستخدم ليس ضمن آخر 20 سجل (مرتبة زمنياً)
    cursor.execute("""
        DELETE FROM remote_orders 
        WHERE id NOT IN (
            SELECT id FROM remote_orders 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 20
        ) AND user_id = ?
    """, (uid, uid))

    conn.commit()
    conn.close()


def get_user_uuids(user_id):
    """جلب قائمة UUIDs للمستخدم من قاعدة البيانات."""
    ensure_uuids_table()
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT order_uuid FROM remote_orders WHERE user_id = ? ORDER BY created_at DESC", (str(user_id),))
    rows = cursor.fetchall()
    conn.close()

    # استخراج القيم من الصفوف
    return [row['order_uuid'] for row in rows]


async def execute_order_dynamic(product_id, qty, inputs_list, param_names_list):
    url = f"{config.API_BASE_URL}/newOrder/{product_id}/params"
    headers = {"api-token": config.API_TOKEN}
    my_uuid = str(uuid.uuid4())
    main_input = inputs_list[0] if inputs_list else ""
    params = {"qty": int(qty), "playerId": main_input, "order_uuid": my_uuid}

    if len(inputs_list) > 1:
        for i in range(1, len(inputs_list)):
            key = param_names_list[i]
            value = inputs_list[i]
            params[key] = value

    print(f"🚀 إرسال طلب: {params}")
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, headers=headers, params=params))
        res = response.json()

        if res.get("status") == "OK":
            return True, res.get("data", {}).get("order_id", "تم"), my_uuid, 200

        code = res.get("code", 0)
        msg = res.get("message", "فشلت العملية")
        if code == 100:
            msg = "رصيد الموقع غير كافٍ"
        elif code == 105:
            msg = "الكمية غير متوفرة"

        return False, msg, None, code

    except Exception as e:
        return False, str(e), None, 500