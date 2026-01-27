"""Deposit handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import config
import services.database as database
import services.settings as settings
import data.keyboards as kb
from bot.utils.helpers import smart_edit, format_price
from states.shop import DepositState

router = Router()


@router.callback_query(F.data == "deposit_menu")
async def dep_menu(call: types.CallbackQuery):
    """Show deposit menu."""
    await smart_edit(call, "💳 المحفظة والشحن:", kb.deposit_menu())


@router.callback_query(F.data == "check_my_balance")
async def chk_bal(call: types.CallbackQuery):
    """Check user balance with deposit statistics."""
    u = call.from_user.id
    b = database.get_balance(u)
    total_deposited = database.get_total_deposited(u)
    rate = settings.get_setting("exchange_rate")
    b_syp = int(round(b * rate))
    total_dep_syp = int(round(total_deposited * rate))
    
    txt = (
        f"💰 <b>محفظتك:</b>\n"
        f"💵 {b:.2f} $\n"
        f"💷 {b_syp:,} ل.س\n"
        f"━━━━━━━━━━━━\n"
        f"📊 <b>إجمالي الإيداعات:</b>\n"
        f"💵 {total_deposited:.2f} $\n"
        f"💷 {total_dep_syp:,} ل.س"
    )
    await smart_edit(call, txt, kb.back_btn("deposit_menu"))


@router.callback_query(F.data == "dep_syriatel")
async def start_syriatel_deposit(call: types.CallbackQuery, state: FSMContext):
    """Start Syriatel deposit flow - Step 1: Ask for amount."""
    await state.update_data(method="syriatel")
    await state.set_state(DepositState.waiting_for_amount)
    
    txt = (
        "🔴 <b>إيداع سيريتيل كاش:</b>\n\n"
        "💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالليرة السورية\n"
        "مثال: <code>25000</code>"
    )
    await smart_edit(call, txt, kb.back_btn("deposit_menu"))


@router.callback_query(F.data == "dep_sham_menu")
async def show_sham_menu(call: types.CallbackQuery):
    """Show Sham Cash menu."""
    await smart_edit(call, "🟣 <b>اختر نوع رصيد شام كاش:</b>", kb.sham_deposit_types())


@router.callback_query(F.data == "dep_sham_syp")
async def start_sham_syp(call: types.CallbackQuery, state: FSMContext):
    """Start Sham Cash SYP deposit - Step 1: Ask for amount."""
    await state.update_data(method="sham_syp")
    await state.set_state(DepositState.waiting_for_amount)
    
    txt = (
        "🟣 <b>إيداع شام كاش (ليرة سوري):</b>\n\n"
        "💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالليرة السورية\n"
        "مثال: <code>25000</code>"
    )
    await smart_edit(call, txt, kb.back_btn("dep_sham_menu"))


@router.callback_query(F.data == "dep_sham_usd")
async def start_sham_usd(call: types.CallbackQuery, state: FSMContext):
    """Start Sham Cash USD deposit - Step 1: Ask for amount."""
    await state.update_data(method="sham_usd")
    await state.set_state(DepositState.waiting_for_amount)
    
    rate = settings.get_setting("exchange_rate")
    txt = (
        "🟣 <b>إيداع شام كاش (دولار $):</b>\n\n"
        f"💵 <b>سعر الصرف:</b> {rate} ل.س\n"
        "━━━━━━━━━━━━\n"
        "💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالدولار\n"
        "مثال: <code>10</code>"
    )
    await smart_edit(call, txt, kb.back_btn("dep_sham_menu"))


@router.callback_query(F.data == "dep_usdt_menu")
async def show_usdt_menu(call: types.CallbackQuery):
    """Show USDT deposit menu."""
    await smart_edit(call, "🟢 <b>اختر طريقة تحويل USDT:</b>", kb.usdt_deposit_types())


@router.callback_query(F.data == "dep_usdt_bep20")
async def start_usdt_bep20(call: types.CallbackQuery, state: FSMContext):
    """Start USDT BEP20 deposit - Step 1: Ask for amount."""
    await state.update_data(method="usdt_bep20")
    await state.set_state(DepositState.waiting_for_amount)
    
    txt = (
        "🔸 <b>إيداع USDT (شبكة BEP20):</b>\n\n"
        "💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالدولار\n"
        "مثال: <code>10</code>"
    )
    await smart_edit(call, txt, kb.back_btn("dep_usdt_menu"))


@router.callback_query(F.data == "dep_usdt_coinex")
async def start_usdt_coinex(call: types.CallbackQuery, state: FSMContext):
    """Start USDT CoinEx deposit - Step 1: Ask for amount."""
    await state.update_data(method="usdt_coinex")
    await state.set_state(DepositState.waiting_for_amount)
    
    txt = (
        "📧 <b>إيداع USDT (CoinEx Email):</b>\n\n"
        "💰 <b>الخطوة 1:</b> أرسل المبلغ الذي تريد إيداعه بالدولار\n"
        "مثال: <code>10</code>"
    )
    await smart_edit(call, txt, kb.back_btn("dep_usdt_menu"))


@router.message(DepositState.waiting_for_amount)
async def process_dep_amount(msg: types.Message, state: FSMContext):
    """Process deposit amount - Step 2: Show payment info and ask for transaction number."""
    # Validate amount input
    if not msg.text:
        return await msg.answer("❌ يرجى إرسال المبلغ كرقم فقط.")
    
    try:
        amount = float(msg.text)
        if amount <= 0:
            raise ValueError
    except:
        return await msg.answer("❌ أرقام فقط (مثال: 10 أو 25000).")

    data = await state.get_data()
    method = data.get('method', 'syriatel')
    uid = msg.from_user.id
    
    # Calculate balance to be added (after commission)
    commission = settings.get_deposit_commission()
    rate = settings.get_setting("exchange_rate")
    
    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
    
    if method in usd_methods:
        # USD deposit
        deposit_usd = amount
        deposit_syp = int(amount * rate)
        commission_amount = deposit_usd * (commission / 100)
        final_usd = deposit_usd - commission_amount
        final_syp = int(final_usd * rate)
        currency_symbol = "$"
        currency_name = "دولار"
    else:
        # SYP deposit
        deposit_syp = int(amount)
        deposit_usd = amount / rate
        commission_amount = deposit_usd * (commission / 100)
        final_usd = deposit_usd - commission_amount
        final_syp = int(round(final_usd * rate))
        currency_symbol = "ل.س"
        currency_name = "ليرة سورية"
    
    # Store amount in state
    await state.update_data(amount=amount, deposit_usd=deposit_usd, deposit_syp=deposit_syp, 
                           final_usd=final_usd, final_syp=final_syp)
    
    # Prepare payment info based on method
    method_name = "سيريتيل كاش"
    payment_info = ""
    
    if method == "syriatel":
        method_name = "سيريتيل كاش"
        nums = ["50380953", "24587779", "17809925", "13822706", "99729846", "32371251"]
        payment_info = "يرجى التحويل إلى أحد الأرقام التالية:\n"
        for n in nums:
            payment_info += f"☎️ <code>{n}</code>\n"
        payment_info += "\n⚠️ <b>تعليمات:</b>\n"
        payment_info += "• أرسال سيرياتل كاش (تحويل يدوي حصرا)\n"
        payment_info += "• انتظر دقيقتين بعد التحويل\n"
        
    elif method == "sham_syp":
        method_name = "شام كاش (سوري)"
        wallet = "eb8956237bde3f68654b53f62fe23c01"
        payment_info = f"🆔 <b>المعرف:</b> <code>{wallet}</code>\n\n"
        payment_info += "⚠️ <b>تعليمات:</b>\n"
        payment_info += "• حول المبلغ بالليرة السورية حصراً\n"
        payment_info += "• انتظر دقيقتين بعد التحويل\n"
        
    elif method == "sham_usd":
        method_name = "شام كاش (دولار)"
        wallet = "eb8956237bde3f68654b53f62fe23c01"
        payment_info = f"🆔 <b>المعرف:</b> <code>{wallet}</code>\n\n"
        payment_info += "⚠️ <b>تعليمات:</b>\n"
        payment_info += "• حول المبلغ بالدولار حصراً\n"
        payment_info += "• انتظر دقيقتين بعد التحويل\n"
        
    elif method == "usdt_bep20":
        method_name = "USDT (BEP20)"
        addr = "0x41bd56631361e110bdb6a1acbf41d7e7eb581f5e"
        payment_info = f"🔗 <b>العنوان:</b> <code>{addr}</code>\n\n"
        payment_info += "⚠️ <b>تعليمات:</b>\n"
        payment_info += "• تأكد من اختيار شبكة <b>BSC (BEP20)</b> حصراً\n"
        payment_info += "• انسخ العنوان بالضغط عليه\n"
        
    elif method == "usdt_coinex":
        method_name = "CoinEx (Email)"
        email = "hussinhamdan028@gmail.com"
        payment_info = f"📧 <b>Email:</b> <code>{email}</code>\n\n"
        payment_info += "⚠️ <b>تعليمات:</b>\n"
        payment_info += "• فقط نقبل عملة USDT\n"
    
    # Build response message
    response_txt = (
        f"💳 <b>طريقة الإيداع:</b> {method_name}\n"
        f"━━━━━━━━━━━━\n"
        f"💰 <b>المبلغ المرسل:</b> {amount} {currency_symbol}\n"
        f"💵 <b>الرصيد المضاف (بعد العمولة):</b>\n"
        f"🇺🇸 {final_usd:.2f} $\n"
        f"🇸🇾 {final_syp:,} ل.س\n"
    )
    
    if commission > 0:
        response_txt += f"📊 <b>العمولة ({commission}%):</b> {commission_amount:.2f} $\n"
    
    response_txt += (
        f"━━━━━━━━━━━━\n"
        f"{payment_info}"
        f"━━━━━━━━━━━━\n"
        f"📝 <b>الخطوة 2:</b> أرسل رقم عملية التحويل\n"
        f"مثال: <code>600044062208</code>"
    )
    
    await msg.answer(response_txt, parse_mode="HTML", reply_markup=kb.back_btn("deposit_menu"))
    await state.set_state(DepositState.waiting_for_txn_id)


@router.message(DepositState.waiting_for_txn_id)
async def process_txn_id(msg: types.Message, state: FSMContext):
    """Process transaction ID - Step 3: Ask for proof image."""
    # Validate transaction ID
    if not msg.text:
        return await msg.answer("❌ يرجى إرسال رقم العملية كرقم فقط.")
    
    txn_id = msg.text.strip()
    
    # Validate transaction ID format (numeric, minimum length)
    if not txn_id.isdigit():
        return await msg.answer("❌ رقم العملية يجب أن يحتوي على أرقام فقط.")
    
    if len(txn_id) < 5:
        return await msg.answer("❌ رقم العملية قصير جداً، يجب أن يكون 5 أرقام على الأقل.")
    
    await state.update_data(txn_id=txn_id)
    
    txt = (
        "✅ <b>تم حفظ رقم العملية.</b>\n\n"
        "📸 <b>الخطوة 3 :</b> أرسل صورة إثبات التحويل\n"

    )
    
    await msg.answer(txt, parse_mode="HTML", reply_markup=kb.back_btn("deposit_menu"))
    await state.set_state(DepositState.waiting_for_proof)


@router.message(DepositState.waiting_for_proof)
async def process_proof_image(msg: types.Message, state: FSMContext):
    """Process proof image - Step 4: Save deposit request."""
    data = await state.get_data()
    txn_id = data.get('txn_id')
    amount = data.get('amount')
    method = data.get('method', 'syriatel')
    uid = msg.from_user.id
    
    # Get proof image if sent
    proof_image_id = None
    if msg.photo:
        proof_image_id = msg.photo[-1].file_id
    elif msg.document:
        proof_image_id = msg.document.file_id
    
    # Save deposit request
    req = database.save_deposit_request(uid, method, txn_id, amount, proof_image_id)
    
    method_name = "سيريتيل كاش"
    if method == "sham_syp":
        method_name = "شام كاش (سوري)"
    elif method == "sham_usd":
        method_name = "شام كاش (دولار)"
    elif method == "usdt_bep20":
        method_name = "USDT (BEP20)"
    elif method == "usdt_coinex":
        method_name = "CoinEx (Email)"
    
    final_usd = data.get('final_usd', 0)
    final_syp = data.get('final_syp', 0)
    
    await msg.answer(
        f"✅ <b>تم استلام الطلب!</b>\n"
        f"━━━━━━━━━━━━\n"
        f"🔢 رقم المتابعة: <code>{req['id']}</code>\n"
        f"💳 الطريقة: {method_name}\n"
        f"💰 الرصيد المضاف:\n"
        f"🇺🇸 {final_usd:.2f} $\n"
        f"🇸🇾 {final_syp:,} ل.س\n"
        f"━━━━━━━━━━━━\n"
        f"سيصلك إشعار فور التحقق من العملية.",
        reply_markup=kb.main_menu(),
        parse_mode="HTML"
    )
    await state.clear()
    
    # Notify admins
    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
    curr_symbol = "$" if method in usd_methods else "ل.س"
    
    admin_txt = (
        f"🔔 <b>إيداع جديد ({method_name})</b>\n"
        f"━━━━━━━━━━━━\n"
        f"👤 من: <code>{uid}</code>\n"
        f"💰 المبلغ: <b>{amount} {curr_symbol}</b>\n"
        f"💵 الرصيد المضاف: <b>{final_usd:.2f} $</b>\n"
        f"🔢 العملية: <code>{txn_id}</code>"
    )
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ قبول", callback_data=f"approve_dep:{req['id']}")],
        [types.InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_dep:{req['id']}")],
        [types.InlineKeyboardButton(text="📋 جميع الطلبات المعلقة", callback_data="admin_pending_all")]
    ])
    
    for aid in config.ADMIN_IDS:
        try:
            if proof_image_id:
                # Try sending as photo first
                try:
                    await msg.bot.send_photo(aid, proof_image_id, caption=admin_txt, reply_markup=markup, parse_mode="HTML")
                except Exception:
                    # Fallback to document if photo fails (e.g. file upload)
                    try:
                        await msg.bot.send_document(aid, proof_image_id, caption=admin_txt, reply_markup=markup, parse_mode="HTML")
                    except:
                        # Fallback to text only if both fail
                        await msg.bot.send_message(aid, admin_txt, reply_markup=markup, parse_mode="HTML")
            else:
                await msg.bot.send_message(aid, admin_txt, reply_markup=markup, parse_mode="HTML")
        except:
            pass


# Handle skip command for proof image
@router.message(F.text == "/skip")
async def skip_proof_image(msg: types.Message, state: FSMContext):
    """Skip proof image step."""
    if await state.get_state() != DepositState.waiting_for_proof:
        return

    data = await state.get_data()
    txn_id = data.get('txn_id')
    amount = data.get('amount')
    method = data.get('method', 'syriatel')
    uid = msg.from_user.id

    # Save deposit request without proof
    req = database.save_deposit_request(uid, method, txn_id, amount, None)

    method_name = "سيريتيل كاش"
    if method == "sham_syp":
        method_name = "شام كاش (سوري)"
    elif method == "sham_usd":
        method_name = "شام كاش (دولار)"
    elif method == "usdt_bep20":
        method_name = "USDT (BEP20)"
    elif method == "usdt_coinex":
        method_name = "CoinEx (Email)"

    final_usd = data.get('final_usd', 0)
    final_syp = data.get('final_syp', 0)

    await msg.answer(
        f"✅ <b>تم استلام الطلب!</b>\n"
        f"━━━━━━━━━━━━\n"
        f"🔢 رقم المتابعة: <code>{req['id']}</code>\n"
        f"💳 الطريقة: {method_name}\n"
        f"💰 الرصيد المضاف:\n"
        f"🇺🇸 {final_usd:.2f} $\n"
        f"🇸🇾 {final_syp:,} ل.س\n"
        f"━━━━━━━━━━━━\n"
        f"سيصلك إشعار فور التحقق من العملية.",
        reply_markup=kb.main_menu(),
        parse_mode="HTML"
    )
    await state.clear()

    # Notify admins
    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
    curr_symbol = "$" if method in usd_methods else "ل.س"

    admin_txt = (
        f"🔔 <b>إيداع جديد ({method_name})</b>\n"
        f"━━━━━━━━━━━━\n"
        f"👤 من: <code>{uid}</code>\n"
        f"💰 المبلغ: <b>{amount} {curr_symbol}</b>\n"
        f"💵 الرصيد المضاف: <b>{final_usd:.2f} $</b>\n"
        f"🔢 العملية: <code>{txn_id}</code>"
    )

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ قبول", callback_data=f"approve_dep:{req['id']}")],
        [types.InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_dep:{req['id']}")],
        [types.InlineKeyboardButton(text="📋 جميع الطلبات المعلقة", callback_data="admin_pending_all")]
    ])

    for aid in config.ADMIN_IDS:
        try:
            await msg.bot.send_message(aid, admin_txt, reply_markup=markup, parse_mode="HTML")
        except:
            pass