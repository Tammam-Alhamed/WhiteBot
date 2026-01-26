"""Admin order management handlers."""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config
import services.database as database
import services.api_manager as api_manager
import data.keyboards as kb
from bot.utils.helpers import smart_edit

router = Router()


@router.callback_query(F.data == "admin_orders")
async def show_pending_orders(call: types.CallbackQuery):
    """Show pending orders list."""
    # Import here to avoid circular import
    from services.database import load_json, PENDING_FILE
    orders = load_json(PENDING_FILE)

    if not orders:
        return await smart_edit(call, "✅ <b>لا يوجد طلبات شراء معلقة حالياً.</b>", kb.admin_dashboard())

    keyboard = InlineKeyboardBuilder()
    for order in orders:
        btn_txt = f"{order['product']['name']} | {order['id']}"
        keyboard.button(text=btn_txt, callback_data=f"view_ord:{order['id']}")

    keyboard.button(text="🔙 رجوع", callback_data="admin_home")
    keyboard.adjust(1)

    await smart_edit(
        call,
        f"📦 <b>قائمة الطلبات المعلقة ({len(orders)}):</b>\nاضغط على الطلب للتنفيذ.",
        keyboard.as_markup()
    )


@router.callback_query(F.data.startswith("view_ord:"))
async def view_order_details(call: types.CallbackQuery):
    """View order details."""
    oid = call.data.split(":")[1]
    order = database.get_pending_order_by_id(oid)

    if not order:
        return await call.answer("الطلب غير موجود (ربما تم تنفيذه)", show_alert=True)

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
        [InlineKeyboardButton(text="✅ تم التنفيذ يدوياً", callback_data=f"manual_ord:{oid}")],
        [InlineKeyboardButton(text="❌ إلغاء وإرجاع الرصيد", callback_data=f"ref_ord:{oid}")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_orders")]
    ])

    await smart_edit(call, txt, markup)


@router.callback_query(F.data.startswith("retry_ord:"))
async def retry_order_api(call: types.CallbackQuery):
    """Retry order via API."""
    oid = call.data.split(":")[1]
    order = database.get_pending_order_by_id(oid)
    if not order:
        return await call.answer("غير موجود!", show_alert=True)
    
    await call.answer("⏳ جاري الاتصال...")
    success, res_msg, uuid_order, code = await api_manager.execute_order_dynamic(
        order['product']['id'], order['qty'], order['inputs'], order['params']
    )
    
    if success:
        if uuid_order:
            api_manager.save_uuid_locally(order['user_id'], uuid_order)
        database.remove_pending_order(oid)
        try:
            await call.bot.send_message(
                order['user_id'],
                f"✅ <b>طلبك #{oid} تم تنفيذه!</b>\nرقم: <code>{res_msg}</code>",
                parse_mode="HTML"
            )
        except:
            pass
        await call.message.answer(f"✅ تم التنفيذ! كود: {res_msg}")
        await show_pending_orders(call)
    elif code == 100:
        await call.message.answer("❌ رصيد الموقع ما زال غير كافٍ.")
    else:
        await call.message.answer(f"❌ خطأ: {res_msg}")


@router.callback_query(F.data.startswith("manual_ord:"))
async def mark_manual_done(call: types.CallbackQuery):
    """Mark order as manually completed."""
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
    await show_pending_orders(call)


@router.callback_query(F.data.startswith("ref_ord:"))
async def refund_order_admin(call: types.CallbackQuery):
    """Refund order and notify user."""
    oid = call.data.split(":")[1]
    order = database.get_pending_order_by_id(oid)
    
    if not order:
        return await call.answer("الطلب غير موجود")
    
    cost = float(order['product']['price']) * int(order['qty'])
    database.add_balance(order['user_id'], cost)
    database.remove_pending_order(oid)
    
    try:
        msg_text = (
            f"❌ <b>تحديث حالة الطلب #{oid}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"📦 المنتج: {order['product']['name']}\n"
            f"📊 الحالة الجديدة: <b>ملغي (Canceled)</b>\n"
            f"💰 الرصيد المسترجع: <b>{cost}$</b>\n"
            f"━━━━━━━━━━━━\n"
            f"تم إعادة المبلغ إلى محفظتك في البوت."
        )
        await call.bot.send_message(chat_id=order['user_id'], text=msg_text, parse_mode="HTML")
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للعميل: {e}")
    
    await call.answer("تم الإلغاء وإشعار العميل ↩️")
    await show_pending_orders(call)


@router.message(Command("get_cats"))
async def export_categories(msg: types.Message):
    """Export categories list."""
    if msg.from_user.id not in config.ADMIN_IDS:
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
