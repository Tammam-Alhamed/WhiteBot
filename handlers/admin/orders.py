"""Admin order management handlers."""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config
import services.database as database
import services.api_manager as api_manager
import data.keyboards as kb
from bot.utils.helpers import smart_edit, format_price
import services.settings as settings
from states.admin import AdminState
import asyncio
import math

from constants.orders import (
    ADMIN_STATUS_LABELS,
    ORDER_SOURCE_API as _ORDER_SOURCE_API,
    ORDER_SOURCE_LOCAL as _ORDER_SOURCE_LOCAL,
    norm_order_status as _norm_order_status,
)
from ui.admin.order_cards import (
    build_compact_admin_order_card as _build_compact_admin_order_card,
    format_admin_order_status as _format_admin_order_status_impl,
    format_api_admin_status as _format_api_admin_status_impl,
    get_order_source_label as _get_order_source_label_impl,
)

router = Router()

# ==================== CONSTANTS ====================

ORDER_SOURCE_LOCAL = _ORDER_SOURCE_LOCAL
ORDER_SOURCE_API = _ORDER_SOURCE_API
PAGE_SIZE = 10  # عدد الطلبات في كل صفحة
# ==================== HELPER FUNCTIONS ====================

def _format_admin_order_status(status: str) -> tuple:
    """Convert status to Arabic label and icon for admin (LOCAL)."""
    return _format_admin_order_status_impl(status)


def _format_api_admin_status(status: str) -> tuple:
    """Convert API status to Arabic label and icon for admin (API)."""
    return _format_api_admin_status_impl(status)


def _get_order_source_label(source: str) -> str:
    """Get Arabic label for order source."""
    return _get_order_source_label_impl(source)


def _build_admin_order_entry(order: dict, is_api: bool = False) -> str:
    """تنسيق بطاقة الطلب الموحدة (للبحث والتفاصيل)."""
    user_id = order.get('user_id', 'غير معروف')

    if is_api:
        internal_id = order.get('uuid', order.get('id', '---'))
        provider_id = order.get('order_id', '---')
        status = order.get('status', 'Unknown')
        status_label, _ = _format_api_admin_status(status)
        service = order.get('product', {}).get('name', order.get('product_name', 'خدمة'))
        price = order.get('product', {}).get('price', order.get('price', 0))
        date = order.get('date', order.get('created_at', '---'))
        code_content = order.get('code')

        entry = (
            f"👤 <b>المستخدم:</b> <code>{user_id}</code>\n"
            f"🆔 <b>رقم الطلب:</b> <code>{internal_id}</code>\n"
            f"────────────────\n"
            f"🔹 <b>الخدمة:</b> {service}\n"
            f"🔹 <b>السعر:</b> {price}$\n"
            f"🔹 <b>الحالة:</b> {status_label}\n"
            f"🔹 <b>المزود:</b> <code>{provider_id}</code>\n"
            f"📅 <b>التاريخ:</b> {date}\n"
        )
        if code_content:
            entry += f"🔑 <b>الكود:</b>\n<pre>{code_content}</pre>\n"

    else:
        local_id = order.get('id', '---')
        status = order.get('status', '')
        status_label, _ = _format_admin_order_status(status)
        service = order.get('product', {}).get('name', 'منتج')
        qty = order.get('qty', 1)
        price = float(order.get('product', {}).get('price', 0))
        total = price * int(qty)
        date = order.get('date', '---')

        entry = (
            f"👤 <b>المستخدم:</b> <code>{user_id}</code>\n"
            f"🆔 <b>رقم الطلب:</b> <code>{local_id}</code>\n"
            f"────────────────\n"
            f"🔸 <b>الخدمة:</b> {service}\n"
            f"🔸 <b>الإجمالي:</b> {total}$ ({qty} قطعة)\n"
            f"🔸 <b>الحالة:</b> {status_label}\n"
            f"📅 <b>التاريخ:</b> {date}\n"
        )

        inputs_data = order.get('inputs')
        if inputs_data:
            entry += f"📝 <b>بيانات العميل:</b>\n"
            if isinstance(inputs_data, dict):
                for k, v in inputs_data.items():
                    entry += f"- {k}: <code>{v}</code>\n"
            elif isinstance(inputs_data, list):
                for item in inputs_data:
                    entry += f"- <code>{item}</code>\n"
    return entry

def _build_compact_order_card(order: dict, is_api: bool = False) -> str:
    """Build compact, clean order card for display."""
    return _build_compact_admin_order_card(order, is_api=is_api)


def _should_show_controls(order: dict, is_api: bool = False) -> bool:
    """
    Determine if control buttons should be shown.

    Rules:
    - API orders: NEVER show controls (read-only)
    - Local orders: ONLY show if status == 'pending'
    """
    if is_api:
        return False

    status = (order.get('status', '')).lower()
    return status == 'pending'


# ==================== MAIN MENU ====================
async def render_orders_page(call: types.CallbackQuery, status_filter: str, page: int):
    """دالة مساعدة لعرض الصفحة المطلوبة مباشرة دون تعديل كائن الحدث."""
    # 1. جلب البيانات
    local_orders = database.get_all_orders()
    api_orders = database.get_all_api_orders()

    # 2. الفلترة وتوحيد الشكل
    def norm_status(s: str) -> str:
        return _norm_order_status(s)

    all_filtered = []

    # معالجة طلبات API
    for o in api_orders:
        if norm_status(o.get('status')) == status_filter:
            mapped = {
                'id': o.get('uuid'),
                'user_id': o.get('user_id'),
                'status': o.get('status'),
                'date': o.get('created_at', ''),
                'order_source': ORDER_SOURCE_API,
                'price': o.get('price', 0),
                'product_name': o.get('product_name', 'API Service')
            }
            all_filtered.append(mapped)

    # معالجة الطلبات المحلية
    for o in local_orders:
        if norm_status(o.get('status')) == status_filter:
            total = float(o.get('product', {}).get('price', 0)) * int(o.get('qty', 1))
            o['price'] = total
            o['product_name'] = o.get('product', {}).get('name', 'Local Product')
            all_filtered.append(o)

    # 3. الترتيب (الأحدث أولاً)
    all_filtered.sort(key=lambda x: x.get('date', ''), reverse=True)

    # 4. منطق الصفحات (Pagination Logic)
    total_items = len(all_filtered)
    total_pages = math.ceil(total_items / PAGE_SIZE) or 1

    if page > total_pages: page = total_pages
    if page < 1: page = 1

    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_items = all_filtered[start_idx:end_idx]

    # 5. بناء الواجهة
    status_label = ADMIN_STATUS_LABELS.get(status_filter, status_filter)

    txt = f"📋 <b>قائمة الطلبات: {status_label}</b>\n"
    txt += f"📄 صفحة <b>{page}</b> من <b>{total_pages}</b>\n"
    txt += f"📦 العدد الكلي: {total_items} طلب\n"
    txt += "═══════════════════════\n"
    txt += "👇 اضغط على زر الطلب لعرض التفاصيل"

    markup = InlineKeyboardBuilder()

    # إضافة أزرار الطلبات
    for order in page_items:
        oid = order['id']
        uid = order.get('user_id', 'Unknown')
        price = order.get('price', 0)
        source_icon = "🌐" if order.get('order_source') == ORDER_SOURCE_API else "🏠"

        # نص الزر: المصدر | المستخدم | رقم الطلب | السعر
        btn_text = f"{source_icon} {uid} | #{oid} | {price}$"
        markup.button(text=btn_text, callback_data=f"view_ord:{oid}")

    markup.adjust(1)  # زر واحد في كل سطر

    # أزرار التنقل بين الصفحات
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ سابق", callback_data=f"filter_orders:{status_filter}:{page - 1}"))

    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))

    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="تالي ➡️", callback_data=f"filter_orders:{status_filter}:{page + 1}"))

    markup.row(*nav_row)

    # تبويبات الفلترة (دائماً ظاهرة)
    tabs_row = []
    tabs_row.append(InlineKeyboardButton(text=f"{'✅ ' if status_filter == 'pending' else ''}⏳ معلّقة",
                                         callback_data="filter_orders:pending:1"))
    tabs_row.append(InlineKeyboardButton(text=f"{'✅ ' if status_filter == 'completed' else ''}✅ مكتملة",
                                         callback_data="filter_orders:completed:1"))
    tabs_row.append(InlineKeyboardButton(text=f"{'✅ ' if status_filter == 'rejected' else ''}❌ مرفوضة",
                                         callback_data="filter_orders:rejected:1"))
    markup.row(*tabs_row)

    # أزرار الأدوات
    markup.row(
        InlineKeyboardButton(text="🔍 بحث", callback_data="search_order_btn"),
        InlineKeyboardButton(text="🔙 خروج", callback_data="admin_home")
    )

    await smart_edit(call, txt, markup.as_markup())


@router.callback_query(F.data == "admin_orders")
async def show_orders_menu(call: types.CallbackQuery):
    """توجيه الأدمن مباشرة للقائمة المعلقة (الصفحة 1)."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # استدعاء دالة العرض مباشرة بدلاً من تعديل call.data
    await render_orders_page(call, "pending", 1)

# ==================== STATE PROTECTION ====================

# Simple in-memory store to prevent double clicks
_recent_clicks = {}

def _is_rate_limited(user_id: int, action: str, timeout: int = 2) -> bool:
    """Check if user is rate limited for a specific action."""
    key = f"{user_id}:{action}"
    current_time = asyncio.get_event_loop().time()

    if key in _recent_clicks:
        if current_time - _recent_clicks[key] < timeout:
            return True

    _recent_clicks[key] = current_time
    return False

# ==================== STATUS FILTER HANDLER ====================


@router.callback_query(F.data.startswith("filter_orders:"))
async def filter_orders_by_status(call: types.CallbackQuery):
    """استقبال طلب الفلترة وتمريره لدالة العرض."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    if _is_rate_limited(call.from_user.id, "filter_orders"):
        return await call.answer("⏳ ...", show_alert=True)

    await call.answer()

    # تحليل البيانات: filter_orders:{status}:{page}
    parts = call.data.split(":")
    status_filter = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1

    # استدعاء دالة العرض
    await render_orders_page(call, status_filter, page)


# ==================== QUICK ACTION HANDLERS ====================

@router.callback_query(F.data.startswith("quick_approve:"))
async def quick_approve_order(call: types.CallbackQuery):
    """Quick approve a local pending order."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # Prevent double clicks
    if _is_rate_limited(call.from_user.id, "quick_approve"):
        return await call.answer("⏳ الرجاء الانتظار...", show_alert=True)

    await call.answer("⏳ جاري المعالجة...")

    order_id = call.data.split(":")[1]

    # Get order details
    all_orders = database.get_all_orders()
    order = next((o for o in all_orders if str(o.get('id')) == str(order_id)), None)

    if not order:
        return await call.answer("❌ الطلب غير موجود", show_alert=True)

    # Safety check: only allow for local pending orders
    if order.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_API:
        return await call.answer("❌ لا يمكن قبول طلبات API", show_alert=True)

    if (order.get('status', '')).lower() != 'pending':
        return await call.answer("❌ يمكن فقط قبول الطلبات المعلقة", show_alert=True)

    # Approve the order
    database.update_order_status(order_id, "completed")

    # Notify user
    try:
        await call.bot.send_message(
            order['user_id'],
            f"✅ <b>تم قبول طلبك #{order_id}</b>\n"
            f"📦 المنتج: {order['product']['name']}\n"
            f"📊 الحالة: مكتمل",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للعميل: {e}")

    # Update the message to show success
    await call.message.edit_text(
        "✅ <b>تم قبول الطلب بنجاح</b>\n"
        f"<code>{order_id}</code>\n"
        f"📦 {order['product']['name']}\n"
        f"💰 المبلغ: {order['product']['price']}$",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="filter_orders:pending")]
        ])
    )

@router.callback_query(F.data.startswith("quick_reject:"))
async def quick_reject_order(call: types.CallbackQuery):
    """Quick reject a local pending order with refund."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # Prevent double clicks
    if _is_rate_limited(call.from_user.id, "quick_reject"):
        return await call.answer("⏳ الرجاء الانتظار...", show_alert=True)

    await call.answer("⏳ جاري المعالجة...")

    order_id = call.data.split(":")[1]

    # Get order details
    all_orders = database.get_all_orders()
    order = next((o for o in all_orders if str(o.get('id')) == str(order_id)), None)

    if not order:
        return await call.answer("❌ الطلب غير موجود", show_alert=True)

    # Safety check: only allow for local pending orders
    if order.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_API:
        return await call.answer("❌ لا يمكن رفض طلبات API", show_alert=True)

    if (order.get('status', '')).lower() != 'pending':
        return await call.answer("❌ يمكن فقط رفض الطلبات المعلقة", show_alert=True)

    # Process refund
    cost = float(order['product']['price']) * int(order.get('qty', 1))
    rate = settings.get_setting("exchange_rate")

    # Refund balance
    new_bal = database.add_balance(order['user_id'], cost)
    new_bal_syp = int(new_bal * rate)
    cost_syp = int(cost * rate)

    # Update order status
    database.update_order_status(order_id, "rejected")

    # Notify user
    try:
        msg_text = (
            f"❌ <b>تم رفض طلبك #{order_id}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 المنتج: {order['product']['name']}\n"
            f"💰 <b>الرصيد المسترجع:</b>\n"
            f"🇺🇸 {cost:.2f} $\n"
            f"🇸🇾 {cost_syp:,} ل.س\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>رصيدك الحالي:</b>\n"
            f"🇺🇸 {new_bal:.2f} $\n"
            f"🇸🇾 {new_bal_syp:,} ل.س"
        )
        await call.bot.send_message(order['user_id'], msg_text, parse_mode="HTML")
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للعميل: {e}")

    # Update the message to show success
    await call.message.edit_text(
        "❌ <b>تم رفض الطلب بنجاح</b>\n"
        f"<code>{order_id}</code>\n"
        f"📦 {order['product']['name']}\n"
        f"💰 المبلغ المسترجع: {cost}$",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="filter_orders:pending")]
        ])
    )


# ==================== LEGACY ALL ORDERS VIEW (KEPT FOR COMPATIBILITY) ====================

@router.callback_query(F.data == "list_all_orders")
async def list_all_orders(call: types.CallbackQuery):
    """توجيه للطلبات المعلقة."""
    await render_orders_page(call, "pending", 1)


# ==================== SEARCH HANDLER ====================

@router.callback_query(F.data == "search_order_btn")
async def ask_search_order_id(call: types.CallbackQuery, state: FSMContext):
    """Ask for order search input."""
    if not database.is_user_admin(call.from_user.id):
        return
    await smart_edit(
        call,
        "🔍 <b>بحث عن طلب</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "أرسل <b>رقم الطلب</b> أو <b>معرف المستخدم</b>:\n\n"
        "📌 مثال: <code>12345</code>",
        kb.back_btn("admin_orders")
    )
    await state.set_state(AdminState.waiting_for_order_id)


@router.message(AdminState.waiting_for_order_id)
async def perform_order_search(msg: types.Message, state: FSMContext):
    """البحث في جميع الطلبات وعرض النتائج المتاحة فقط بتنسيق HTML."""
    if not database.is_user_admin(msg.from_user.id):
        await state.clear()
        return

    search_term = (msg.text or '').strip()
    if not search_term:
        await msg.answer("❌ الرجاء إدخال رقم صحيح.")
        return

    # جلب البيانات
    local_all = database.get_all_orders()
    api_all = database.get_all_api_orders()

    # البحث
    local_matches = [o for o in local_all if str(o.get('id')) == search_term or str(o.get('user_id')) == search_term]

    api_matches = []
    for o in api_all:
        if str(o.get('uuid')) == search_term or str(o.get('order_id')) == search_term or str(
                o.get('user_id')) == search_term:
            api_matches.append(o)

    # إذا لم توجد نتائج
    if not local_matches and not api_matches:
        # هنا أيضاً نستخدم HTML لتلوين الكود
        await msg.answer(
            f"❌ لم يتم العثور على نتائج للبحث: <code>{search_term}</code>",
            parse_mode="HTML"
        )
        await state.clear()
        return

    # بناء النص
    results_text = f"🔍 <b>نتائج البحث عن:</b> <code>{search_term}</code>\n"
    results_text += "═══════════════════════\n\n"

    # عرض طلبات API
    for o in api_matches:
        mapped_api = {
            'id': o.get('uuid'),
            'user_id': o.get('user_id'),
            'status': o.get('status'),
            'created_at': o.get('created_at'),
            'product_name': o.get('product_name'),
            'price': o.get('price'),
            'order_id': o.get('order_id'),
            'code': o.get('code')
        }
        results_text += _build_admin_order_entry(mapped_api, is_api=True)
        results_text += "<b>━━━━━━━━━━━━━━</b>\n\n"

    # عرض الطلبات المحلية
    for o in local_matches:
        results_text += _build_admin_order_entry(o, is_api=False)
        results_text += "<b>━━━━━━━━━━━━━━</b>\n\n"

    # الأزرار
    keyboard = InlineKeyboardBuilder()
    for o in local_matches:
        keyboard.button(text=f"⚙️ إدارة #{o['id']}", callback_data=f"view_ord:{o['id']}")

    keyboard.button(text="🔙 رجوع", callback_data="admin_orders")
    keyboard.adjust(2)

    # ✅ التعديل الأهم: إضافة parse_mode="HTML"
    await msg.answer(results_text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.clear()

# ==================== ORDER DETAILS & ACTIONS ====================

@router.callback_query(F.data.startswith("view_ord:"))
async def view_order_details(call: types.CallbackQuery):
    """عرض تفاصيل الطلب باستخدام البطاقة الموحدة."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    oid = call.data.split(":")[1]

    # البحث عن الطلب محلياً أو في API
    all_local = database.get_all_orders()
    order = next((o for o in all_local if str(o.get('id')) == str(oid)), None)

    is_api = False
    if not order:
        all_api = database.get_all_api_orders()
        api_order = next((o for o in all_api if str(o.get('uuid')) == str(oid)), None)
        if api_order:
            is_api = True
            order = api_order
            order['order_source'] = ORDER_SOURCE_API
            if 'product' not in order:
                order['product'] = {'name': order.get('product_name'), 'price': order.get('price')}

    if not order:
        return await call.answer("❌ الطلب غير موجود", show_alert=True)

    # بناء البطاقة
    txt = _build_admin_order_entry(order, is_api=is_api)

    # تحديد وجهة زر الرجوع (يعود لنفس القائمة التي جاء منها)
    status = (order.get('status') or '').lower()
    norm_status = _norm_order_status(status)
    # إذا كانت الحالة غير معروفة عد للمعلقة، وإلا عد للحالة نفسها الصفحة 1
    back_callback = f"filter_orders:{norm_status}:1" if norm_status in ['pending', 'completed',
                                                                        'rejected'] else "filter_orders:pending:1"

    markup = InlineKeyboardBuilder()

    # أزرار التحكم (تظهر فقط للطلبات المحلية المعلقة)
    if not is_api and norm_status == 'pending':
        markup.button(text="✅ قبول (يدوي)", callback_data=f"quick_approve:{oid}")
        markup.button(text="❌ رفض (استرجاع)", callback_data=f"quick_reject:{oid}")
        markup.button(text="🔄 إعادة محاولة (API)", callback_data=f"retry_ord:{oid}")
        markup.adjust(1)

    markup.row(InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data=back_callback))

    await smart_edit(call, txt, markup.as_markup())

@router.callback_query(F.data.startswith("retry_ord:"))
async def retry_order_api(call: types.CallbackQuery):
    """Retry order execution via API."""
    if not database.is_user_admin(call.from_user.id):
        return

    oid = call.data.split(":")[1]
    # Work against full set, but ensure it's pending when performing actions
    all_orders = database.get_all_orders()
    o = next((x for x in all_orders if str(x.get('id')) == str(oid)), None)
    if not o:
        return await call.answer("❌ الطلب غير موجود")

    # Safety check: only allow retry for local pending orders
    if o.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_API:
        return await call.answer("❌ لا يمكن إعادة محاولة طلبات API", show_alert=True)

    if (o.get('status', '')).lower() != 'pending':
        return await call.answer("❌ يمكن فقط إعادة محاولة الطلبات المعلقة", show_alert=True)

    await call.answer("⏳ جاري المحاولة...")
    ok, res, uuid, code = await api_manager.execute_order_dynamic(
        o['product']['id'], o['qty'], o['inputs'], o['params'], o['user_id']
    )

    if ok:
        database.update_order_status(oid, "completed")
        await call.message.answer(f"✅ <b>تم التنفيذ!</b>\n🔑 الكود: <code>{res}</code>")
        try:
            await call.bot.send_message(
                o['user_id'],
                f"✅ <b>تم تنفيذ طلبك #{oid}</b>\n"
                f"🔑 الكود: <code>{res}</code>"
            )
        except:
            pass
        await list_all_orders(call)
    else:
        await call.message.answer(f"❌ <b>فشل التنفيذ:</b>\n{res}")


@router.callback_query(F.data.startswith("manual_ord:"))
async def mark_manual_done(call: types.CallbackQuery):
    """Mark order as manually completed."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    oid = call.data.split(":")[1]
    all_orders = database.get_all_orders()
    order = next((x for x in all_orders if str(x.get('id')) == str(oid)), None)

    if not order:
        return await call.answer("❌ الطلب غير موجود")

    # Safety check: only allow for local pending orders
    if order.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_API:
        return await call.answer("❌ لا يمكن تعديل طلبات API", show_alert=True)

    if (order.get('status', '')).lower() != 'pending':
        return await call.answer("❌ يمكن فقط تعديل الطلبات المعلقة", show_alert=True)

    database.update_order_status(oid, "completed")

    try:
        msg_text = (
            f"✅ <b>تحديث حالة الطلب #{oid}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 المنتج: {order['product']['name']}\n"
            f"📊 الحالة الجديدة: <b>مكتمل</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"شكراً لاستخدامك متجرنا! 🌹"
        )
        await call.bot.send_message(chat_id=order['user_id'], text=msg_text, parse_mode="HTML")
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للعميل: {e}")

    await call.answer("✅ تم الحفظ وإشعار العميل")
    await list_all_orders(call)


@router.callback_query(F.data.startswith("ref_ord:"))
async def refund_order_admin(call: types.CallbackQuery):
    """Refund order and notify user."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    oid = call.data.split(":")[1]
    all_orders = database.get_all_orders()
    order = next((x for x in all_orders if str(x.get('id')) == str(oid)), None)

    if not order:
        return await call.answer("❌ الطلب غير موجود")

    # Safety check: only allow for local pending orders
    if order.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_API:
        return await call.answer("❌ لا يمكن استرجاع طلبات API", show_alert=True)

    if (order.get('status', '')).lower() != 'pending':
        return await call.answer("❌ يمكن فقط استرجاع الطلبات المعلقة", show_alert=True)

    cost = float(order['product']['price']) * int(order['qty'])
    rate = settings.get_setting("exchange_rate")

    # Check if PUBG order for currency display
    category_name = order['product'].get('category_name', '')
    is_pubg = 'PUBG' in category_name or 'ببجي' in category_name

    # Refund balance
    new_bal = database.add_balance(order['user_id'], cost)
    new_bal_syp = int(new_bal * rate)
    cost_syp = int(cost * rate)

    database.update_order_status(oid, "rejected")

    try:
        if is_pubg:
            msg_text = (
                f"❌ <b>تحديث حالة الطلب #{oid}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 المنتج: {order['product']['name']}\n"
                f"📊 الحالة الجديدة: <b>ملغي</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>الرصيد المسترجع:</b> {cost:.2f} $\n"
                f"💎 <b>رصيدك الحالي:</b> {new_bal:.2f} $\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"تم إعادة المبلغ إلى محفظتك."
            )
        else:
            msg_text = (
                f"❌ <b>تحديث حالة الطلب #{oid}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 المنتج: {order['product']['name']}\n"
                f"📊 الحالة الجديدة: <b>ملغي</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>الرصيد المسترجع:</b>\n"
                f"🇺🇸 {cost:.2f} $\n"
                f"🇸🇾 {cost_syp:,} ل.س\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <b>رصيدك الحالي:</b>\n"
                f"🇺🇸 {new_bal:.2f} $\n"
                f"🇸🇾 {new_bal_syp:,} ل.س\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"تم إعادة المبلغ إلى محفظتك."
            )
        await call.bot.send_message(chat_id=order['user_id'], text=msg_text, parse_mode="HTML")
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للعميل: {e}")

    await call.answer("✅ تم الإلغاء وإشعار العميل")
    await list_all_orders(call)


# ==================== BULK OPERATIONS ====================

@router.callback_query(F.data == "bulk_approve_orders")
async def bulk_approve_orders(call: types.CallbackQuery):
    """Confirm bulk approve all pending LOCAL orders only."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # Only get LOCAL orders - API orders are excluded
    local_orders = database.get_all_orders()
    pending = [o for o in local_orders if (o.get('status') or '').lower() == 'pending' and o.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_LOCAL]

    if not pending:
        return await call.answer("❌ لا يوجد طلبات محلية معلقة", show_alert=True)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأكيد قبول الكل", callback_data="confirm_bulk_approve_orders")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="list_all_orders")]
    ])

    await smart_edit(
        call,
        f"⚠️ <b>تأكيد العملية</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"سيتم قبول <b>{len(pending)}</b> طلب محلي فقط\n"
        f"وتعليمها كمكتملة يدوياً.\n\n"
        f"ملاحظة: طلبات API لا يمكن تعديلها.",
        markup
    )


@router.callback_query(F.data == "confirm_bulk_approve_orders")
async def confirm_bulk_approve_orders(call: types.CallbackQuery):
    """Execute bulk approve."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    all_orders = database.get_all_orders()
    pending = [o for o in all_orders if (o.get('status') or '').lower() == 'pending' and o.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_LOCAL]

    approved_count = 0

    for order in pending:
        try:
            database.update_order_status(order['id'], "completed")
            try:
                await call.bot.send_message(
                    order['user_id'],
                    f"✅ <b>تم قبول طلبك #{order['id']}</b>\n"
                    f"📦 المنتج: {order['product']['name']}\n"
                    f"📊 الحالة: مكتمل",
                    parse_mode="HTML"
                )
            except:
                pass
            approved_count += 1
        except:
            pass

    await smart_edit(
        call,
        f"✅ <b>تمت العملية!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ تم القبول: <b>{approved_count}</b>",
        kb.back_btn("list_all_orders")
    )


@router.callback_query(F.data == "bulk_reject_orders")
async def bulk_reject_orders(call: types.CallbackQuery):
    """Confirm bulk reject all pending LOCAL orders only."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # Only get LOCAL orders - API orders are excluded
    local_orders = database.get_all_orders()
    pending = [o for o in local_orders if (o.get('status') or '').lower() == 'pending' and o.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_LOCAL]

    if not pending:
        return await call.answer("❌ لا يوجد طلبات محلية معلقة", show_alert=True)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأكيد رفض الكل", callback_data="confirm_bulk_reject_orders")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="list_all_orders")]
    ])

    await smart_edit(
        call,
        f"⚠️ <b>تأكيد العملية</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"سيتم رفض <b>{len(pending)}</b> طلب محلي فقط\n"
        f"وإرجاع الرصيد للمستخدمين.\n\n"
        f"ملاحظة: طلبات API لا يمكن تعديلها.",
        markup
    )


@router.callback_query(F.data == "confirm_bulk_reject_orders")
async def confirm_bulk_reject_orders(call: types.CallbackQuery):
    """Execute bulk reject."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    all_orders = database.get_all_orders()
    pending = [o for o in all_orders if (o.get('status') or '').lower() == 'pending' and o.get('order_source', ORDER_SOURCE_LOCAL) == ORDER_SOURCE_LOCAL]

    rate = settings.get_setting("exchange_rate")
    rejected_count = 0

    for order in pending:
        try:
            cost = float(order['product']['price']) * int(order['qty'])
            cost_syp = int(cost * rate)

            new_bal = database.add_balance(order['user_id'], cost)
            new_bal_syp = int(new_bal * rate)

            database.update_order_status(order['id'], "rejected")
            rejected_count += 1

            try:
                await call.bot.send_message(
                    order['user_id'],
                    f"❌ <b>تم رفض طلبك #{order['id']}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 المنتج: {order['product']['name']}\n"
                    f"💰 <b>الرصيد المسترجع:</b>\n"
                    f"🇺🇸 {cost:.2f} $\n"
                    f"🇸🇾 {cost_syp:,} ل.س\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 <b>رصيدك الحالي:</b>\n"
                    f"🇺🇸 {new_bal:.2f} $\n"
                    f"🇸🇾 {new_bal_syp:,} ل.س",
                    parse_mode="HTML"
                )
            except:
                pass
        except:
            pass

    await smart_edit(
        call,
        f"✅ <b>تمت العملية!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ تم الرفض: <b>{rejected_count}</b>",
        kb.back_btn("list_all_orders")
    )


# ==================== EXPORT CATEGORIES ====================

@router.message(Command("get_cats"))
async def export_categories(msg: types.Message):
    """Export categories list."""
    if not database.is_user_admin(msg.from_user.id):
        return

    await msg.answer("⏳ جاري جلب الفئات من الموقع...")

    api_manager.refresh_data()

    cats = set()
    for p in api_manager._products_cache:
        c_name = p.get('category_name', '').strip()
        if c_name:
            cats.add(c_name)

    if not cats:
        return await msg.answer("❌ لم يتم العثور على فئات!")

    report = "قائمة الفئات المتوفرة في الموقع:\n(انسخ الاسم وضعه في mappings.py)\n━━━━━━━━━━━━━━━━━━\n"
    for c in sorted(list(cats)):
        report += f"- {c}\n"

    file = BufferedInputFile(report.encode("utf-8"), filename="categories.txt")

    await msg.answer_document(file, caption="📂 هذه كل الألعاب والخدم��ت الموجودة في الموقع حالياً.")
