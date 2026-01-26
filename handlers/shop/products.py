"""Product browsing and purchasing handlers."""
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
import config
import services.database as database
import services.api_manager as api_manager
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
    
    syp_price = format_price(prod['price'])
    desc = prod.get('description', '')
    desc_txt = f"\n\n📝 <b>ملاحظات:</b>\n{desc}" if desc else ""
    
    txt = f"🛒 <b>شراء:</b> {prod['name']}\n💰 <b>السعر:</b> {syp_price}{desc_txt}"
    
    cancel_markup = kb.cancel_or_back_btn(back_target)
    
    if prod.get('product_type') == "amount":
        qv = prod.get('qty_values', {})
        await state.update_data(min_q=qv.get('min', 1), max_q=qv.get('max', 100000))
        await state.set_state(ShopState.waiting_for_quantity)
        await call.message.delete()
        await call.message.answer(
            txt + "\n\n👇 <b>أدخل الكمية المطلوبة:</b>",
            reply_markup=cancel_markup,
            parse_mode="HTML"
        )
    
    elif not prod.get('params'):
        await call.message.delete()
        await finalize_order(call.message, state, call.bot)
    
    else:
        await call.message.delete()
        await state.set_state(ShopState.waiting_for_input)
        await call.message.answer(
            f"{txt}\n\n📝 أدخل: <b>{prod['params'][0]}</b>",
            reply_markup=cancel_markup,
            parse_mode="HTML"
        )


@router.message(ShopState.waiting_for_quantity)
async def process_qty(msg: types.Message, state: FSMContext):
    """Process quantity input."""
    data = await state.get_data()
    back_target = data.get('back_path', 'home')
    cancel_markup = kb.cancel_or_back_btn(back_target)

    try:
        qty = int(msg.text)
        if qty < data['min_q'] or qty > data['max_q']:
            raise ValueError
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
    except:
        await msg.answer("❌ كمية غير صحيحة، حاول مجدداً:", reply_markup=cancel_markup)


@router.message(ShopState.waiting_for_input)
async def process_inp(msg: types.Message, state: FSMContext):
    """Process input parameters."""
    d = await state.get_data()
    back_target = d.get('back_path', 'home')
    cancel_markup = kb.cancel_or_back_btn(back_target)
    
    inputs = d['collected']
    inputs.append(msg.text)
    await state.update_data(collected=inputs)
    
    idx = d['idx'] + 1
    if idx < len(d['params']):
        await state.update_data(idx=idx)
        await msg.answer(
            f"📝 أدخل: <b>{d['params'][idx]}</b>",
            reply_markup=cancel_markup,
            parse_mode="HTML"
        )
    else:
        await finalize_order(msg, state, msg.bot)


async def finalize_order(msg: types.Message, state: FSMContext, bot: Bot):
    """Finalize and execute order."""
    d = await state.get_data()
    uid = d.get('real_user_id', msg.from_user.id)
    if uid == bot.id:
        uid = msg.chat.id
    
    prod, qty = d['prod'], d['qty']
    total = float(prod['price']) * qty
    
    if not database.deduct_balance(uid, total):
        await msg.answer(
            f"{config.MSG_NO_BALANCE}\n💰 التكلفة: {format_price(total)}",
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )
        await state.clear()
        return

    await msg.answer("⏳ جاري إرسال الطلب للمزود...")
    ok, res, uuid, code = await api_manager.execute_order_dynamic(
        prod['id'], qty, d['collected'], d['params']
    )
    
    if ok:
        if uuid:
            api_manager.save_uuid_locally(uid, uuid)
        txt = (
            f"✅ <b>تم استلام طلبك بنجاح!</b>\n"
            f"🔢 رقم العملية: <code>{res}</code>\n"
            f"💰 تم خصم: {format_price(total)}\n\n"
            f"🕵️‍♂️ <b>ملاحظة:</b> يمكنك متابعة حالة التنفيذ من قسم <b>📦 طلباتي</b>."
        )
        await msg.answer(txt, parse_mode="HTML")
        
    elif code == 100:
        lid = database.save_pending_order(uid, prod, qty, d['collected'], d['params'])
        await msg.answer(
            f"⏳ <b>الطلب قيد المعالجة (Processing)</b>\n"
            f"رقم المتابعة: <code>{lid}</code>\n"
            f"سيتم إشعارك عند الاكتمال.",
            parse_mode="HTML"
        )
        for aid in config.ADMIN_IDS:
            try:
                await bot.send_message(aid, f"🚨 طلب معلق جديد من {uid}")
            except:
                pass
    else:
        database.add_balance(uid, total)
        await msg.answer(f"❌ فشل: {res}\n✅ تم استرجاع الرصيد", parse_mode="HTML")
    
    await state.clear()
    await msg.answer("القائمة الرئيسية:", reply_markup=kb.main_menu())
