"""Shop orders handler (User Side) with Clean UI & Pagination."""
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.database as database
from bot.utils.helpers import smart_edit
import math

router = Router()

# ==================== HELPER FUNCTIONS ====================

def _get_status_label(status: str) -> str:
    """تحويل الحالة إلى نص عربي مع إيموجي."""
    s = (status or '').lower()
    if s in ['pending', 'processing', 'waiting']:
        return "⏳ قيد المعالجة"
    elif s in ['completed', 'success', 'accept']:
        return "✅ مكتمل"
    elif s in ['rejected', 'canceled', 'fail']:
        return "❌ ملغي/مرفوض"
    elif s == 'partial':
        return "⚠️ مكتمل جزئياً"
    return f"❓ {status}"

def _build_shop_order_card(order: dict, is_api: bool = False) -> str:
    """بناء بطاقة تفاصيل الطلب للمستخدم (تصميم أنيق)."""

    # استخراج البيانات المشتركة
    if is_api:
        order_id = order.get('uuid', order.get('id', '---'))
        # محاولة استخراج الاسم والسعر من حقول مختلفة قد تكون موجودة
        service_name = order.get('product_name', order.get('product', {}).get('name', 'خدمة فورية'))
        price = order.get('price', 0)
        date = order.get('created_at', order.get('date', '---'))
        code_content = order.get('code')
        status = order.get('status', 'pending')
    else:
        order_id = order.get('id', '---')
        service_name = order.get('product', {}).get('name', 'منتج')
        qty = order.get('qty', 1)
        price_unit = float(order.get('product', {}).get('price', 0))
        price = price_unit * int(qty)
        date = order.get('date', '---')
        # في النظام المحلي، الكود قد لا يكون مخزناً بنفس الطريقة، ولكن يمكن إضافته إذا وجد
        code_content = None
        status = order.get('status', 'pending')

        # إذا كان هناك رد من الأدمن أو ملاحظات، يمكن عرضها هنا (حسب هيكلة الداتابيز لديك)

    status_label = _get_status_label(status)

    # بناء البطاقة
    card = (
        f"📦 <b>تفاصيل الطلب</b>\n"
        f"🆔 <b>رقم الطلب:</b> <code>{str(order_id)[-8:]}</code>\n" # عرض آخر 8 خانات فقط للترتيب
        f"────────────────\n"
        f"🛠 <b>الخدمة:</b> {service_name}\n"
        f"💰 <b>القيمة:</b> {price}$\n"
        f"📊 <b>الحالة:</b> {status_label}\n"
        f"📅 <b>التاريخ:</b> {date}\n"
    )

    # عرض المدخلات (مثل الآيدي أو اليوزر) إن وجدت
    if not is_api:
        inputs = order.get('inputs')
        if inputs:
            card += f"📝 <b>بياناتك:</b>\n"
            if isinstance(inputs, dict):
                for k, v in inputs.items():
                    card += f"- {k}: <code>{v}</code>\n"
            elif isinstance(inputs, list):
                for item in inputs:
                    card += f"- <code>{item}</code>\n"

    # عرض الكود أو الرد (الأهم)
    if code_content:
        card += f"\n🔑 <b>الرد / الكود:</b>\n<pre>{code_content}</pre>\n"
    elif status.lower() in ['completed', 'success'] and not code_content:
        # رسالة لطيفة في حال الاكتتمال بدون كود ظاهر (مثل الشحن المباشر)
        card += f"\n✅ <b>تم تنفيذ الطلب بنجاح!</b>\n"

    return card


# ==================== MAIN HANDLERS ====================

@router.callback_query(F.data == "my_orders")
async def show_my_orders_main(call: types.CallbackQuery):
    """نقطة الدخول الرئيسية لطلباتي."""
    await render_orders_page(call, page=1)


@router.callback_query(F.data.startswith("my_ord_pg:"))
async def my_orders_pagination(call: types.CallbackQuery):
    """التنقل بين الصفحات."""
    page = int(call.data.split(":")[1])
    await render_orders_page(call, page=page)


async def render_orders_page(call: types.CallbackQuery, page: int):
    """عرض قائمة الطلبات مع الصفحات."""
    user_id = call.from_user.id
    PAGE_SIZE = 8  # عدد الطلبات في الصفحة

    # 1. جلب البيانات (محلي + API)
    # ملاحظة: نستخدم دوال قاعدة البيانات الموجودة
    try:
        local_orders = database.get_user_local_orders(user_id)
        # جلب آخر 50 طلب API لعدم التحميل الزائد
        api_orders = database.get_user_api_history(user_id, limit=50)
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return await call.answer("حدث خطأ أثناء جلب البيانات", show_alert=True)

    # 2. توحيد القائمة
    all_orders = []

    for o in local_orders:
        o['source_type'] = 'local'
        o['sort_date'] = o.get('date', '')
        all_orders.append(o)

    for o in api_orders:
        o['source_type'] = 'api'
        o['sort_date'] = o.get('created_at', '')
        # توحيد اسم المنتج للعرض
        if 'product_name' in o:
            o['product'] = {'name': o['product_name']}
        elif 'product' not in o:
             o['product'] = {'name': 'خدمة API'}
        all_orders.append(o)

    # 3. الترتيب (الأحدث أولاً)
    all_orders.sort(key=lambda x: x.get('sort_date', ''), reverse=True)

    if not all_orders:
        return await smart_edit(
            call,
            "📭 <b>سجل الطلبات فارغ</b>\n\nلم تقم بأي طلبات بعد.",
            InlineKeyboardBuilder().button(text="🔙 رجوع", callback_data="shop_main").as_markup()
        )

    # 4. تقسيم الصفحات
    total_items = len(all_orders)
    total_pages = math.ceil(total_items / PAGE_SIZE)
    if page > total_pages: page = total_pages
    if page < 1: page = 1

    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    current_items = all_orders[start_idx:end_idx]

    # 5. بناء الواجهة
    txt = f"📦 <b>طلباتي ({total_items})</b>\n"
    txt += f"📄 صفحة {page} من {total_pages}\n"
    txt += "━━━━━━━━━━━━━━━━"

    kb = InlineKeyboardBuilder()

    for order in current_items:
        # تحديد المعرف للزر
        is_api = (order['source_type'] == 'api')
        oid = order.get('uuid') if is_api else order.get('id')

        # أيقونة الحالة
        status = (order.get('status') or '').lower()
        if status in ['completed', 'success', 'accept']:
            icon = "✅"
        elif status in ['rejected', 'canceled', 'fail']:
            icon = "❌"
        else:
            icon = "⏳"

        # اسم الخدمة مختصر
        p_name = order.get('product', {}).get('name', 'طلب')
        short_name = (p_name[:18] + '..') if len(p_name) > 18 else p_name

        # نص الزر: أيقونة | رقم | اسم
        btn_text = f"{icon} #{str(oid)[-5:]} | {short_name}"

        # Callback: view_my_ord:TYPE:ID:PAGE
        # TYPE: L=Local, A=Api
        type_code = "A" if is_api else "L"
        kb.button(text=btn_text, callback_data=f"view_my_ord:{type_code}:{oid}:{page}")

    kb.adjust(1)

    # أزرار التنقل
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton(text="⬅️ سابق", callback_data=f"my_ord_pg:{page-1}"))

    nav.append(types.InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")) # زر وهمي للرقم

    if page < total_pages:
        nav.append(types.InlineKeyboardButton(text="تالي ➡️", callback_data=f"my_ord_pg:{page+1}"))

    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="home"))

    await smart_edit(call, txt, kb.as_markup())


# ==================== DETAIL VIEWER ====================

@router.callback_query(F.data.startswith("view_my_ord:"))
async def view_order_details(call: types.CallbackQuery):
    """عرض تفاصيل طلب محدد."""
    try:
        # Parse data: view_my_ord:TYPE:ID:PAGE
        parts = call.data.split(":")
        type_code = parts[1]
        oid = parts[2]
        page = parts[3]
        user_id = call.from_user.id

        target_order = None
        is_api = (type_code == "A")

        if is_api:
            # بحث في API
            # ملاحظة: نستخدم get_user_api_history ونبحث فيه لأننا لا نملك دالة get_api_order_by_uuid مباشرة للزبون
            # أو يمكننا عمل دالة جديدة، لكن البحث في القائمة الحديثة كافٍ للسرعة
            orders = database.get_user_api_history(user_id, limit=100)
            target_order = next((o for o in orders if str(o.get('uuid')) == str(oid)), None)
        else:
            # بحث في المحلي
            orders = database.get_user_local_orders(user_id)
            target_order = next((o for o in orders if str(o.get('id')) == str(oid)), None)

        if not target_order:
            return await call.answer("❌ لم يتم العثور على الطلب", show_alert=True)

        # بناء البطاقة
        card_text = _build_shop_order_card(target_order, is_api=is_api)

        # زر الرجوع
        back_kb = InlineKeyboardBuilder()
        back_kb.button(text="🔙 رجوع للقائمة", callback_data=f"my_ord_pg:{page}")

        await smart_edit(call, card_text, back_kb.as_markup())

    except Exception as e:
        print(f"Error viewing order: {e}")
        await call.answer("حدث خطأ ما", show_alert=True)