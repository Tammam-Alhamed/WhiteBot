import requests
import config
import uuid
import asyncio
import zlib
import json
import os
import services.settings as settings
import services.database as database  # 🔄 استيراد قاعدة البيانات
import data.mappings as mappings

_products_cache = []
_category_id_map = {}


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
                for p in data:
                    # حساب السعر
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
                    p['price'] = original_rate * margin

                _products_cache = data
                _category_id_map = {}
                for p in data:
                    cat_name = clean_str(p.get('category_name', ''))
                    if cat_name:
                        short_id = generate_stable_id(cat_name)
                        _category_id_map[short_id] = cat_name

                # 🔥🔥 التعديل الهام هنا: حفظ البيانات في الداتابيز 🔥🔥
                try:
                    database.sync_products_from_api(data)
                except Exception as db_err:
                    print(f"⚠️ خطأ في حفظ المنتجات للقاعدة: {db_err}")

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
        if clean_str(p.get('category_name', '')) == full_name:
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


def get_product_details(pid):
    str_id = str(pid)
    for p in _products_cache:
        if str(p.get('id')) == str_id: return p
    return None


def check_orders_status(order_ids):
    if not order_ids: return []

    # تحديد نوع البحث (ID vs UUID)
    is_search_by_uuid = True
    first_item = str(order_ids[0])

    # ✅ التعديل هنا: إذا كان رقم فقط، نعتبره order_id عادي ولا نحوله لـ int
    # (نرسله كـ string في JSON لضمان التوافق)
    if first_item.isdigit():
        is_search_by_uuid = False
        # لا نستخدم int() هنا، نتركها strings داخل القائمة

    orders_param = json.dumps(order_ids)
    url = f"{config.API_BASE_URL}/check"
    headers = {"api-token": config.API_TOKEN}
    params = {"orders": orders_param}

    if is_search_by_uuid:
        params["uuid"] = "1"

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if data.get("status") == "OK": return data.get("data", [])
    except Exception as e:
        print(f"⚠️ Check API Error: {e}")
    return []




def get_user_uuids(user_id):
    """جلب UUIDs من قاعدة البيانات"""
    try:
        orders = database.get_user_api_history(user_id)
        return [o['uuid'] for o in orders]
    except:
        return []


# تأكد من وجود import services.database as database في الأعلى

async def execute_order_dynamic(product_id, qty, inputs_list, param_names_list, user_id=None):
    url = f"{config.API_BASE_URL}/newOrder/{product_id}/params"
    headers = {"api-token": config.API_TOKEN}
    my_uuid = str(uuid.uuid4())
    main_input = inputs_list[0] if inputs_list else ""

    params = {
        "qty": int(qty),
        "playerId": main_input,
        "order_uuid": my_uuid,
        "custom_uuid": my_uuid
    }
    if user_id: params['telegram_id'] = str(user_id)

    if len(inputs_list) > 1:
        for i in range(1, len(inputs_list)):
            if i < len(param_names_list):
                params[param_names_list[i]] = inputs_list[i]

    print(f"🚀 Sending Order: {params}")
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, headers=headers, params=params))
        res = response.json()

        if res.get("status") == "OK":
            # ✅ نحصل على الآيدي الخارجي
            final_id = res.get("data", {}).get("order_id")

            prod = get_product_details(product_id)
            p_name = prod.get('name', 'Unknown') if prod else 'Unknown'
            p_price = prod.get('price', 0) * int(qty) if prod else 0

            # ✅ نمرر final_id (رقم الطلب الخارجي) ليتم حفظه
            database.log_api_order(user_id, my_uuid, p_name, p_price, "pending", order_id=final_id)

            return True, final_id or my_uuid, my_uuid, 200

        return False, res.get("message", "Error"), None, res.get("code", 0)
    except Exception as e:
        return False, str(e), None, 500

def get_all_recent_uuids_with_users(limit=50):
    try:
        orders = database.get_all_recent_api_orders(limit)
        return [{'uuid': o['uuid'], 'user_id': o['user_id']} for o in orders]
    except: return []

def save_uuid_locally(user_id, order_uuid):
    pass

def get_all_recent_uuids_with_users(limit=50):
    """جلب أحدث الطلبات من قاعدة البيانات للوحة الأدمن"""
    try:
        orders = database.get_all_recent_api_orders(limit)
        return [{'uuid': o['uuid'], 'user_id': o['user_id']} for o in orders]
    except:
        return []

def save_uuid_locally(user_id, order_uuid):
    pass