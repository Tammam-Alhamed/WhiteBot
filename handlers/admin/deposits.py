"""Admin deposit management handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.database as database
import services.settings as settings
import data.keyboards as kb
from bot.utils.helpers import smart_edit, format_price
from states.admin import AdminState

router = Router()


@router.callback_query(F.data == "admin_deposits")
async def show_deposit_requests(call: types.CallbackQuery):
    """Show pending deposit requests."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # ✅ استخدام الدالة الجديدة من قاعدة البيانات
    all_reqs = database.get_all_deposit_requests()

    pending = [r for r in all_reqs if r.get('status') == 'pending']

    if not pending:
        return await smart_edit(call, "✅ <b>لا يوجد طلبات إيداع معلقة حالياً.</b>", kb.admin_dashboard())

    keyboard = InlineKeyboardBuilder()
    for req in pending:
        usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
        currency = "$" if req['method'] in usd_methods else "ل.س"
        btn_text = f"{req['method']} | {req['amount']} {currency} | {req['user_id']}"
        keyboard.button(text=btn_text, callback_data=f"view_dep_req:{req['id']}")

    # Add bulk action buttons
    keyboard.button(text="✅ قبول الكل", callback_data="bulk_approve_deposits")
    keyboard.button(text="❌ رفض الكل", callback_data="bulk_reject_deposits")
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
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    req_id = call.data.split(":")[1]
    req = database.get_deposit_request(req_id)

    if not req:
        return await call.answer("⚠️ الطلب غير موجود (ربما تمت معالجته)", show_alert=True)

    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
    currency = "$" if req['method'] in usd_methods else "ل.س"
    rate = settings.get_setting("exchange_rate")

    # Calculate what will be added (with commission)
    commission = settings.get_deposit_commission()
    amount = float(req['amount'])

    if req['method'] in usd_methods:
        deposit_usd = amount
        deposit_syp = int(amount * rate)
    else:
        deposit_syp = int(amount)
        deposit_usd = amount / rate

    commission_amount = deposit_usd * (commission / 100)
    final_usd = deposit_usd - commission_amount
    final_syp = int(round(final_usd * rate))

    txt = (
        f"📝 <b>تفاصيل طلب الإيداع #{req['id']}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"👤 المستخدم: <code>{req['user_id']}</code>\n"
        f"💳 الطريقة: <b>{req['method']}</b>\n"
        f"💰 المبلغ المرسل: <b>{amount} {currency}</b>\n"
        f"💵 الرصيد المضاف (بعد العمولة):\n"
        f"🇺🇸 {final_usd:.2f} $\n"
        f"🇸🇾 {final_syp:,} ل.س\n"
    )

    if commission > 0:
        txt += f"📊 العمولة ({commission}%): {commission_amount:.2f} $\n"

    txt += (
        f"🔢 رقم العملية: <code>{req['txn_id']}</code>\n"
        f"📅 التاريخ: {req['date']}\n"
    )

    if req.get('proof_image_id'):
        txt += f"📸 يوجد صورة إثبات\n"

    txt += f"━━━━━━━━━━━━\n"
    txt += f"⚠️ <b>يرجى التأكد من وصول الحوالة قبل القبول.</b>"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ قبول وإضافة", callback_data=f"approve_dep:{req_id}"),
            InlineKeyboardButton(text="❌ رفض وحذف", callback_data=f"reject_dep:{req_id}")
        ],
        [InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="admin_deposits")]
    ])

    # Show proof image if available
    if req.get('proof_image_id'):
        try:
            # Try sending as photo
            await call.message.answer_photo(
                req['proof_image_id'],
                caption=txt,
                reply_markup=markup,
                parse_mode="HTML"
            )
            # Only delete the previous message if sending photo succeeded
            await call.message.delete()
            return
        except Exception:
            try:
                # Fallback: Try sending as document (if it was uploaded as file)
                await call.message.answer_document(
                    req['proof_image_id'],
                    caption=txt,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
                await call.message.delete()
                return
            except:
                pass

    await smart_edit(call, txt, markup)


@router.callback_query(F.data.startswith("approve_dep:"))
async def approve_deposit(call: types.CallbackQuery):
    """Approve deposit request with commission."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    req_id = call.data.split(":")[1]
    req = database.get_deposit_request(req_id)

    if not req:
        return await call.answer("الطلب غير موجود", show_alert=True)

    amount = float(req['amount'])
    method = req['method']
    rate = settings.get_setting("exchange_rate")
    commission = settings.get_deposit_commission()

    if rate == 0:
        rate = 1

    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]

    # Calculate deposit amounts
    if method in usd_methods:
        deposit_usd = amount
    else:
        deposit_usd = amount / rate

    # Apply commission
    commission_amount = deposit_usd * (commission / 100)
    final_usd = deposit_usd - commission_amount
    final_syp = int(round(final_usd * rate))

    # Add balance (mark as deposit for statistics) + keep row for user history
    new_bal = database.add_balance(req['user_id'], final_usd, is_deposit=True)
    database.update_deposit_status(req_id, "approved")

    new_bal_syp = int(round(new_bal * rate))

    # --- Handle Photo vs Text Message editing ---
    current_content = call.message.caption if call.message.caption else (call.message.text or "")

    new_status_text = (
        f"{current_content}\n\n✅ <b>تم القبول</b>\n"
        f"💵 أضيف: {final_usd:.2f}$ ({final_syp:,} ل.س)\n"
        f"💳 الرصيد بعد الموافقة: {new_bal:.2f}$ ({new_bal_syp:,} ل.س)\n"
        f"بواسطة: {call.from_user.first_name}"
    )

    if call.message.photo:
        await call.message.edit_caption(
            caption=new_status_text,
            reply_markup=None,
            parse_mode="HTML"
        )
    else:
        await call.message.edit_text(
            text=new_status_text,
            reply_markup=None,
            parse_mode="HTML"
        )

    method_name = method.replace('_', ' ').upper()
    if method == "syriatel":
        method_name = "سيريتيل كاش"
    elif method == "sham_syp":
        method_name = "شام كاش (سوري)"
    elif method == "sham_usd":
        method_name = "شام كاش (دولار)"
    elif method == "usdt_bep20":
        method_name = "USDT (BEP20)"
    elif method == "usdt_coinex":
        method_name = "CoinEx (Email)"

    user_msg = (
        f"✅ <b>تم شحن رصيدك بنجاح!</b>\n"
        f"━━━━━━━━━━━━\n"
        f"💳 <b>الطريقة:</b> {method_name}\n"
        f"💹 <b>سعر الصرف:</b> {rate} ل.س\n"
        f"📥 <b>المبلغ المرسل:</b>\n"
    )
    if method in usd_methods:
        user_msg += f"🇺🇸 {amount:.2f} $\n🇸🇾 {int(amount * rate):,} ل.س\n\n"
    else:
        user_msg += f"🇸🇾 {int(amount):,} ل.س\n🇺🇸 {deposit_usd:.2f} $\n\n"

    if commission > 0:
        user_msg += (
            f"📊 <b>العمولة ({commission}%):</b> {commission_amount:.2f} $\n\n"
        )

    user_msg += (
        f"➕ <b>المبلغ المضاف:</b>\n"
        f"🇺🇸 {final_usd:.2f} $\n"
        f"🇸🇾 {final_syp:,} ل.س\n\n"
        f"💳 <b>رصيدك بعد الموافقة:</b>\n"
        f"🇺🇸 <b>{new_bal:.2f} $</b>\n"
        f"🇸🇾 <b>{new_bal_syp:,} ل.س</b>\n"
        f"━━━━━━━━━━━━\n"
        f"شكراً لثقتك بنا!"
    )

    try:
        await call.bot.send_message(
            req['user_id'],
            user_msg,
            parse_mode="HTML",
            reply_markup=kb.back_btn("deposit_menu")
        )
    except:
        pass


@router.callback_query(F.data.startswith("reject_dep:"))
async def reject_deposit(call: types.CallbackQuery, state: FSMContext):
    """Reject deposit request (with optional admin note)."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    req_id = call.data.split(":")[1]
    req = database.get_deposit_request(req_id)

    if not req:
        return await call.answer("الطلب غير موجود", show_alert=True)

    ask_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ نعم", callback_data=f"reject_dep_note_yes:{req_id}")],
        [InlineKeyboardButton(text="❌ لا", callback_data=f"reject_dep_note_no:{req_id}")]
    ])
    await state.clear()
    await smart_edit(call, "هل تريد إضافة ملاحظة؟", ask_kb)
    return


@router.callback_query(F.data.startswith("reject_dep_note_no:"))
async def reject_deposit_no_note(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    req_id = call.data.split(":")[1]
    req = database.get_deposit_request(req_id)
    if not req:
        return await call.answer("الطلب غير موجود", show_alert=True)

    database.update_deposit_status(req_id, "rejected")

    # --- Handle Photo vs Text Message editing ---
    current_content = call.message.caption if call.message.caption else (call.message.text or "")

    new_status_text = (
        f"{current_content}\n\n❌ <b>تم رفض الطلب</b>\n"
        f"بواسطة: {call.from_user.first_name}"
    )

    if call.message.photo:
        await call.message.edit_caption(
            caption=new_status_text,
            reply_markup=None,
            parse_mode="HTML"
        )
    else:
        await call.message.edit_text(
            text=new_status_text,
            reply_markup=None,
            parse_mode="HTML"
        )

    try:
        await call.bot.send_message(
            req['user_id'],
            "❌ <b>عذراً، تم رفض طلب الإيداع الخاص بك.</b>\nيرجى التأكد من رقم العملية أو التواصل مع الدعم.",
            parse_mode="HTML",
            reply_markup=kb.back_btn("deposit_menu")
        )
    except:
        pass


@router.callback_query(F.data.startswith("reject_dep_note_yes:"))
async def reject_deposit_yes_note(call: types.CallbackQuery, state: FSMContext):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    req_id = call.data.split(":")[1]
    req = database.get_deposit_request(req_id)
    if not req:
        return await call.answer("الطلب غير موجود", show_alert=True)

    await state.update_data(reject_dep_id=req_id)
    await state.set_state(AdminState.waiting_for_reject_note)
    await smart_edit(call, "✍️ اكتب الملاحظة الآن وسيتم إرسالها للمستخدم:", kb.back_btn("admin_deposits"))


@router.message(AdminState.waiting_for_reject_note)
async def reject_deposit_write_note(msg: types.Message, state: FSMContext):
    if not database.is_user_admin(msg.from_user.id):
        await state.clear()
        return

    note = (msg.text or "").strip()
    if not note:
        return await msg.answer("❌ يرجى إرسال نص الملاحظة فقط.")

    data = await state.get_data()
    req_id = data.get("reject_dep_id")
    req = database.get_deposit_request(req_id)
    if not req:
        await state.clear()
        return await msg.answer("❌ الطلب غير موجود أو تمت معالجته.")

    note = (msg.text or "").strip()
    data = await state.get_data()
    req_id = data.get("reject_dep_id")

    # تحديث الحالة مع حفظ الملاحظة في قاعدة البيانات
    database.update_deposit_status(req_id, "rejected", note=note)

    try:
        await msg.bot.send_message(
            req["user_id"],
            "❌ <b>تم رفض طلب الإيداع الخاص بك.</b>\n"
            f"📝 <b>ملاحظة الإدارة:</b>\n{note}",
            parse_mode="HTML",
            reply_markup=kb.back_btn("deposit_menu")
        )
    except:
        pass

    await msg.answer("✅ تم رفض الطلب وإرسال الملاحظة للمستخدم.", reply_markup=kb.back_to_admin())
    await state.clear()


@router.callback_query(F.data == "bulk_approve_deposits")
async def bulk_approve_deposits(call: types.CallbackQuery):
    """Bulk approve all pending deposits."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # ✅ استخدام الدالة الجديدة
    all_reqs = database.get_all_deposit_requests()
    pending = [r for r in all_reqs if r.get('status') == 'pending']

    if not pending:
        return await call.answer("لا يوجد طلبات معلقة", show_alert=True)

    # Confirm action
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأكيد قبول الكل", callback_data="confirm_bulk_approve_deposits")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_deposits")]
    ])

    await smart_edit(
        call,
        f"⚠️ <b>تأكيد العملية:</b>\n"
        f"سيتم قبول <b>{len(pending)}</b> طلب إيداع.\n"
        f"هل أنت متأكد؟",
        markup
    )


@router.callback_query(F.data == "confirm_bulk_approve_deposits")
async def confirm_bulk_approve_deposits(call: types.CallbackQuery):
    """Confirm and execute bulk approve."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # ✅ استخدام الدالة الجديدة
    all_reqs = database.get_all_deposit_requests()
    pending = [r for r in all_reqs if r.get('status') == 'pending']

    rate = settings.get_setting("exchange_rate")
    commission = settings.get_deposit_commission()
    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]

    if rate == 0:
        rate = 1

    approved_count = 0
    failed_count = 0

    for req in pending:
        try:
            amount = float(req['amount'])
            method = req['method']

            # Calculate final amount
            if method in usd_methods:
                deposit_usd = amount
            else:
                deposit_usd = amount / rate

            commission_amount = deposit_usd * (commission / 100)
            final_usd = deposit_usd - commission_amount

            database.add_balance(req['user_id'], final_usd, is_deposit=True)
            database.update_deposit_status(req['id'], "approved")
            approved_count += 1

            # Notify user
            try:
                final_syp = int(final_usd * rate)
                await call.bot.send_message(
                    req['user_id'],
                    f"✅ <b>تم قبول طلب الإيداع #{req['id']}</b>\n"
                    f"💵 الرصيد المضاف: {final_usd:.2f} $ ({final_syp:,} ل.س)",
                    parse_mode="HTML"
                )
            except:
                pass
        except:
            failed_count += 1

    await smart_edit(
        call,
        f"✅ <b>تمت العملية!</b>\n"
        f"✅ تم القبول: {approved_count}\n"
        f"❌ فشل: {failed_count}",
        kb.back_btn("admin_deposits")
    )


@router.callback_query(F.data == "bulk_reject_deposits")
async def bulk_reject_deposits(call: types.CallbackQuery):
    """Bulk reject all pending deposits."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # ✅ استخدام الدالة الجديدة
    all_reqs = database.get_all_deposit_requests()
    pending = [r for r in all_reqs if r.get('status') == 'pending']

    if not pending:
        return await call.answer("لا يوجد طلبات معلقة", show_alert=True)

    # Confirm action
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأكيد رفض الكل", callback_data="confirm_bulk_reject_deposits")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_deposits")]
    ])

    await smart_edit(
        call,
        f"⚠️ <b>تأكيد العملية:</b>\n"
        f"سيتم رفض <b>{len(pending)}</b> طلب إيداع.\n"
        f"هل أنت متأكد؟",
        markup
    )


@router.callback_query(F.data == "confirm_bulk_reject_deposits")
async def confirm_bulk_reject_deposits(call: types.CallbackQuery):
    """Confirm and execute bulk reject."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    # ✅ استخدام الدالة الجديدة
    all_reqs = database.get_all_deposit_requests()
    pending = [r for r in all_reqs if r.get('status') == 'pending']

    rejected_count = 0

    for req in pending:
        try:
            database.update_deposit_status(req['id'], "rejected")
            rejected_count += 1

            # Notify user
            try:
                await call.bot.send_message(
                    req['user_id'],
                    f"❌ <b>تم رفض طلب الإيداع #{req['id']}</b>\n"
                    f"يرجى التأكد من رقم العملية أو التواصل مع الدعم.",
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
        kb.back_btn("admin_deposits")
    )
