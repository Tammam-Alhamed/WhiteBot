"""Product browsing and purchasing handlers."""
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
import config
import services.database as database
import services.api_manager as api_manager
import services.settings as settings
import data.mappings as mappings
import data.keyboards as kb
from bot.utils.helpers import smart_edit, format_price
from states.shop import ShopState

router = Router()

@router.callback_query(F.data.startswith("open:"))
async def products(call: types.CallbackQuery, state: FSMContext):
    """Show products in a category."""
    parts = call.data.split(":")
    pid = parts[1]
    parent_key = parts[2] if len(parts) > 2 else ""

    prods = api_manager.get_products_by_cat_id(pid)
    if not prods:
        return await call.answer("لا يوجد منتجات", show_alert=True)

    if parent_key in mappings.GAMES_MAP:
        back_callback = f"srch_g:{parent_key}"
    elif parent_key in mappings.APPS_MAP:
        back_callback = f"srch_a:{parent_key}"
    else:
        back_callback = "home"

    await state.update_data(back_path=call.data)
    for p in prods:
        p['formatted_price'] = format_price(p['price'])

    menu = kb.build_products(prods, back_callback)
    await smart_edit(call, "👇 المنتجات المتاحة:", menu)


@router.callback_query(F.data.startswith("buy:"))
async def init_buy(call: types.CallbackQuery, state: FSMContext):
    """Initialize purchase flow."""
    pid = call.data.split(":")[1]
    prod = api_manager.get_product_details(pid)
    if not prod:
        return await call.answer("خطأ: المنتج غير موجود", show_alert=True)

    data = await state.get_data()
    back_target = data.get('back_path', 'home')

    await state.update_data(real_user_id=call.from_user.id)
    await state.update_data(prod=prod, collected=[], idx=0, qty=1, params=prod.get('params', []))

    # Check if PUBG order for currency display consistency
    category_name = prod.get('category_name', '')
    is_pubg = 'PUBG' in category_name or 'ببجي' in category_name

    if is_pubg:
        syp_price = format_price(prod['price'])
        desc = prod.get('description', '')
        desc_txt = f"\n\n📝 <b>ملاحظات:</b>\n{desc}" if desc else ""
        txt = f"🛒 <b>شراء:</b> {prod['name']}\n💰 <b>السعر:</b> {syp_price}{desc_txt}"
    else:
        rate = settings.get_setting("exchange_rate")
        price_usd = prod['price']
        price_syp = int(price_usd * rate)
        desc = prod.get('description', '')
        desc_txt = f"\n\n📝 <b>ملاحظات:</b>\n{desc}" if desc else ""
        txt = (
            f"🛒 <b>شراء:</b> {prod['name']}\n"
            f"💰 <b>السعر:</b>\n"
            f"🇺🇸 {price_usd:.2f} $\n"
            f"🇸🇾 {price_syp:,} ل.س{desc_txt}"
        )

    cancel_markup = kb.cancel_or_back_btn(back_target)

    # ⚠️ التعديل الهام هنا: استخدام smart_edit بدلاً من delete+answer

    if prod.get('product_type') == "amount":
        qv = prod.get('qty_values', {})
        await state.update_data(min_q=qv.get('min', 1), max_q=qv.get('max', 100000))
        await state.set_state(ShopState.waiting_for_quantity)

        msg_text = txt + "\n\n👇 <b>أدخل الكمية المطلوبة:</b>"
        await smart_edit(call, msg_text, cancel_markup)

    elif not prod.get('params'):
        # هنا نحذف لأننا سننشيء عملية جديدة وقد لا يكون هناك رسالة لتعديلها بعد انتهاء العملية
        await call.message.delete()
        await finalize_order(call.message, state, call.bot)

    else:
        await state.set_state(ShopState.waiting_for_input)
        msg_text = f"{txt}\n\n📝 أدخل: <b>{prod['params'][0]}</b>"
        await smart_edit(call, msg_text, cancel_markup)


# باقي الدوال (process_qty, process_inp, finalize_order) تبقى كما هي دون تغيير
# ... (تكملة الملف كما هو عندك) ...
# ...
@router.message(ShopState.waiting_for_quantity)
async def process_qty(msg: types.Message, state: FSMContext):
    # ... (نفس الكود القديم) ...
    # فقط تأكد أنك نسخت باقي الملف كما هو
    if not msg.text:
        return await msg.answer("❌ يرجى إرسال الكمية كرقم.")

    data = await state.get_data()
    back_target = data.get('back_path', 'home')
    cancel_markup = kb.cancel_or_back_btn(back_target)

    try:
        qty = int(msg.text.strip())
        min_q = data.get('min_q', 1)
        max_q = data.get('max_q', 100000)

        if qty < min_q:
            return await msg.answer(
                f"❌ <b>الكمية صغيرة جداً:</b>\n"
                f"الحد الأدنى: {min_q}\n"
                f"يرجى المحاولة مرة أخرى:",
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )
        if qty > max_q:
            return await msg.answer(
                f"❌ <b>الكمية كبيرة جداً:</b>\n"
                f"الحد الأقصى: {max_q:,}\n"
                f"يرجى المحاولة مرة أخرى:",
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )

        await state.update_data(qty=qty)

        total = float(data['prod']['price']) * qty
        await msg.answer(f"✅ الكمية: {qty}\n💰 المجموع: {format_price(total)}")

        if not data['params']:
            await finalize_order(msg, state, msg.bot)
        else:
            await msg.answer(
                f"📝 أدخل: <b>{data['params'][0]}</b>",
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )
            await state.set_state(ShopState.waiting_for_input)
    except ValueError:
        await msg.answer(
            "❌ <b>خطأ في الإدخال:</b>\n"
            "يرجى إرسال رقم صحيح فقط.\n"
            "مثال: <code>100</code>",
            reply_markup=cancel_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        await msg.answer("❌ كمية غير صحيحة، حاول مجدداً:", reply_markup=cancel_markup)


@router.message(ShopState.waiting_for_input)
async def process_inp(msg: types.Message, state: FSMContext):
    if not msg.text:
        return await msg.answer("❌ يرجى إرسال النص المطلوب.")

    d = await state.get_data()
    back_target = d.get('back_path', 'home')
    cancel_markup = kb.cancel_or_back_btn(back_target)

    current_param = d['params'][d['idx']] if d['params'] else ""
    user_input = msg.text.strip()

    if 'player' in current_param.lower() or 'id' in current_param.lower():
        if not user_input.isdigit():
            return await msg.answer(
                "❌ <b>خطأ في الإدخال:</b>\n"
                f"معرف اللاعب يجب أن يكون أرقام فقط.\n"
                f"يرجى المحاولة مرة أخرى:",
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )
        if len(user_input) < 6:
            return await msg.answer(
                "❌ <b>خطأ في الإدخال:</b>\n"
                f"معرف اللاعب قصير جداً. يجب أن يكون 6 أرقام على الأقل.\n"
                f"يرجى المحاولة مرة أخرى:",
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )
    elif 'user' in current_param.lower() or 'username' in current_param.lower():
        if not user_input.startswith('@'):
            return await msg.answer(
                "❌ <b>خطأ في الإدخال:</b>\n"
                f"اسم المستخدم يجب أن يبدأ بـ @\n"
                f"مثال: <code>@username</code>\n"
                f"يرجى المحاولة مرة أخرى:",
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )

    inputs = d['collected']
    inputs.append(user_input)
    await state.update_data(collected=inputs)

    idx = d['idx'] + 1
    if idx < len(d['params']):
        await state.update_data(idx=idx)
        await msg.answer(
            f"✅ تم حفظ: <code>{user_input}</code>\n\n"
            f"📝 أدخل: <b>{d['params'][idx]}</b>",
            reply_markup=cancel_markup,
            parse_mode="HTML"
        )
    else:
        await finalize_order(msg, state, msg.bot)


async def finalize_order(msg: types.Message, state: FSMContext, bot: Bot):
    d = await state.get_data()
    uid = d.get('real_user_id', msg.from_user.id)
    if uid == bot.id:
        uid = msg.chat.id

    prod, qty = d['prod'], d['qty']
    total = float(prod['price']) * qty
    rate = settings.get_setting("exchange_rate")
    total_syp = int(total * rate)

    old_bal = database.get_balance(uid)
    old_bal_syp = int(old_bal * rate)

    if not database.deduct_balance(uid, total):
        await msg.answer(
            f"{config.MSG_NO_BALANCE}\n💰 التكلفة: {format_price(total)}",
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )
        await state.clear()
        return

    new_bal = database.get_balance(uid)
    new_bal_syp = int(new_bal * rate)

    await msg.answer("⏳ جاري إرسال الطلب للمزود...")
    ok, res, uuid, code = await api_manager.execute_order_dynamic(
        prod['id'], qty, d['collected'], d['params']
    )

    if ok:
        if uuid:
            api_manager.save_uuid_locally(uid, uuid)
        txt = (
            f"✅ <b>تم استلام طلبك بنجاح!</b>\n"
            f"━━━━━━━━━━━━\n"
            f"🔢 رقم العملية: <code>{res}</code>\n"
            f"━━━━━━━━━━━━\n"
            f"💰 <b>المبلغ المخصوم:</b>\n"
            f"🇺🇸 {total:.2f} $\n"
            f"🇸🇾 {total_syp:,} ل.س\n"
            f"━━━━━━━━━━━━\n"
            f"💎 <b>رصيدك المتبقي:</b>\n"
            f"🇺🇸 {new_bal:.2f} $\n"
            f"🇸🇾 {new_bal_syp:,} ل.س\n"
            f"━━━━━━━━━━━━\n"
            f"🕵️‍♂️ <b>ملاحظة:</b> يمكنك متابعة حالة التنفيذ من قسم <b>📦 طلباتي</b>."
        )
        await msg.answer(txt, parse_mode="HTML")

    elif code == 100:
        lid = database.save_pending_order(uid, prod, qty, d['collected'], d['params'])
        txt = (
            f"⏳ <b>الطلب قيد المعالجة (Processing)</b>\n"
            f"━━━━━━━━━━━━\n"
            f"🔢 رقم المتابعة: <code>{lid}</code>\n"
            f"━━━━━━━━━━━━\n"
            f"💰 <b>المبلغ المخصوم:</b>\n"
            f"🇺🇸 {total:.2f} $\n"
            f"🇸🇾 {total_syp:,} ل.س\n"
            f"━━━━━━━━━━━━\n"
            f"💎 <b>رصيدك المتبقي:</b>\n"
            f"🇺🇸 {new_bal:.2f} $\n"
            f"🇸🇾 {new_bal_syp:,} ل.س\n"
            f"━━━━━━━━━━━━\n"
            f"سيتم إشعارك عند الاكتمال."
        )
        await msg.answer(txt, parse_mode="HTML")
        from services.database import get_all_admin_ids
        for aid in get_all_admin_ids():
            try:
                await bot.send_message(aid, f"🚨 طلب معلق جديد من {uid}")
            except:
                pass
    else:
        database.add_balance(uid, total)
        await msg.answer(f"❌ فشل: {res}\n✅ تم استرجاع الرصيد", parse_mode="HTML")

    await state.clear()
    await msg.answer("القائمة الرئيسية:", reply_markup=kb.main_menu())