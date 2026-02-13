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

def _is_jawaker_category(name: str) -> bool:
    n = (name or "").lower()
    return "jawaker" in n or "جواكر" in n


def _build_new_order_context_text(user_id: int, previous_order: str | None, bal_before: float, bal_after: float, rate: float) -> str:
    before_syp = int(round(bal_before * rate))
    after_syp = int(round(bal_after * rate))
    prev_txt = previous_order if previous_order else "لا يوجد"
    return (
        f"🧾 <b>طلبك السابق:</b> {prev_txt}\n"
        f"💰 <b>رصيدك قبل هذا الطلب:</b> {bal_before:.2f}$ ({before_syp:,} ل.س)\n"
        f"💳 <b>رصيدك بعد هذا الطلب:</b> {bal_after:.2f}$ ({after_syp:,} ل.س)\n"
        f"━━━━━━━━━━━━\n"
    )


def _get_previous_order_label(user_id: int) -> str | None:
    try:
        local = database.get_user_local_orders(user_id)
    except Exception:
        local = []
    try:
        api = database.get_user_api_history(user_id, limit=1)
    except Exception:
        api = []

    candidates = []
    if local:
        latest_local = sorted(local, key=lambda x: x.get("date", ""), reverse=True)[0]
        candidates.append(("L", latest_local.get("id"), latest_local.get("date", "")))
    if api:
        latest_api = api[0]
        candidates.append(("A", latest_api.get("uuid"), str(latest_api.get("created_at", ""))))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[2], reverse=True)
    src, oid, _ = candidates[0]
    if not oid:
        return None
    return f"{src}#{str(oid)[-8:]}"


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
    filtered = []
    for p in prods:
        # إزالة فري فاير روبوت 2
        if str(p.get("name", "")).strip() == "Free Fire Robot 2":
            continue

        # معالجة سعر جواكر في القائمة
        if _is_jawaker_category(p.get("category_name", "")) and float(p.get("price", 0) or 0) > 0:
            rate = settings.get_setting("exchange_rate")
            syp = int(float(p["price"]) * rate)
            if syp < 1:
                syp = 1
            p['formatted_price'] = f"{syp:,} ل.س"
        else:
            p['formatted_price'] = format_price(p['price'])

        filtered.append(p)

    menu = kb.build_products(filtered, back_callback)

    # ✅ إضافة الملاحظات حسب القسم (النقطة 13)
    msg_text = "👇 المنتجات المتاحة:"
    pk_lower = parent_key.lower()

    if "pubg" in pk_lower or "ببجي" in pk_lower:
        msg_text += "\n\n💡 <b>نصيحة:</b> نوصي باستخدام <b>ببجي موبايل روبوت</b> (الاسرع والافضل سعر)."
    elif "free" in pk_lower and "fire" in pk_lower:
        msg_text += "\n\n💡 <b>نصيحة:</b> نوصي باستخدام <b>فري فير روبوت</b> (الاسرع والافضل سعر)."
    elif "jawaker" in pk_lower or "جواكر" in pk_lower:
        msg_text += "\n\n💡 <b>نصيحة:</b> نوصي باستخدام <b>(Jawaker حسب الكمية)</b> ومن ثم <b>الكميه المطلوبه</b> لتتمكن من شحن الكمية التي تحب."

    await smart_edit(call, msg_text, menu)


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
        # ✅ ضمان عدم ظهور 0 ليرة (خاصة لجواكر)
        price_syp = int(price_usd * rate)
        if price_syp < 1 and price_usd > 0:
            price_syp = 1

        desc = prod.get('description', '')
        desc_txt = f"\n\n📝 <b>ملاحظات:</b>\n{desc}" if desc else ""
        txt = (
            f"🛒 <b>شراء:</b> {prod['name']}\n"
            f"💰 <b>السعر:</b>\n"
            f"🇺🇸 {price_usd:.5f} $\n" # زيادة الدقة للأرقام الصغيرة
            f"🇸🇾 {price_syp:,} ل.س{desc_txt}"
        )

    cancel_markup = kb.cancel_or_back_btn(back_target)

    if prod.get('product_type') == "amount":
        qv = prod.get('qty_values', {})
        await state.update_data(min_q=qv.get('min', 1), max_q=qv.get('max', 100000))
        await state.set_state(ShopState.waiting_for_quantity)

        msg_text = txt + "\n\n👇 <b>أدخل الكمية المطلوبة:</b>"
        await smart_edit(call, msg_text, cancel_markup)

    elif not prod.get('params'):
        await call.message.delete()
        await finalize_order(call.message, state, call.bot)

    else:
        await state.set_state(ShopState.waiting_for_input)
        uid = call.from_user.id
        bal_before = database.get_balance(uid)
        total_cost = float(prod.get("price", 0) or 0) * int(1)
        bal_after = max(0.0, bal_before - total_cost)
        rate = settings.get_setting("exchange_rate")
        prev = _get_previous_order_label(uid)
        ctx = _build_new_order_context_text(uid, prev, bal_before, bal_after, rate)

        msg_text = f"{txt}\n\n{ctx}📝 أدخل: <b>{prod['params'][0]}</b>"
        await smart_edit(call, msg_text, cancel_markup)


@router.message(ShopState.waiting_for_quantity)
async def process_qty(msg: types.Message, state: FSMContext):
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
        # ✅ تنسيق السعر الإجمالي أيضاً
        rate = settings.get_setting("exchange_rate")
        total_syp = int(total * rate)
        if total_syp < 1 and total > 0:
            total_syp = 1

        await msg.answer(f"✅ الكمية: {qty}\n💰 المجموع: {total:.4f}$ ({total_syp:,} ل.س)")

        if not data['params']:
            await finalize_order(msg, state, msg.bot)
        else:
            uid = msg.from_user.id
            bal_before = database.get_balance(uid)
            total_cost = float(data['prod'].get("price", 0) or 0) * int(qty)
            bal_after = max(0.0, bal_before - total_cost)
            # rate = settings.get_setting("exchange_rate") # already fetched
            prev = _get_previous_order_label(uid)
            ctx = _build_new_order_context_text(uid, prev, bal_before, bal_after, rate)
            await msg.answer(
                f"{ctx}📝 أدخل: <b>{data['params'][0]}</b>",
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
        if len(user_input) < 5: # Changed from 6 to 5 for flexibility
            return await msg.answer(
                "❌ <b>خطأ في الإدخال:</b>\n"
                f"معرف اللاعب قصير جداً.\n"
                f"يرجى المحاولة مرة أخرى:",
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )
    elif 'user' in current_param.lower() or 'username' in current_param.lower():
        # بعض الخدمات تقبل يوزر بدون @، لذا سنزيل الشرط الصارم
        pass

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

    prod, qty = d['prod'], d['qty']
    total = float(prod['price']) * qty
    rate = settings.get_setting("exchange_rate")
    total_syp = int(total * rate)
    if total_syp < 1 and total > 0: # ✅ ضمان عدم ظهور 0 عند الخصم
        total_syp = 1

    bal_before = database.get_balance(uid)
    if not database.deduct_balance(uid, total):
        need = max(0.0, total - bal_before)
        await msg.answer(
            f"❌ الرصيد غير كافٍ\n"
            f"يرجى شحن رصيدك\n"
            f"💰 التكلفة: {format_price(total)}\n"
            f"تحتاج: {format_price(need)}",
            reply_markup=kb.insufficient_balance_menu(),
            parse_mode="HTML"
        )
        await state.clear()
        return

    new_bal = database.get_balance(uid)
    new_bal_syp = int(new_bal * rate)

    await msg.answer("⏳ جاري إرسال الطلب للمزود...")
    ok, res, uuid, code = await api_manager.execute_order_dynamic(
        prod['id'], qty, d['collected'], d['params'], uid
    )

    if ok:
        # ✅ 1. تم الحفظ تلقائياً في api_manager
        # (تم حذف السطر الذي كان يسبب الخطأ هنا)

        # ✅ 2. رسالة نجاح للزبون
        txt = (
            f"✅ <b>تم استلام طلبك بنجاح!</b>\n"
            f"━━━━━━━━━━━━\n"
            f"🔢 رقم العملية: <code>{res}</code>\n"
            f"━━━━━━━━━━━━\n"
            f"💰 <b>المبلغ المخصوم:</b>\n"
            f"🇺🇸 {total:.4f} $\n"
            f"🇸🇾 {total_syp:,} ل.س\n"
            f"━━━━━━━━━━━━\n"
            f"💎 <b>رصيدك المتبقي:</b>\n"
            f"🇺🇸 {new_bal:.2f} $\n"
            f"🇸🇾 {new_bal_syp:,} ل.س\n"
            f"━━━━━━━━━━━━\n"
            f"🕵️‍♂️ <b>ملاحظة:</b> يمكنك متابعة حالة التنفيذ من قسم <b>📦 طلباتي</b>."
        )
        await msg.answer(txt, parse_mode="HTML")

        # إشعار للأدمن
        from services.database import get_all_admin_ids
        admin_msg = (
            f"🚀 <b>طلب جديد (عبر API)</b>\n"
            f"👤 المستخدم: <code>{uid}</code>\n"
            f"📦 المنتج: <b>{prod['name']}</b>\n"
            f"🔢 الكمية: {qty}\n"
            f"💰 السعر: {total:.4f} $\n"
            f"🆔 رقم الطلب: <code>{res}</code>\n"
            f"✅ الحالة: تم الإرسال للموقع بنجاح"
        )
        for aid in get_all_admin_ids():
            try:
                await bot.send_message(aid, admin_msg, parse_mode="HTML")
            except:
                pass

    elif code == 100:
        # حالة الرصيد غير كافٍ في الموقع -> تحويل لطلب معلق
        lid = database.save_pending_order(uid, prod, qty, d['collected'], d['params'])
        txt = (
            f"⏳ <b>الطلب قيد المعالجة (Processing)</b>\n"
            f"━━━━━━━━━━━━\n"
            f"🔢 رقم المتابعة: <code>{lid}</code>\n"
            f"━━━━━━━━━━━━\n"
            f"💰 <b>المبلغ المخصوم:</b>\n"
            f"🇺🇸 {total:.4f} $\n"
            f"🇸🇾 {total_syp:,} ل.س\n"
            f"━━━━━━━━━━━━\n"
            f"💎 <b>رصيدك المتبقي:</b>\n"
            f"🇺🇸 {new_bal:.2f} $\n"
            f"🇸🇾 {new_bal_syp:,} ل.س\n"
            f"━━━━━━━━━━━━\n"
            f"سيتم إشعارك عند الاكتمال."
        )
        await msg.answer(txt, parse_mode="HTML")

        # إشعار للأدمن بالطلب المعلق
        from services.database import get_all_admin_ids
        for aid in get_all_admin_ids():
            try:
                await bot.send_message(aid, f"🚨 <b>طلب معلق جديد (يحتاج شحن الموقع)</b>\nمن: {uid}\nرقم: {lid}", parse_mode="HTML")
            except:
                pass
    else:
        # فشل (خطأ آخر) -> استرجاع الرصيد
        database.add_balance(uid, total)
        await msg.answer(f"❌ فشل تنفيذ الطلب: {res}\n✅ تم استرجاع الرصيد لمحفظتك.", parse_mode="HTML")

    await state.clear()
    await msg.answer("القائمة الرئيسية:", reply_markup=kb.main_menu())