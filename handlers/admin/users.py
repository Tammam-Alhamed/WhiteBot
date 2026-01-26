"""Admin user management handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.database as database
import services.api_manager as api_manager
import services.settings as settings
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
    """Execute balance change and notify user."""
    try:
        amount = float(msg.text)
        data = await state.get_data()
        uid = data['target_uid']
        action = data.get('action', 'add')
        rate = settings.get_setting("exchange_rate")
        
        if action == 'add':
            old_bal = database.get_balance(uid)
            new_bal = database.add_balance(uid, amount)
            old_bal_syp = int(old_bal * rate)
            new_bal_syp = int(new_bal * rate)
            amount_syp = int(amount * rate)
            
            res_txt = f"✅ <b>تم إضافة {amount:.2f}$</b>"
            
            # Notify user
            try:
                user_msg = (
                    f"💰 <b>تحديث الرصيد</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"➕ <b>المبلغ المضاف:</b>\n"
                    f"🇺🇸 {amount:.2f} $\n"
                    f"🇸🇾 {amount_syp:,} ل.س\n"
                    f"━━━━━━━━━━━━\n"
                    f"💎 <b>رصيدك الحالي:</b>\n"
                    f"🇺🇸 {new_bal:.2f} $\n"
                    f"🇸🇾 {new_bal_syp:,} ل.س"
                )
                await msg.bot.send_message(uid, user_msg, parse_mode="HTML")
            except:
                pass
        else:
            old_bal = database.get_balance(uid)
            if database.deduct_balance(uid, amount):
                new_bal = database.get_balance(uid)
                old_bal_syp = int(old_bal * rate)
                new_bal_syp = int(round(new_bal * rate))
                amount_syp = int(amount * rate)
                
                res_txt = f"✅ <b>تم خصم {amount:.2f}$</b>"
                
                # Notify user
                try:
                    user_msg = (
                        f"💰 <b>تحديث الرصيد</b>\n"
                        f"━━━━━━━━━━━━\n"
                        f"➖ <b>المبلغ المخصوم:</b>\n"
                        f"🇺🇸 {amount:.2f} $\n"
                        f"🇸🇾 {amount_syp:,} ل.س\n"
                        f"━━━━━━━━━━━━\n"
                        f"💎 <b>رصيدك الحالي:</b>\n"
                        f"🇺🇸 {new_bal:.2f} $\n"
                        f"🇸🇾 {new_bal_syp:,} ل.س"
                    )
                    await msg.bot.send_message(uid, user_msg, parse_mode="HTML")
                except:
                    pass
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
    """Show user order history (both local and API orders)."""
    uid = call.data.split(":")[1]
    
    txt = f"📜 <b>سجل طلبات المستخدم {uid}:</b>\n━━━━━━━━━━━━\n"
    has_orders = False
    
    # Get local orders (pending + completed)
    local_orders = database.get_user_local_orders(uid)
    if local_orders:
        has_orders = True
        txt += "<b>📦 الطلبات المحلية:</b>\n"
        for o in local_orders[:10]:  # Limit to 10 most recent
            total_price = float(o['product']['price']) * int(o['qty'])
            status_icon = "✅" if o['status'] == 'completed' else "⏳"
            status_txt = "مكتمل" if o['status'] == 'completed' else "معلق"
            txt += (
                f"{status_icon} <b>{o['product']['name']}</b>\n"
                f"🔢 رقم: <code>{o['id']}</code>\n"
                f"📊 الحالة: {status_txt}\n"
                f"💰 السعر: {total_price:.2f}$\n"
                f"----------------\n"
            )
    
    # Get API orders
    uuids = api_manager.get_user_uuids(uid)
    if uuids:
        stats = api_manager.check_orders_status(uuids[:10])  # Limit to 10 most recent
        if stats:
            has_orders = True
            if local_orders:
                txt += "\n<b>🌐 طلبات API:</b>\n"
            else:
                txt += "<b>🌐 طلبات API:</b>\n"
            for s in stats:
                icon = "✅" if s.get('status') in ['completed', 'accept'] else "❌" if s.get('status') in ['canceled', 'reject'] else "⏳"
                price = s.get('price', 0)
                status_txt = s.get('status', 'unknown')
                txt += f"{icon} {s.get('product_name', 'Unknown')}\n💰 {price:.2f}$ | {status_txt}\n----------------\n"
    
    if not has_orders:
        txt = f"📜 <b>سجل طلبات المستخدم {uid}:</b>\n━━━━━━━━━━━━\n📂 السجل فارغ"
    
    back_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔙 رجوع للبروفايل", callback_data=f"mang_usr:{uid}")
    ]])
    await smart_edit(call, txt, back_markup)
