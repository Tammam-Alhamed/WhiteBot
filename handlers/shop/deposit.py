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
    """Check user balance."""
    u = call.from_user.id
    b = database.get_balance(u)
    await smart_edit(call, f"💰 <b>محفظتك:</b>\n💵 {b} $\n💷 {format_price(b)}", kb.back_btn("deposit_menu"))


@router.callback_query(F.data == "dep_syriatel")
async def start_syriatel_deposit(call: types.CallbackQuery, state: FSMContext):
    """Start Syriatel deposit flow."""
    await state.update_data(method="syriatel")
    await state.set_state(DepositState.waiting_for_txn_id)

    nums = ["50380953", "24587779", "17809925", "13822706", "99729846", "32371251"]

    txt = "🔴 <b>إيداع سيريتيل كاش :</b>\n\nيرجى التحويل إلى أحد الأرقام التالية:\n"
    for n in nums:
        txt += f"☎️ <code>{n}</code>\n"

    txt += (
        "\n⚠️ <b>تعليمات هامة:</b>\n"
        "1. أرسال سيرياتل كاش (تحويل يدوي حصرا).\n"
        "2. انتظر دقيقتين بعد التحويل لضمان وصول الرسالة.\n"
        "3. ثم أكتب رقم عملية التحويل في الأسفل. 👇. مثال لرقم التحويل :\n"
        "<code>600044062208</code>"
    )

    await smart_edit(call, txt, kb.back_btn("deposit_menu"))


@router.callback_query(F.data == "dep_sham_menu")
async def show_sham_menu(call: types.CallbackQuery):
    """Show Sham Cash menu."""
    await smart_edit(call, "🟣 <b>اختر نوع رصيد شام كاش:</b>", kb.sham_deposit_types())


@router.callback_query(F.data == "dep_sham_syp")
async def start_sham_syp(call: types.CallbackQuery, state: FSMContext):
    """Start Sham Cash SYP deposit."""
    await state.update_data(method="sham_syp")
    await state.set_state(DepositState.waiting_for_txn_id)

    wallet = "eb8956237bde3f68654b53f62fe23c01"

    txt = (
        "🟣 <b>إيداع شام كاش (ليرة سوري):</b>\n\n"
        "يرجى التحويل إلى المعرف التالي:\n"
        f"🆔 <code>{wallet}</code>\n\n"
        "⚠️ <b>تعليمات هامة:</b>\n"
        "1. حول المبلغ بالليرة السورية حصراً.\n"
        "2. انتظر دقيقتين بعد التحويل.\n"
        "3. ثم أرسل رقم عملية التحويل في الأسفل. 👇\n"
        "مثال لرقم التحويل <code>77242526</code>"
    )
    await smart_edit(call, txt, kb.back_btn("dep_sham_menu"))


@router.callback_query(F.data == "dep_sham_usd")
async def start_sham_usd(call: types.CallbackQuery, state: FSMContext):
    """Start Sham Cash USD deposit."""
    await state.update_data(method="sham_usd")
    await state.set_state(DepositState.waiting_for_txn_id)

    wallet = "eb8956237bde3f68654b53f62fe23c01"
    rate = settings.get_setting("exchange_rate")

    txt = (
        "🟣 <b>إيداع شام كاش (دولار $):</b>\n\n"
        f"💵 <b>سعر الصرف المعتمد:</b> {rate} ل.س\n"
        "━━━━━━━━━━━━\n"
        "يرجى التحويل إلى المعرف التالي:\n"
        f"🆔 <code>{wallet}</code>\n\n"
        "⚠️ <b>تعليمات هامة:</b>\n"
        "1. حول المبلغ بالدولار حصراً.\n"
        "2. انتظر دقيقتين بعد التحويل.\n"
        "3. ثم أرسل رقم عملية التحويل في الأسفل. 👇\n"
        "مثال لرقم التحويل <code>77242526</code>"
    )
    await smart_edit(call, txt, kb.back_btn("dep_sham_menu"))


@router.callback_query(F.data == "dep_usdt_menu")
async def show_usdt_menu(call: types.CallbackQuery):
    """Show USDT deposit menu."""
    await smart_edit(call, "🟢 <b>اختر طريقة تحويل USDT:</b>", kb.usdt_deposit_types())


@router.callback_query(F.data == "dep_usdt_bep20")
async def start_usdt_bep20(call: types.CallbackQuery, state: FSMContext):
    """Start USDT BEP20 deposit."""
    await state.update_data(method="usdt_bep20")
    await state.set_state(DepositState.waiting_for_txn_id)

    addr = "0x41bd56631361e110bdb6a1acbf41d7e7eb581f5e"

    txt = (
        "🔸 <b>إيداع USDT (شبكة BEP20):</b>\n\n"
        "يرجى التحويل إلى عنوان المحفظة التالي:\n"
        f"<code>{addr}</code>\n\n"
        "⚠️ <b>تعليمات هامة:</b>\n"
        "1. تأكد من اختيار شبكة <b>BSC (BEP20)</b> حصراً.\n"
        "2. انسخ العنوان بالضغط عليه.\n"
        "3. بعد التحويل، أرسل <b>رقم العملية (TXID)</b> في الأسفل. 👇"
    )
    await smart_edit(call, txt, kb.back_btn("dep_usdt_menu"))


@router.callback_query(F.data == "dep_usdt_coinex")
async def start_usdt_coinex(call: types.CallbackQuery, state: FSMContext):
    """Start USDT CoinEx deposit."""
    await state.update_data(method="usdt_coinex")
    await state.set_state(DepositState.waiting_for_txn_id)

    email = "hussinhamdan028@gmail.com"

    txt = (
        "CoinEx (Email) لا توجد رسوم\n\n"
        f"Email: <code>{email}</code>\n\n"
        "Only send USDT **\n"
        "** فقط نقبل عملة USDT **\n\n"
        "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
        "بعد التحويل، الرجاء إرسال <b>رقم العملية (Transaction ID)</b> في الأسفل للتحقق 👇"
    )

    await smart_edit(call, txt, kb.back_btn("dep_usdt_menu"))


@router.message(DepositState.waiting_for_txn_id)
async def process_txn_id(msg: types.Message, state: FSMContext):
    """Process transaction ID."""
    txn_id = msg.text
    if len(txn_id) < 5:
        return await msg.answer("❌ رقم العملية قصير جداً، تأكد وأعد المحاولة:")

    await state.update_data(txn_id=txn_id)

    data = await state.get_data()
    method = data.get('method', 'syriatel')

    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]

    if method in usd_methods:
        currency_txt = "الدولار ($)"
        example_txt = "10"
    else:
        currency_txt = "الليرة السورية"
        example_txt = "25000"

    await msg.answer(
        f"✅ تم حفظ رقم العملية.\n\n"
        f"💰 <b>الآن، أرسل المبلغ الذي حولته (بـ {currency_txt}):</b>\n"
        f"مثال: <code>{example_txt}</code>",
        parse_mode="HTML"
    )

    await state.set_state(DepositState.waiting_for_amount)


@router.message(DepositState.waiting_for_amount)
async def process_dep_amount(msg: types.Message, state: FSMContext):
    """Process deposit amount."""
    try:
        amount = float(msg.text)
        if amount <= 0:
            raise ValueError
    except:
        return await msg.answer("❌ أرقام فقط (مثال: 10 أو 25000).")

    data = await state.get_data()
    txn_id = data['txn_id']
    method = data.get('method', 'syriatel')
    uid = msg.from_user.id

    method_name = "سيريتيل كاش"
    if method == "sham_syp":
        method_name = "شام كاش (سوري)"
    elif method == "sham_usd":
        method_name = "شام كاش (دولار)"
    elif method == "usdt_bep20":
        method_name = "USDT (BEP20)"
    elif method == "usdt_coinex":
        method_name = "CoinEx (Email)"

    req = database.save_deposit_request(uid, method, txn_id, amount)

    await msg.answer(
        f"✅ <b>تم استلام الطلب!</b>\n"
        f"رقم المتابعة: <code>{req['id']}</code>\n"
        f"💳 الطريقة: {method_name}\n"
        f"سيصلك إشعار فور التحقق من العملية.",
        reply_markup=kb.main_menu(),
        parse_mode="HTML"
    )
    await state.clear()

    usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
    curr_symbol = "$" if method in usd_methods else "ل.س"

    admin_txt = (
        f"🔔 <b>إيداع جديد ({method_name})</b>\n"
        f"👤 من: <code>{uid}</code>\n"
        f"💰 المبلغ: <b>{amount} {curr_symbol}</b>\n"
        f"🔢 العملية: <code>{txn_id}</code>"
    )

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ قبول", callback_data=f"approve_dep:{req['id']}")],
        [types.InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_dep:{req['id']}")]
    ])

    for aid in config.ADMIN_IDS:
        try:
            await msg.bot.send_message(aid, admin_txt, reply_markup=markup, parse_mode="HTML")
        except:
            pass
