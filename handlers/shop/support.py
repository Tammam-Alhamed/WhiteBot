"""معالجات التواصل مع الدعم للطلبات والإيداعات."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import asyncio
import services.database as database
import services.settings as settings
import config
import data.keyboards as kb
from bot.utils.helpers import smart_edit
from states.shop import SupportState

router = Router()


def _build_order_support_details(order: dict, is_api: bool) -> str:
    if is_api:
        order_id = order.get('uuid', order.get('id', '---'))
        service_name = order.get('product_name', order.get('product', {}).get('name', 'API Service'))
        price = order.get('price', 0)
        date = order.get('created_at', order.get('date', '---'))
        status = order.get('status', 'pending')
    else:
        order_id = order.get('id', '---')
        service_name = order.get('product', {}).get('name', 'Local Service')
        qty = order.get('qty', 1)
        price_unit = float(order.get('product', {}).get('price', 0))
        price = price_unit * int(qty)
        date = order.get('date', '---')
        status = order.get('status', 'pending')

    return (
        f"📦 <b>تفاصيل الطلب</b>\n"
        f"🆔 <b>الرقم:</b> <code>{order_id}</code>\n"
        f"🛍 <b>الخدمة:</b> {service_name}\n"
        f"💰 <b>القيمة:</b> {price}$\n"
        f"📌 <b>الحالة:</b> {status}\n"
        f"📅 <b>التاريخ:</b> {date}\n"
    )


@router.callback_query(F.data.startswith("support_order:"))
async def support_order_start(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    type_code = parts[1]
    oid = parts[2]
    page = parts[3] if len(parts) > 3 else "1"
    user_id = call.from_user.id

    is_api = (type_code == "A")
    if is_api:
        orders = await asyncio.to_thread(database.get_user_api_history, user_id, 100)
        target_order = next((o for o in orders if str(o.get('uuid')) == str(oid)), None)
    else:
        orders = await asyncio.to_thread(database.get_user_local_orders, user_id)
        target_order = next((o for o in orders if str(o.get('id')) == str(oid)), None)

    if not target_order:
        return await call.answer("❌ الطلب غير موجود.", show_alert=True)

    details = _build_order_support_details(target_order, is_api=is_api)
    return_cb = f"view_my_ord:{type_code}:{oid}:{page}"

    await state.update_data(
        support_return=return_cb,
        support_details=details,
        support_title="📞 تواصل مع الدعم بخصوص هذا الطلب"
    )
    await state.set_state(SupportState.waiting_for_support_note)

    await smart_edit(
        call,
        "✍️ اكتب ملاحظتك الآن وسيتم إرسالها للدعم:",
        kb.back_btn(return_cb)
    )


@router.callback_query(F.data.startswith("support_deposit:"))
async def support_deposit_start(call: types.CallbackQuery, state: FSMContext):
    dep_id = call.data.split(":")[1]
    dep = await asyncio.to_thread(database.get_deposit_request, dep_id)
    if not dep:
        return await call.answer("❌ الإيداع غير موجود.", show_alert=True)

    details = (
        f"💳 <b>تفاصيل الإيداع</b>\n"
        f"🆔 <b>الرقم:</b> <code>{dep.get('id')}</code>\n"
        f"💳 <b>الطريقة:</b> {dep.get('method')}\n"
        f"💰 <b>المبلغ:</b> {dep.get('amount')}\n"
        f"🧾 <b>رقم العملية:</b> <code>{dep.get('txn_id')}</code>\n"
        f"📅 <b>التاريخ:</b> {dep.get('date')}\n"
        f"📌 <b>الحالة:</b> {dep.get('status')}\n"
    )
    return_cb = f"view_my_dep:{dep_id}"

    await state.update_data(
        support_return=return_cb,
        support_details=details,
        support_title="📞 تواصل مع الدعم بخصوص هذا الإيداع"
    )
    await state.set_state(SupportState.waiting_for_support_note)

    await smart_edit(
        call,
        "✍️ اكتب ملاحظتك الآن وسيتم إرسالها للدعم:",
        kb.back_btn(return_cb)
    )


@router.message(SupportState.waiting_for_support_note)
async def support_send_note(msg: types.Message, state: FSMContext):
    if not msg.text:
        return await msg.answer("❌ يرجى إرسال النص فقط.")

    data = await state.get_data()
    details = data.get("support_details", "")
    title = data.get("support_title", "📞 رسالة دعم")
    note = msg.text.strip()
    user_id = msg.from_user.id
    support_msg = (
        f"{title}\n"
        f"👤 <b>المستخدم:</b> <code>{user_id}</code>\n"
        f"━━━━━━━━━━━━\n"
        f"{details}\n"
        f"📝 <b>ملاحظة المستخدم:</b>\n{note}"
    )

    admin_ids = await asyncio.to_thread(database.get_all_admin_ids)

    sent_successfully = False
    for aid in admin_ids:
        try:
            await msg.bot.send_message(aid, support_msg, parse_mode="HTML")
            sent_successfully = True
        except Exception:
            continue

    if sent_successfully:
        await msg.answer("✅ تم إرسال رسالتك للدعم.", reply_markup=kb.back_btn("my_account"))
    else:
        await msg.answer("❌ تعذر إرسال الرسالة للدعم. حاول مرة أخرى لاحقًا.")

    await state.clear()
