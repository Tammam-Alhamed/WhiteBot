"""Admin user management handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.database as database
import services.api_manager as api_manager
import data.keyboards as kb
from bot.utils.helpers import smart_edit
from states.admin import AdminState

router = Router()


@router.callback_query(F.data == "admin_users")
async def users_menu_main(call: types.CallbackQuery):
    """Show user management menu."""
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📜 عرض كل المستخدمين", callback_data="list_users:0")],
        [types.InlineKeyboardButton(text="🔍 بحث بواسطة ID", callback_data="search_user_id")],
        [types.InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_home")]
    ])
    await smart_edit(call, "👥 <b>إدارة المستخدمين:</b>\nاختر طريقة العرض:", markup)


@router.callback_query(F.data.startswith("list_users:"))
async def list_all_users(call: types.CallbackQuery):
    """List all users with pagination."""
    try:
        page = int(call.data.split(":")[1])
    except:
        page = 0
    
    users = database.get_all_users_list()
    if not users:
        return await call.answer("لا يوجد مستخدمين!", show_alert=True)

    ITEMS_PER_PAGE = 6
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_users = users[start:end]
    
    builder = InlineKeyboardBuilder()
    for u in current_users:
        status = "⛔" if u['banned'] else "✅"
        btn_txt = f"{status} {u['name']} | {u['balance']}$"
        builder.button(text=btn_txt, callback_data=f"mang_usr:{u['id']}")
    builder.adjust(1)

    nav_btns = []
    if page > 0:
        nav_btns.append(types.InlineKeyboardButton(text="⬅️ السابق", callback_data=f"list_users:{page-1}"))
    if end < len(users):
        nav_btns.append(types.InlineKeyboardButton(text="التالي ➡️", callback_data=f"list_users:{page+1}"))
    
    if nav_btns:
        builder.row(*nav_btns)
    builder.row(types.InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_users"))

    txt = f"👥 <b>قائمة المستخدمين ({len(users)})</b>\nالصفحة {page+1}:"
    await smart_edit(call, txt, builder.as_markup())


@router.callback_query(F.data == "search_user_id")
async def ask_search_id(call: types.CallbackQuery, state: FSMContext):
    """Ask for user ID to search."""
    await smart_edit(call, "🔍 أرسل <b>الآيدي (ID)</b> للمستخدم:", kb.back_to_admin())
    await state.set_state(AdminState.waiting_for_user_id)


@router.message(AdminState.waiting_for_user_id)
async def search_result(msg: types.Message, state: FSMContext):
    """Show search result."""
    try:
        uid = int(msg.text)
        await open_user_control(msg, uid)
        await state.clear()
    except:
        await msg.answer("آيدي خاطئ")


@router.callback_query(F.data.startswith("mang_usr:"))
async def manage_user_profile(call: types.CallbackQuery):
    """Open user management profile."""
    uid = call.data.split(":")[1]
    await open_user_control(call.message, uid, is_edit=True)


async def open_user_control(msg_or_call, user_id, is_edit=False):
    """Show user control panel."""
    data = database.get_user_data(user_id)
    if not data:
        text = "❌ مستخدم غير موجود"
        markup = kb.back_to_admin()
        if is_edit:
            await msg_or_call.edit_text(text, reply_markup=markup)
        else:
            await msg_or_call.answer(text, reply_markup=markup)
        return

    bal = data.get('balance', 0)
    name = data.get('name', 'غير معروف')
    username = f"@{data.get('username')}" if data.get('username') else "لا يوجد"
    status = "🔴 <b>محظور</b>" if data.get('banned') else "🟢 <b>نشط</b>"
    
    txt = (
        f"👤 <b>ملف المستخدم:</b>\n"
        f"🆔 <code>{user_id}</code>\n"
        f"📝 {name}\n"
        f"🔗 {username}\n"
        f"💰 الرصيد: <b>{bal}$</b>\n"
        f"📊 الحالة: {status}\n"
        f"━━━━━━━━━━━━"
    )

    ban_txt = "🟢 فك الحظر" if data.get('banned') else "⛔ حظر المستخدم"
    ban_act = f"admin_unban:{user_id}" if data.get('banned') else f"admin_ban:{user_id}"
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ إضافة رصيد", callback_data=f"admin_add_bal:{user_id}"),
         types.InlineKeyboardButton(text="➖ خصم رصيد", callback_data=f"admin_sub_bal:{user_id}")],
        [types.InlineKeyboardButton(text="📜 سجل الطلبات", callback_data=f"admin_history:{user_id}")],
        [types.InlineKeyboardButton(text=ban_txt, callback_data=ban_act)],
        [types.InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="list_users:0")]
    ])

    if is_edit:
        await msg_or_call.edit_text(text=txt, reply_markup=markup, parse_mode="HTML")
    else:
        await msg_or_call.answer(text=txt, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_sub_bal:"))
async def ask_sub_bal(call: types.CallbackQuery, state: FSMContext):
    """Ask for amount to subtract."""
    uid = call.data.split(":")[1]
    await state.update_data(target_uid=uid, action="sub")
    back_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔙 إلغاء", callback_data=f"mang_usr:{uid}")
    ]])
    await smart_edit(call, f"➖ أدخل المبلغ لخصمه من المستخدم بالدولار {uid}:", back_markup)
    await state.set_state(AdminState.waiting_for_amount_add)


@router.callback_query(F.data.startswith("admin_add_bal:"))
async def ask_add_bal(call: types.CallbackQuery, state: FSMContext):
    """Ask for amount to add."""
    uid = call.data.split(":")[1]
    await state.update_data(target_uid=uid, action="add")
    back_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔙 إلغاء", callback_data=f"mang_usr:{uid}")
    ]])
    await smart_edit(call, f"➕ أدخل المبلغ لإضافته للمستخدم بالدولار {uid}:", back_markup)
    await state.set_state(AdminState.waiting_for_amount_add)


@router.message(AdminState.waiting_for_amount_add)
async def exec_balance_change(msg: types.Message, state: FSMContext):
    """Execute balance change."""
    try:
        amount = float(msg.text)
        data = await state.get_data()
        uid = data['target_uid']
        action = data.get('action', 'add')
        
        if action == 'add':
            new_bal = database.add_balance(uid, amount)
            res_txt = f"✅ <b>تم إضافة {amount}$</b>"
        else:
            if database.deduct_balance(uid, amount):
                new_bal = database.get_balance(uid)
                res_txt = f"✅ <b>تم خصم {amount}$</b>"
            else:
                res_txt = "❌ <b>فشل الخصم:</b> الرصيد غير كافٍ."
        
        await msg.answer(res_txt, parse_mode="HTML")
        await open_user_control(msg, uid, is_edit=False)
        await state.clear()
    except:
        await msg.answer("أرقام فقط!")


@router.callback_query(F.data.startswith("admin_ban:"))
async def ban_user_exec(call: types.CallbackQuery):
    """Ban user."""
    uid = call.data.split(":")[1]
    database.ban_user(uid, True)
    await call.answer("تم الحظر ⛔")
    await open_user_control(call.message, uid, is_edit=True)


@router.callback_query(F.data.startswith("admin_unban:"))
async def unban_user_exec(call: types.CallbackQuery):
    """Unban user."""
    uid = call.data.split(":")[1]
    database.ban_user(uid, False)
    await call.answer("تم فك الحظر ✅")
    await open_user_control(call.message, uid, is_edit=True)


@router.callback_query(F.data.startswith("admin_history:"))
async def user_history(call: types.CallbackQuery):
    """Show user order history."""
    uid = call.data.split(":")[1]
    orders = api_manager.get_user_uuids(uid)
    if not orders:
        return await call.answer("السجل فارغ", show_alert=True)
    check_data = api_manager.check_orders_status(orders[:5])
    txt = f"📜 <b>آخر طلبات {uid}:</b>\n"
    for o in check_data:
        txt += f"- {o.get('product_name')} | {o.get('status')} | {o.get('price')}$\n"
    
    back_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔙 رجوع للبروفايل", callback_data=f"mang_usr:{uid}")
    ]])
    await smart_edit(call, txt, back_markup)
