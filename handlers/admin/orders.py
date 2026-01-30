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

router = Router()

@router.callback_query(F.data == "admin_orders")
async def show_orders_menu(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    orders = database.get_all_orders()
    pending_count = len([o for o in orders if o.get('status') == 'pending'])

    markup = InlineKeyboardBuilder()
    markup.button(text=f"📦 الطلبات المعلقة (Local) - {pending_count}", callback_data="list_pending_orders")
    markup.button(text="🌐 سجل طلبات API (الموقع)", callback_data="list_api_orders")
    markup.button(text="🔍 بحث عن طلب", callback_data="search_order_btn")
    markup.button(text="🔙 رجوع", callback_data="admin_home")
    markup.adjust(1)

    await smart_edit(call, "📦 <b>إدارة الطلبات:</b>\nاختر السجل الذي تريد عرضه:", markup.as_markup())

@router.callback_query(F.data == "search_order_btn")
async def ask_search_order_id(call: types.CallbackQuery, state: FSMContext):
    if not database.is_user_admin(call.from_user.id): return
    await smart_edit(call, "🔍 <b>بحث عن طلب:</b>\n\nأرسل الآن <b>رقم الطلب (Order ID)</b> أو <b>الكود (UUID)</b>.", kb.back_btn("admin_orders"))
    await state.set_state(AdminState.waiting_for_order_id)

@router.message(AdminState.waiting_for_order_id)
async def perform_order_search(msg: types.Message, state: FSMContext):
    if not database.is_user_admin(msg.from_user.id):
        await state.clear()
        return

    order_id = msg.text.strip()
    found = False

    local_order = database.get_pending_order_by_id(order_id)
    if local_order:
        found = True
        txt = (
            f"✅ <b>تم العثور على طلب محلي!</b>\n"
            f"📦 <b>رقم الطلب:</b> {local_order['id']}\n"
            f"👤 العميل: <code>{local_order['user_id']}</code>\n"
            f"🛍 المنتج: {local_order['product'].get('name', 'غير معروف')}\n"
            f"💰 السعر: {local_order['product'].get('price', 0)}$\n"
            f"📊 الحالة: <b>{local_order['status']}</b>\n"
            f"📅 التاريخ: {local_order['date']}"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="عرض التحكم", callback_data=f"view_ord:{local_order['id']}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_orders")]
        ])
        await msg.answer(txt, parse_mode="HTML", reply_markup=markup)

    if not found or len(order_id) > 10:
        await msg.answer("⏳ جاري البحث في سجلات الموقع (API)...")
        try:
            stats = api_manager.check_orders_status([order_id])
            if stats:
                found = True
                stat = stats[0]
                status = stat.get('status', 'Unknown')
                p_name = stat.get('product_name', 'Product')
                price = stat.get('price', 0)
                ext_id = stat.get('order_id') or stat.get('id') or order_id
                codes = stat.get('replay_api')

                # 🔥 محاولة جلب الآيدي
                api_data = stat.get('data') or {}
                api_owner_id = api_data.get('telegram_id') or "غير معروف"

                icon = "✅" if status in ['completed', 'Success', 'accept'] else "❌" if status in ['Canceled', 'Fail', 'rejected'] else "⏳"

                txt = (
                    f"🌐 <b>نتيجة البحث في الموقع:</b>\n"
                    f"{icon} <b>{p_name}</b>\n"
                    f"🆔 Ref: <code>{ext_id}</code>\n"
                    f"👤 العميل: <code>{api_owner_id}</code>\n"
                    f"💰 السعر: {price}$\n"
                    f"📊 الحالة: <b>{status}</b>"
                )
                if codes and isinstance(codes, list) and len(codes) > 0:
                    code_str = "\n".join([f"<code>{c}</code>" for c in codes])
                    txt += f"\n🔑 <b>الكود:</b>\n{code_str}"

                await msg.answer(txt, parse_mode="HTML")
            elif not found:
                await msg.answer("❌ لم يتم العثور على الطلب.")
        except:
            if not found: await msg.answer("❌ خطأ أثناء البحث.")

    await state.clear()

@router.callback_query(F.data == "list_pending_orders")
async def list_pending_orders(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    orders = database.get_all_orders()
    pending_orders = [o for o in orders if o.get('status') == 'pending']

    if not pending_orders:
        return await smart_edit(call, "✅ <b>لا يوجد طلبات شراء معلقة حالياً.</b>", kb.back_btn("admin_orders"))

    keyboard = InlineKeyboardBuilder()
    for order in pending_orders:
        btn_txt = f"{order['product']['name']} | {order['id']}"
        keyboard.button(text=btn_txt, callback_data=f"view_ord:{order['id']}")

    keyboard.button(text="✅ قبول الكل", callback_data="bulk_approve_orders")
    keyboard.button(text="❌ رفض الكل", callback_data="bulk_reject_orders")
    keyboard.button(text="🔙 رجوع", callback_data="admin_orders")
    keyboard.adjust(1)

    await smart_edit(call, f"📦 <b>قائمة الطلبات المعلقة ({len(pending_orders)}):</b>", keyboard.as_markup())

@router.callback_query(F.data == "list_api_orders")
async def list_api_orders(call: types.CallbackQuery):
    """List recent API orders with TELEGRAM ID."""
    orders_info = api_manager.get_all_recent_uuids_with_users(limit=50)

    if not orders_info:
        return await smart_edit(call, "📂 <b>سجل API فارغ.</b>", kb.back_btn("admin_orders"))

    uuids = [o['uuid'] for o in orders_info]
    stats = api_manager.check_orders_status(uuids)

    txt = "🌐 <b>سجل طلبات الموقع (API):</b>\n━━━━━━━━━━━━\n"

    if not stats:
        txt += "⚠️ لا يمكن جلب البيانات من الموقع حالياً.\n"

    # 🔥 طباعة للتأكد من البيانات القادمة من الموقع
    print(f"DEBUG STATS: {stats[:1]}")

    for stat in stats[:15]:
        api_data = stat.get('data') or {}

        # 1. محاولة جلب الآيدي المباشر (telegram_id)
        owner_id = api_data.get('telegram_id')

        # 2. محاولة المطابقة عبر custom_uuid
        if not owner_id:
            c_uuid = api_data.get('custom_uuid')
            if c_uuid:
                for o in orders_info:
                    if o['uuid'] == c_uuid:
                        owner_id = o['user_id']
                        break

        # 3. محاولة المطابقة العكسية (إذا كان الموقع يعيد order_uuid الأصلي)
        if not owner_id:
            returned_uuid = stat.get('order_uuid')
            if returned_uuid:
                for o in orders_info:
                    if o['uuid'] == returned_uuid:
                        owner_id = o['user_id']
                        break

        # 4. محاولة المطابقة النصية (أضعف إيمان)
        if not owner_id:
            for o in orders_info:
                if o['uuid'] in str(stat):
                    owner_id = o['user_id']
                    break

        if not owner_id:
            owner_id = "غير معروف"

        status = stat.get('status', 'Unknown')
        if status in ['completed', 'Success', 'Complete', 'accept']: icon = "✅"
        elif status in ['Canceled', 'Fail', 'Refunded', 'Rejected']: icon = "❌"
        elif status in ['Pending', 'Processing', 'In progress']: icon = "⏳"
        else: icon = "❔"

        p_name = stat.get('product_name', 'Product')
        price = stat.get('price', 0)
        external_id = stat.get('order_id') or stat.get('id') or '---'

        codes = stat.get('replay_api')
        code_txt = f" | 🔑 {codes[0]}" if (codes and isinstance(codes, list) and len(codes)>0) else ""
        fail_reason = stat.get('reason') or stat.get('note')

        txt += f"{icon} <b>{p_name}</b>\n"
        txt += f"🆔 Ref: <code>{external_id}</code>\n"
        txt += f"👤 <code>{owner_id}</code> | 💰 {price}${code_txt}\n"
        txt += f"📊 {status}"

        if fail_reason and status in ['Canceled', 'Fail', 'Rejected']:
             txt += f" | ⚠️ {fail_reason}"

        txt += "\n----------------\n"

    txt += "\n💡 للبحث عن طلب قديم استخدم زر 'بحث عن طلب'."

    back = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تحديث القائمة", callback_data="list_api_orders")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_orders")]
    ])

    await smart_edit(call, txt, back)

# ... (انسخ باقي الدوال view_ord وما بعدها من الملف السابق، فهي لم تتغير) ...
# =========================================================
# 👇👇👇 باقي الملف كما هو تماماً 👇👇👇
# =========================================================

@router.callback_query(F.data.startswith("view_ord:"))
async def view_order_details(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    oid = call.data.split(":")[1]
    order = database.get_pending_order_by_id(oid)

    if not order:
        return await call.answer("الطلب غير موجود", show_alert=True)

    inputs_txt = ""
    if "inputs" in order:
        inp_data = order["inputs"]
        if isinstance(inp_data, dict):
            for k, v in inp_data.items():
                inputs_txt += f"🔹 {k}: <code>{v}</code>\n"
        elif isinstance(inp_data, list):
            for item in inp_data:
                inputs_txt += f"🔹 معلومات: <code>{item}</code>\n"

    txt = (
        f"📦 <b>تفاصيل الطلب #{order['id']}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"👤 العميل: <code>{order['user_id']}</code>\n"
        f"🛍 المنتج: {order['product']['name']}\n"
        f"💰 السعر: {order['product']['price']}$\n"
        f"🔢 الكمية: {order['qty']}\n"
        f"━━━━━━━━━━━━\n"
        f"{inputs_txt}"
        f"━━━━━━━━━━━━\n"
        f"📅 التاريخ: {order['date']}"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 إعادة المحاولة (API)", callback_data=f"retry_ord:{oid}")],
        [InlineKeyboardButton(text="✅ تم التنفيذ يدوياً", callback_data=f"manual_ord:{oid}")],
        [InlineKeyboardButton(text="❌ إلغاء وإرجاع الرصيد", callback_data=f"ref_ord:{oid}")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="list_pending_orders")]
    ])

    await smart_edit(call, txt, markup)


@router.callback_query(F.data.startswith("retry_ord:"))
async def retry_order_api(call: types.CallbackQuery):
    oid = call.data.split(":")[1]
    o = database.get_pending_order_by_id(oid)
    if not o: return await call.answer("غير موجود")

    await call.answer("⏳ جاري المحاولة...")
    ok, res, uuid, code = await api_manager.execute_order_dynamic(o['product']['id'], o['qty'], o['inputs'],
                                                                  o['params'], o['user_id'])

    if ok:
        # ✅ تمت إزالة save_uuid_locally من هنا
        database.update_order_status(oid, "completed")
        await call.message.answer(f"✅ تم التنفيذ! كود: {res}")
        try:
            await call.bot.send_message(o['user_id'], f"✅ تم تنفيذ طلبك #{oid}\n{res}")
        except:
            pass
        await list_pending_orders(call)
    else:
        await call.message.answer(f"❌ فشل: {res}")

@router.callback_query(F.data.startswith("manual_ord:"))
async def mark_manual_done(call: types.CallbackQuery):
    """Mark order as manually completed."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    oid = call.data.split(":")[1]
    order = database.get_pending_order_by_id(oid)

    if not order:
        return await call.answer("الطلب غير موجود")

    database.update_order_status(oid, "completed")

    try:
        msg_text = (
            f"✅ <b>تحديث حالة الطلب #{oid}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"📦 المنتج: {order['product']['name']}\n"
            f"📊 الحالة الجديدة: <b>مكتمل (Completed)</b>\n"
            f"━━━━━━━━━━━━\n"
            f"شكراً لاستخدامك متجرنا! 🌹"
        )
        await call.bot.send_message(chat_id=order['user_id'], text=msg_text, parse_mode="HTML")
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للعميل: {e}")

    await call.answer("تم الحفظ وإشعار العميل ✅")
    await list_pending_orders(call)


@router.callback_query(F.data.startswith("ref_ord:"))
async def refund_order_admin(call: types.CallbackQuery):
    """Refund order and notify user with balance transparency."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    oid = call.data.split(":")[1]
    order = database.get_pending_order_by_id(oid)

    if not order:
        return await call.answer("الطلب غير موجود")

    cost = float(order['product']['price']) * int(order['qty'])
    rate = settings.get_setting("exchange_rate")

    # Check if PUBG order for currency display consistency
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
                f"━━━━━━━━━━━━\n"
                f"📦 المنتج: {order['product']['name']}\n"
                f"📊 الحالة الجديدة: <b>ملغي (Canceled)</b>\n"
                f"━━━━━━━━━━━━\n"
                f"💰 <b>الرصيد المسترجع:</b> {cost:.2f} $\n"
                f"💎 <b>رصيدك الحالي:</b> {new_bal:.2f} $\n"
                f"━━━━━━━━━━━━\n"
                f"تم إعادة المبلغ إلى محفظتك في البوت."
            )
        else:
            msg_text = (
                f"❌ <b>تحديث حالة الطلب #{oid}</b>\n"
                f"━━━━━━━━━━━━\n"
                f"📦 المنتج: {order['product']['name']}\n"
                f"📊 الحالة الجديدة: <b>ملغي (Canceled)</b>\n"
                f"━━━━━━━━━━━━\n"
                f"💰 <b>الرصيد المسترجع:</b>\n"
                f"🇺🇸 {cost:.2f} $\n"
                f"🇸🇾 {cost_syp:,} ل.س\n"
                f"━━━━━━━━━━━━\n"
                f"💎 <b>رصيدك الحالي:</b>\n"
                f"🇺🇸 {new_bal:.2f} $\n"
                f"🇸🇾 {new_bal_syp:,} ل.س\n"
                f"━━━━━━━━━━━━\n"
                f"تم إعادة المبلغ إلى محفظتك في البوت."
            )
        await call.bot.send_message(chat_id=order['user_id'], text=msg_text, parse_mode="HTML")
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للعميل: {e}")

    await call.answer("تم الإلغاء وإشعار العميل ↩️")
    await list_pending_orders(call)


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

    await msg.answer_document(file, caption="📂 هذه كل الألعاب والخدمات الموجودة في الموقع حالياً.")


@router.callback_query(F.data == "bulk_approve_orders")
async def bulk_approve_orders(call: types.CallbackQuery):
    """Bulk approve all pending orders."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # ✅ استخدام الدالة الجديدة
    all_orders = database.get_all_orders()
    pending = [o for o in all_orders if o.get('status') == 'pending']

    if not pending:
        return await call.answer("لا يوجد طلبات معلقة", show_alert=True)

    # Confirm action
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأكيد قبول الكل", callback_data="confirm_bulk_approve_orders")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="list_pending_orders")]
    ])

    await smart_edit(
        call,
        f"⚠️ <b>تأكيد العملية:</b>\n"
        f"سيتم قبول <b>{len(pending)}</b> طلب.\n"
        f"سيتم تعليمها كمكتملة يدوياً.\n"
        f"هل أنت متأكد؟",
        markup
    )


@router.callback_query(F.data == "confirm_bulk_approve_orders")
async def confirm_bulk_approve_orders(call: types.CallbackQuery):
    """Confirm and execute bulk approve."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    all_orders = database.get_all_orders()
    pending = [o for o in all_orders if o.get('status') == 'pending']

    approved_count = 0

    for order in pending:
        try:
            database.update_order_status(order['id'], "completed")

            # Notify user
            try:
                await call.bot.send_message(
                    order['user_id'],
                    f"✅ <b>تم قبول طلبك #{order['id']}</b>\n"
                    f"📦 المنتج: {order['product']['name']}\n"
                    f"📊 الحالة: مكتمل (Completed)",
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
        f"✅ تم القبول: {approved_count}",
        kb.back_btn("list_pending_orders")
    )


@router.callback_query(F.data == "bulk_reject_orders")
async def bulk_reject_orders(call: types.CallbackQuery):
    """Bulk reject all pending orders."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    all_orders = database.get_all_orders()
    pending = [o for o in all_orders if o.get('status') == 'pending']

    if not pending:
        return await call.answer("لا يوجد طلبات معلقة", show_alert=True)

    # Confirm action
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأكيد رفض الكل", callback_data="confirm_bulk_reject_orders")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="list_pending_orders")]
    ])

    await smart_edit(
        call,
        f"⚠️ <b>تأكيد العملية:</b>\n"
        f"سيتم رفض <b>{len(pending)}</b> طلب.\n"
        f"سيتم إرجاع الرصيد للمستخدمين.\n"
        f"هل أنت متأكد؟",
        markup
    )


@router.callback_query(F.data == "confirm_bulk_reject_orders")
async def confirm_bulk_reject_orders(call: types.CallbackQuery):
    """Confirm and execute bulk reject."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    all_orders = database.get_all_orders()
    pending = [o for o in all_orders if o.get('status') == 'pending']

    rate = settings.get_setting("exchange_rate")
    rejected_count = 0

    for order in pending:
        try:
            cost = float(order['product']['price']) * int(order['qty'])
            cost_syp = int(cost * rate)

            # Refund balance
            new_bal = database.add_balance(order['user_id'], cost)
            new_bal_syp = int(new_bal * rate)

            database.update_order_status(order['id'], "rejected")
            rejected_count += 1

            # Notify user
            try:
                await call.bot.send_message(
                    order['user_id'],
                    f"❌ <b>تم رفض طلبك #{order['id']}</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"📦 المنتج: {order['product']['name']}\n"
                    f"💰 <b>الرصيد المسترجع:</b>\n"
                    f"🇺🇸 {cost:.2f} $\n"
                    f"🇸🇾 {cost_syp:,} ل.س\n"
                    f"━━━━━━━━━━━━\n"
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
        f"❌ تم الرفض: {rejected_count}",
        kb.back_btn("list_pending_orders")
    )