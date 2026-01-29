"""Deposit and Account handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import asyncio  # ✅ 1. إضافة مكتبة asyncio
import config
import services.database as database
import services.settings as settings
import data.keyboards as kb
from bot.utils.helpers import smart_edit, format_price
from states.shop import DepositState

router = Router()

# ✅ دالة زر "حسابي" الجديد
@router.callback_query(F.data == "my_account")
async def show_my_account(call: types.CallbackQuery):
    """Show user account details (ID, Total Deposited, Orders Count)."""
    user_id = call.from_user.id

    # ✅ استخدام to_thread لتسريع الاستجابة
    total_deposited = await asyncio.to_thread(database.get_total_deposited, user_id)
    orders = await asyncio.to_thread(database.get_user_local_orders, user_id)

    completed_orders = [o for o in orders if o['status'] == 'completed']
    orders_count = len(completed_orders)

    txt = (
        f"👤 <b>حسابي الشخصي</b>\n"
        f"━━━━━━━━━━━━\n"
        f"🆔 <b>الآيدي الخاص بك:</b>\n"
        f"<code>{user_id}</code>\n"
        f"(شارك هذا الرقم مع الإدارة عند الطلب)\n\n"
        f"📊 <b>إحصائياتك:</b>\n"
        f"💰 إجمالي الإيداعات: <b>{total_deposited:.2f} $</b>\n"
        f"📦 الطلبات المكتملة: <b>{orders_count}</b> طلب\n"
        f"━━━━━━━━━━━━"
    )

    await smart_edit(call, txt, kb.back_btn("home"))


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