"""Deposit and Account handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import asyncio  # ✅ 1. إضافة مكتبة asyncio

from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import services.database as database
import services.settings as settings
import data.keyboards as kb
from bot.utils.helpers import smart_edit, format_price
from states.shop import DepositState

router = Router()

def _build_balance_text(balance_usd: float, total_deposited_usd: float, rate: float) -> str:
    b_syp = int(round(balance_usd * rate))
    total_dep_syp = int(round(total_deposited_usd * rate))
    return (
        f"💰 <b>محفظتك:</b>\n"
        f"💵 {balance_usd:.2f} $\n"
        f"💷 {b_syp:,} ل.س\n"
        f"━━━━━━━━━━━━\n"
        f"📊 <b>إجمالي الإيداعات:</b>\n"
        f"💵 {total_deposited_usd:.2f} $\n"
        f"💷 {total_dep_syp:,} ل.س"
    )

# ✅ دالة زر "حسابي" الجديد
@router.callback_query(F.data == "my_account")
async def show_my_account(call: types.CallbackQuery):
    """عرض قائمة حسابي."""
    await smart_edit(call, "👤 <b>حسابي</b>\nاختر القسم المطلوب:", kb.my_account_menu())


@router.callback_query(F.data == "my_wallet")
async def show_my_wallet(call: types.CallbackQuery):
    """Show wallet balance with deposit shortcut."""
    u = call.from_user.id
    b = await asyncio.to_thread(database.get_balance, u)
    total_deposited = await asyncio.to_thread(database.get_total_deposited, u)
    rate = settings.get_setting("exchange_rate")
    txt = _build_balance_text(b, total_deposited, rate)
    await smart_edit(call, txt, kb.wallet_balance_menu())


@router.callback_query(F.data == "my_deposits")
async def show_my_deposits(call: types.CallbackQuery):
    """عرض إيداعات المستخدم (معلقة + مقبولة + مرفوضة)."""
    u = call.from_user.id
    deposits = await asyncio.to_thread(database.get_user_deposits, u)

    # تقسيم الإيداعات حسب الحالة
    pending = [d for d in deposits if (d.get("status") or "").lower() == "pending"]
    approved = [d for d in deposits if (d.get("status") or "").lower() == "approved"]
    rejected = [d for d in deposits if (d.get("status") or "").lower() == "rejected"]  # إضافة المرفوضة هنا

    def _fmt_row(d):
        return f"#{d.get('id')} | {d.get('method')} | {d.get('amount')} | {d.get('date')}"

    txt = "💳 <b>إيداعاتي</b>\n"
    txt += "━━━━━━━━━━━━\n"

    txt += "⏳ <b>معلّقة:</b>\n"
    txt += ("\n".join(_fmt_row(d) for d in pending[:10]) + "\n") if pending else "لا يوجد طلبات معلقة.\n"

    txt += "━━━━━━━━━━━━\n"
    txt += "✅ <b>مقبولة:</b>\n"
    txt += ("\n".join(_fmt_row(d) for d in approved[:10]) + "\n") if approved else "لا يوجد طلبات مقبولة.\n"

    txt += "━━━━━━━━━━━━\n"
    txt += "❌ <b>مرفوضة:</b>\n"
    txt += ("\n".join(_fmt_row(d) for d in rejected[:10])) if rejected else "لا يوجد طلبات مرفوضة."

    kb_builder = InlineKeyboardBuilder()
    # عرض أزرار التفاصيل لأحدث 12 طلب من جميع الحالات
    for d in (pending + approved + rejected)[:12]:
        kb_builder.button(text=f"تفاصيل #{d.get('id')}", callback_data=f"view_my_dep:{d.get('id')}")

    kb_builder.adjust(1)
    kb_builder.row(types.InlineKeyboardButton(text="🔙 رجوع", callback_data="my_account"))

    await smart_edit(call, txt, kb_builder.as_markup())


@router.callback_query(F.data.startswith("view_my_dep:"))
async def view_my_deposit(call: types.CallbackQuery):
    req_id = call.data.split(":")[1]
    dep = await asyncio.to_thread(database.get_deposit_request, req_id)
    if not dep:
        return await call.answer("❌ الطلب غير موجود.", show_alert=True)

    txt = (
        f"💳 <b>تفاصيل الإيداع #{dep.get('id')}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"👤 المستخدم: <code>{dep.get('user_id')}</code>\n"
        f"💳 الطريقة: <b>{dep.get('method')}</b>\n"
        f"💰 المبلغ: <b>{dep.get('amount')}</b>\n"
        f"🧾 رقم العملية: <code>{dep.get('txn_id')}</code>\n"
        f"📅 التاريخ: {dep.get('date')}\n"
        f"📌 الحالة: <b>{dep.get('status')}</b>\n"
    )
    admin_note = dep.get('admin_note')
    if admin_note:
        txt += f"📝 <b>ملاحظة الإدارة:</b>\n<code>{admin_note}</code>\n"

    txt += f"━━━━━━━━━━━━\n"
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="📞 تواصل مع الدعم بخصوص هذا الطلب", callback_data=f"support_deposit:{req_id}")
    kb_builder.button(text="🔙 رجوع", callback_data="my_deposits")
    kb_builder.adjust(1)
    await smart_edit(call, txt, kb_builder.as_markup())


@router.callback_query(F.data == "deposit_menu")
async def dep_menu(call: types.CallbackQuery):
    """Show deposit menu."""
    await smart_edit(call, "💳 المحفظة والشحن:", kb.deposit_menu())


@router.callback_query(F.data == "check_my_balance")
async def chk_bal(call: types.CallbackQuery):
    """Check user balance with deposit statistics."""
    u = call.from_user.id

    # ✅ تسريع جلب البيانات
    b = await asyncio.to_thread(database.get_balance, u)
    total_deposited = await asyncio.to_thread(database.get_total_deposited, u)

    rate = settings.get_setting("exchange_rate")
    txt = _build_balance_text(b, total_deposited, rate)
    await smart_edit(call, txt, kb.back_btn("deposit_menu"))


# --- (باقي دوال القوائم dep_syriatel, dep_sham_menu... تبقى كما هي بدون تعديل) ---
@router.callback_query(F.data == "dep_syriatel")
async def start_syriatel_deposit(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(method="syriatel")
    await state.set_state(DepositState.waiting_for_amount)
    txt = "🔴 <b>إيداع سيريتيل كاش:</b>\n\n💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالليرة السورية\nمثال: <code>25000</code>"
    await smart_edit(call, txt, kb.back_btn("deposit_menu"))

@router.callback_query(F.data == "dep_sham_menu")
async def show_sham_menu(call: types.CallbackQuery):
    await smart_edit(call, "🟣 <b>اختر نوع رصيد شام كاش:</b>", kb.sham_deposit_types())

@router.callback_query(F.data == "dep_sham_syp")
async def start_sham_syp(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(method="sham_syp")
    await state.set_state(DepositState.waiting_for_amount)
    txt = "🟣 <b>إيداع شام كاش (ليرة سوري):</b>\n\n💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالليرة السورية\nمثال: <code>25000</code>"
    await smart_edit(call, txt, kb.back_btn("dep_sham_menu"))

@router.callback_query(F.data == "dep_sham_usd")
async def start_sham_usd(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(method="sham_usd")
    await state.set_state(DepositState.waiting_for_amount)
    rate = settings.get_setting("exchange_rate")
    txt = f"🟣 <b>إيداع شام كاش (دولار $):</b>\n\n💵 <b>سعر الصرف:</b> {rate} ل.س\n━━━━━━━━━━━━\n💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالدولار\nمثال: <code>10</code>"
    await smart_edit(call, txt, kb.back_btn("dep_sham_menu"))

@router.callback_query(F.data == "dep_usdt_menu")
async def show_usdt_menu(call: types.CallbackQuery):
    await smart_edit(call, "🟢 <b>اختر طريقة تحويل USDT:</b>", kb.usdt_deposit_types())

@router.callback_query(F.data == "dep_usdt_bep20")
async def start_usdt_bep20(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(method="usdt_bep20")
    await state.set_state(DepositState.waiting_for_amount)
    txt = "🔸 <b>إيداع USDT (شبكة BEP20):</b>\n\n💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالدولار\nمثال: <code>10</code>"
    await smart_edit(call, txt, kb.back_btn("dep_usdt_menu"))

@router.callback_query(F.data == "dep_usdt_coinex")
async def start_usdt_coinex(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(method="usdt_coinex")
    await state.set_state(DepositState.waiting_for_amount)
    txt = "📧 <b>إيداع USDT (CoinEx Email):</b>\n\n💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالدولار\nمثال: <code>10</code>"
    await smart_edit(call, txt, kb.back_btn("dep_usdt_menu"))


@router.message(DepositState.waiting_for_amount)
async def process_dep_amount(msg: types.Message, state: FSMContext):
    """Process deposit amount - Step 2."""
    if not msg.text:
        return await msg.answer("❌ يرجى إرسال المبلغ كرقم فقط.")

    try:
        amount = float(msg.text)
        if amount <= 0: raise ValueError
    except:
        return await msg.answer("❌ أرقام فقط (مثال: 10 أو 25000).")

    data = await state.get_data()
    method = data.get('method', 'syriatel')

    # Calculate balance
    commission = settings.get_deposit_commission()
    rate = settings.get_setting("exchange_rate")
    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]

    if method in usd_methods:
        deposit_usd = amount
        deposit_syp = int(amount * rate)
        commission_amount = deposit_usd * (commission / 100)
        final_usd = deposit_usd - commission_amount
        final_syp = int(final_usd * rate)
        currency_symbol = "$"
    else:
        deposit_syp = int(amount)
        deposit_usd = amount / rate
        commission_amount = deposit_usd * (commission / 100)
        final_usd = deposit_usd - commission_amount
        final_syp = int(round(final_usd * rate))
        currency_symbol = "ل.س"

    # --- الجزء الجديد: حساب الرصيد المتوقع ---
    current_bal = await asyncio.to_thread(database.get_balance, msg.from_user.id)
    after_bal_usd = current_bal + final_usd
    after_bal_syp = int(round(after_bal_usd * rate))
    # ---------------------------------------

    await state.update_data(amount=amount, deposit_usd=deposit_usd, deposit_syp=deposit_syp,
                           final_usd=final_usd, final_syp=final_syp)

    # Prepare payment info (Same logic as before, just shortened for brevity in this fix)
    method_name = "سيريتيل كاش"
    payment_info = ""
    if method == "syriatel":
        nums = ["50380953", "24587779", "17809925", "13822706", "99729846", "32371251"]
        payment_info = "يرجى التحويل إلى أحد الأرقام التالية:\n" + "\n".join([f"☎️ <code>{n}</code>" for n in nums])
    elif method == "sham_syp":
        payment_info = f"🆔 <b>المعرف:</b> <code>eb8956237bde3f68654b53f62fe23c01</code>"
    elif method == "sham_usd":
        payment_info = f"🆔 <b>المعرف:</b> <code>eb8956237bde3f68654b53f62fe23c01</code>"
    elif method == "usdt_bep20":
        payment_info = f"🔗 <b>العنوان:</b> <code>0x41bd56631361e110bdb6a1acbf41d7e7eb581f5e</code>"
    elif method == "usdt_coinex":
        payment_info = f"📧 <b>Email:</b> <code>hussinhamdan028@gmail.com</code>"

    response_txt = (
        f"💳 <b>طريقة الإيداع:</b> {method} (تم الاختيار)\n" # simplified name logic
        f"━━━━━━━━━━━━\n"
        f"💰 <b>المبلغ المرسل:</b> {amount} {currency_symbol}\n"
        f"💵 <b>الرصيد المضاف:</b> {final_usd:.2f} $\n"
        f"💷 <b>المعادل بالسوري:</b> {final_syp:,} ل.س\n"
        f"━━━━━━━━━━━━\n"
        f"📈 <b>رصيدك بعد قبول الإيداع سيصبح:</b>\n"
        f"🇺🇸 <b>{after_bal_usd:.2f} $</b>\n"
        f"🇸🇾 <b>{after_bal_syp:,} ل.س</b>\n"
        f"━━━━━━━━━━━━\n"
        f"{payment_info}\n"
        f"━━━━━━━━━━━━\n"
        f"📝 <b>الخطوة 2:</b> أرسل رقم عملية التحويل\n"
    )
    await msg.answer(response_txt, parse_mode="HTML", reply_markup=kb.back_btn("deposit_menu"))
    await state.set_state(DepositState.waiting_for_txn_id)


@router.message(DepositState.waiting_for_txn_id)
async def process_txn_id(msg: types.Message, state: FSMContext):
    """Step 3: Save txn id."""
    if not msg.text:
        return await msg.answer("❌ يرجى إرسال رقم العملية كرقم فقط.")
    txn_id = msg.text.strip()
    if not txn_id.isdigit() or len(txn_id) < 5:
        return await msg.answer("❌ رقم العملية غير صحيح.")

    await state.update_data(txn_id=txn_id)
    await msg.answer("✅ <b>تم حفظ الرقم.</b>\n📸 <b>الخطوة 3:</b> أرسل صورة الإثبات.", parse_mode="HTML", reply_markup=kb.back_btn("deposit_menu"))
    await state.set_state(DepositState.waiting_for_proof)


# ✅✅✅ هنا الحل الجذري لمشكلة التعليق ✅✅✅
@router.message(DepositState.waiting_for_proof)
async def process_proof_image(msg: types.Message, state: FSMContext):
    """Process proof image - Step 4: Save deposit request ASYNC."""
    data = await state.get_data()
    txn_id = data.get('txn_id')
    amount = data.get('amount')
    method = data.get('method', 'syriatel')
    uid = msg.from_user.id

    proof_image_id = None
    if msg.photo:
        proof_image_id = msg.photo[-1].file_id
    elif msg.document:
        proof_image_id = msg.document.file_id

    # 🔥🔥 التغيير الجوهري: استخدام await asyncio.to_thread 🔥🔥
    # هذا يمنع البوت من التجمد أثناء الكتابة في قاعدة البيانات
    req = await asyncio.to_thread(
        database.save_deposit_request,
        uid, method, txn_id, amount, proof_image_id
    )

    final_usd = data.get('final_usd', 0)
    final_syp = data.get('final_syp', 0)

    await msg.answer(
        f"✅ <b>تم استلام الطلب رقم #{req['id']}!</b>\nسيتم مراجعته قريباً.",
        reply_markup=kb.main_menu(),
        parse_mode="HTML"
    )
    await state.clear()

    # إعداد رسالة الأدمن
    admin_txt = (
        f"🔔 <b>إيداع جديد ({method})</b>\n"
        f"👤 من: <code>{uid}</code>\n"
        f"💰 المبلغ: <b>{amount}</b>\n"
        f"💵 الرصيد المضاف: <b>{final_usd:.2f} $</b>\n"
        f"🔢 العملية: <code>{txn_id}</code>"
    )

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ قبول", callback_data=f"approve_dep:{req['id']}")],
        [types.InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_dep:{req['id']}")],
        [types.InlineKeyboardButton(text="📋 الكل", callback_data="admin_pending_all")]
    ])

    # 🔥🔥 تسريع إشعار الأدمن أيضاً 🔥🔥
    admin_ids = await asyncio.to_thread(database.get_all_admin_ids)

    for aid in admin_ids:
        try:
            if proof_image_id:
                try:
                    await msg.bot.send_photo(aid, proof_image_id, caption=admin_txt, reply_markup=markup, parse_mode="HTML")
                except:
                    await msg.bot.send_document(aid, proof_image_id, caption=admin_txt, reply_markup=markup, parse_mode="HTML")
            else:
                await msg.bot.send_message(aid, admin_txt, reply_markup=markup, parse_mode="HTML")
        except:
            pass


@router.message(F.text == "/skip")
async def skip_proof_image(msg: types.Message, state: FSMContext):
    if await state.get_state() != DepositState.waiting_for_proof: return

    data = await state.get_data()
    txn_id = data.get('txn_id')
    amount = data.get('amount')
    method = data.get('method', 'syriatel')
    uid = msg.from_user.id

    # 🔥🔥 التغيير الجوهري هنا أيضاً 🔥🔥
    req = await asyncio.to_thread(
        database.save_deposit_request,
        uid, method, txn_id, amount, None
    )

    final_usd = data.get('final_usd', 0)
    await msg.answer(
        f"✅ <b>تم استلام الطلب رقم #{req['id']}!</b>\nسيتم مراجعته قريباً.",
        reply_markup=kb.main_menu(),
        parse_mode="HTML"
    )
    await state.clear()

    # إشعار الأدمن (نفس المنطق)
    admin_ids = await asyncio.to_thread(database.get_all_admin_ids)
    admin_txt = f"🔔 إيداع جديد ({method}) - {amount} - {txn_id}"
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ قبول", callback_data=f"approve_dep:{req['id']}")],
        [types.InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_dep:{req['id']}")]
    ])

    for aid in admin_ids:
        try:
            await msg.bot.send_message(aid, admin_txt, reply_markup=markup, parse_mode="HTML")
        except: pass
