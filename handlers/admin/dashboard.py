"""Admin dashboard handlers."""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import config
import services.settings as settings
import services.database as database
import data.keyboards as kb
from bot.utils.helpers import smart_edit
from states.admin import AdminState

router = Router()


@router.message(Command("admin"))
async def open_admin(msg: types.Message):
    """Open admin panel."""
    # التحقق من صلاحيات الأدمن (ديناميكي)
    if not database.is_user_admin(msg.from_user.id):
        return

    rate = settings.get_setting("exchange_rate")
    maint = settings.get_setting("maintenance_mode")
    status = "✅ مفعل" if maint else "❌ معطل"
    
    txt = (
        f"👑 <b>لوحة الإدارة</b>\n"
        f"💵 سعر الصرف: <b>{rate} ل.س</b>\n"
        f"🛠 وضع الصيانة: <b>{status}</b>"
    )
    await msg.answer(txt, reply_markup=kb.admin_dashboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_home")
@router.callback_query(F.data == "admin_dashboard")
async def admin_home(call: types.CallbackQuery, state: FSMContext):
    """Show admin dashboard."""
    # التحقق من صلاحيات الأدمن (ديناميكي)
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    await state.clear()

    rate = settings.get_setting("exchange_rate")
    maint = settings.get_setting("maintenance_mode")
    status = "✅ مفعل" if maint else "❌ معطل"

    txt = (
        f"👑 <b>لوحة الإدارة</b>\n"
        f"💵 سعر الصرف: <b>{rate} ل.س</b>\n"
        f"🛠 وضع الصيانة: <b>{status}</b>"
    )
    await smart_edit(call, txt, kb.admin_dashboard())


@router.callback_query(F.data == "close_admin")
async def close_admin_panel(call: types.CallbackQuery, state: FSMContext):
    """Close admin panel."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    await state.clear()
    try:
        await call.message.delete()
    except:
        await call.message.edit_text("✅ تم إغلاق اللوحة.")


@router.callback_query(F.data == "admin_maintenance")
async def toggle_maintenance(call: types.CallbackQuery, state: FSMContext):
    """Toggle maintenance mode."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    current_status = settings.get_setting("maintenance_mode")
    new_status = not current_status
    settings.update_setting("maintenance_mode", new_status)
    
    msg = "تم تفعيل وضع الصيانة 🛠" if new_status else "تم تعطيل وضع الصيانة ✅"
    await call.answer(msg)
    
    await admin_home(call, state)


@router.callback_query(F.data == "admin_broadcast")
async def ask_broadcast_message(call: types.CallbackQuery, state: FSMContext):
    """Ask for broadcast message."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    cancel_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_home")]
    ])
    
    await smart_edit(
        call,
        "📨 <b>إرسال رسالة للكل:</b>\n\nأرسل الآن الرسالة التي تريد نشرها (نص، صورة، فيديو... أي شيء).\nسيتم إرسالها لجميع المشتركين.",
        cancel_kb
    )
    await state.set_state(AdminState.waiting_for_broadcast_msg)


@router.message(AdminState.waiting_for_broadcast_msg)
async def execute_broadcast(msg: types.Message, state: FSMContext):
    """Execute broadcast to all users."""
    
    # تأكيد أن المرسل ما زال أدمن
    if not database.is_user_admin(msg.from_user.id):
        await state.clear()
        return

    users = database.get_all_user_ids()
    if not users:
        await msg.answer("لا يوجد مستخدمين لإرسال الرسالة لهم!")
        await state.clear()
        return

    status_msg = await msg.answer(f"⏳ جاري الإرسال إلى {len(users)} مستخدم...\nيرجى الانتظار وعدم إيقاف البوت.")
    
    sent_count = 0
    blocked_count = 0
    
    for user_id in users:
        try:
            await msg.copy_to(chat_id=user_id)
            sent_count += 1
            await asyncio.sleep(0.05) 
        except Exception as e:
            blocked_count += 1
    
    report = (
        f"✅ <b>تم انتهاء الحملة!</b>\n"
        f"━━━━━━━━━━━━\n"
        f"📨 تم الإرسال بنجاح: <b>{sent_count}</b>\n"
        f"⛔ لم تصل (حظروا البوت): <b>{blocked_count}</b>\n"
        f"👥 العدد الكلي: <b>{len(users)}</b>"
    )
    
    await status_msg.edit_text(report, parse_mode="HTML", reply_markup=kb.back_to_admin())
    await state.clear()


@router.callback_query(F.data == "admin_pending_all")
async def show_all_pending(call: types.CallbackQuery):
    """Show unified view of all pending requests (deposits + orders)."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    from services.database import load_json, DEPOSITS_FILE, PENDING_FILE
    
    # Get pending deposits
    all_deposits = load_json(DEPOSITS_FILE)
    pending_deposits = [r for r in all_deposits if r.get('status') == 'pending']
    
    # Get pending orders
    all_orders = load_json(PENDING_FILE)
    pending_orders = [o for o in all_orders if o.get('status') == 'pending']
    
    total_pending = len(pending_deposits) + len(pending_orders)
    
    if total_pending == 0:
        return await smart_edit(
            call,
            "✅ <b>لا يوجد طلبات معلقة حالياً.</b>",
            kb.admin_dashboard()
        )
    
    keyboard = InlineKeyboardBuilder()
    
    # Add deposit requests
    if pending_deposits:
        keyboard.button(text="━━ 💰 طلبات الإيداع ━━", callback_data="ignore")
        for req in pending_deposits[:10]:  # Limit to 10
            usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
            currency = "$" if req['method'] in usd_methods else "ل.س"
            btn_text = f"💰 {req['method']} | {req['amount']} {currency} | {req['user_id']}"
            keyboard.button(text=btn_text, callback_data=f"view_dep_req:{req['id']}")
    
    # Add order requests
    if pending_orders:
        keyboard.button(text="━━ 📦 طلبات الشراء ━━", callback_data="ignore")
        for order in pending_orders[:10]:  # Limit to 10
            btn_text = f"📦 {order['product']['name']} | {order['id']}"
            keyboard.button(text=btn_text, callback_data=f"view_ord:{order['id']}")
    
    keyboard.button(text="🔙 رجوع", callback_data="admin_home")
    keyboard.adjust(1)
    
    txt = (
        f"📋 <b>جميع الطلبات المعلقة ({total_pending}):</b>\n"
        f"━━━━━━━━━━━━\n"
        f"💰 طلبات الإيداع: {len(pending_deposits)}\n"
        f"📦 طلبات الشراء: {len(pending_orders)}\n"
        f"━━━━━━━━━━━━\n"
        f"اضغط على الطلب لعرض التفاصيل."
    )
    
    await smart_edit(call, txt, keyboard.as_markup())
