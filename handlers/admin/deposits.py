"""Admin deposit management handlers."""
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.database as database
import services.settings as settings
import data.keyboards as kb
from bot.utils.helpers import smart_edit

router = Router()


@router.callback_query(F.data == "admin_deposits")
async def show_deposit_requests(call: types.CallbackQuery):
    """Show pending deposit requests."""
    from services.database import load_json, DEPOSITS_FILE
    all_reqs = load_json(DEPOSITS_FILE)

    pending = [r for r in all_reqs if r.get('status') == 'pending']

    if not pending:
        return await smart_edit(call, "✅ <b>لا يوجد طلبات إيداع معلقة حالياً.</b>", kb.admin_dashboard())

    keyboard = InlineKeyboardBuilder()
    for req in pending:
        btn_text = f"{req['method']} | {req['amount']} | {req['user_id']}"
        keyboard.button(text=btn_text, callback_data=f"view_dep_req:{req['id']}")

    keyboard.button(text="🔙 رجوع", callback_data="admin_home")
    keyboard.adjust(1)

    await smart_edit(
        call,
        f"💰 <b>طلبات الإيداع المعلقة ({len(pending)}):</b>\nاضغط على الطلب لعرض التفاصيل واتخاذ قرار.",
        keyboard.as_markup()
    )


@router.callback_query(F.data.startswith("view_dep_req:"))
async def view_deposit_details(call: types.CallbackQuery):
    """View deposit request details."""
    req_id = call.data.split(":")[1]
    req = database.get_deposit_request(req_id)

    if not req:
        return await call.answer("⚠️ الطلب غير موجود (ربما تمت معالجته)", show_alert=True)

    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
    currency = "$" if req['method'] in usd_methods else "ل.س"

    txt = (
        f"📝 <b>تفاصيل طلب الإيداع #{req['id']}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"👤 المستخدم: <code>{req['user_id']}</code>\n"
        f"💳 الطريقة: <b>{req['method']}</b>\n"
        f"💰 المبلغ: <b>{req['amount']} {currency}</b>\n"
        f"🔢 رقم العملية: <code>{req['txn_id']}</code>\n"
        f"📅 التاريخ: {req['date']}\n"
        f"━━━━━━━━━━━━\n"
        f"⚠️ <b>يرجى التأكد من وصول الحوالة قبل القبول.</b>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ قبول وإضافة", callback_data=f"approve_dep:{req_id}"),
            InlineKeyboardButton(text="❌ رفض وحذف", callback_data=f"reject_dep:{req_id}")
        ],
        [InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="admin_deposits")]
    ])

    await smart_edit(call, txt, markup)


@router.callback_query(F.data.startswith("approve_dep:"))
async def approve_deposit(call: types.CallbackQuery):
    """Approve deposit request."""
    req_id = call.data.split(":")[1]
    req = database.get_deposit_request(req_id)

    if not req:
        return await call.answer("الطلب غير موجود", show_alert=True)

    amount = float(req['amount'])
    method = req['method']
    rate = settings.get_setting("exchange_rate")
    if rate == 0:
        rate = 1

    final_usd = 0.0
    display_syp = 0
    display_usd = 0.0

    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]

    if method in usd_methods:
        final_usd = amount
        display_usd = amount
        display_syp = int(amount * rate)
    else:
        final_usd = amount / rate
        display_syp = int(amount)
        display_usd = final_usd

    new_bal = database.add_balance(req['user_id'], final_usd)
    database.remove_deposit_request(req_id)

    new_bal_syp = int(new_bal * rate)

    await call.message.edit_text(
        f"{call.message.html_text}\n\n✅ <b>تم القبول</b>\n"
        f"💵 أضيف: {round(final_usd, 2)}$\n"
        f"بواسطة: {call.from_user.first_name}",
        reply_markup=None,
        parse_mode="HTML"
    )

    user_msg = (
        f"✅ <b>تم شحن رصيدك بنجاح!</b>\n"
        f"━━━━━━━━━━━━\n"
        f"💳 <b>الطريقة:</b> {method.replace('_', ' ').upper()}\n"
        f"📥 <b>المبلغ المستلم:</b>\n"
        f"🇸🇾 {display_syp:,} ل.س\n"
        f"🇺🇸 {round(display_usd, 2)} $\n\n"
        f"💵 <b>الرصيد المضاف:</b> {round(final_usd, 2)}$\n"
        f"💎 <b>رصيدك الحالي:</b>\n"
        f"🇺🇸 <b>{new_bal} $</b>\n"
        f"🇸🇾 <b>{new_bal_syp:,} ل.س</b>\n"
        f"━━━━━━━━━━━━\n"
        f"شكراً لثقتك بنا! 🌹"
    )

    try:
        await call.bot.send_message(req['user_id'], user_msg, parse_mode="HTML")
    except:
        pass


@router.callback_query(F.data.startswith("reject_dep:"))
async def reject_deposit(call: types.CallbackQuery):
    """Reject deposit request."""
    req_id = call.data.split(":")[1]
    req = database.get_deposit_request(req_id)

    if not req:
        return await call.answer("الطلب غير موجود", show_alert=True)

    database.remove_deposit_request(req_id)

    await call.message.edit_text(
        f"{call.message.html_text}\n\n❌ <b>تم رفض الطلب</b>\nبواسطة: {call.from_user.first_name}",
        reply_markup=None,
        parse_mode="HTML"
    )

    try:
        await call.bot.send_message(
            req['user_id'],
            "❌ <b>عذراً، تم رفض طلب الإيداع الخاص بك.</b>\nيرجى التأكد من رقم العملية أو التواصل مع الدعم.",
            parse_mode="HTML"
        )
    except:
        pass
