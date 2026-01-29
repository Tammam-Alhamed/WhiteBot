"""Admin user management handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.database as database
import services.settings as settings
import data.keyboards as kb
from bot.utils.helpers import smart_edit
from states.admin import AdminState
import html

router = Router()

@router.callback_query(F.data == "admin_users")
async def users_menu_main(call: types.CallbackQuery):
    """Show user management menu."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📜 عرض كل المستخدمين", callback_data="list_users:0")],
        [types.InlineKeyboardButton(text="🔍 بحث بواسطة ID", callback_data="search_user_id")],
        [types.InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_home")]
    ])
    await smart_edit(call, "👥 <b>إدارة المستخدمين:</b>\nاختر طريقة العرض:", markup)


@router.callback_query(F.data.startswith("list_users:"))
async def list_all_users(call: types.CallbackQuery):
    """List all users with pagination."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
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
        is_admin = database.is_user_admin(u['id'])
        admin_tag = "👮‍♂️" if is_admin else ""

        safe_name = html.escape(str(u['name']))
        btn_txt = f"{status} {admin_tag} {safe_name} | {u['balance']:.2f}$"
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
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    await smart_edit(call, "🔍 أرسل <b>الآيدي (ID)</b> للمستخدم:", kb.back_to_admin())
    await state.set_state(AdminState.waiting_for_user_id)


@router.message(AdminState.waiting_for_user_id)
async def search_result(msg: types.Message, state: FSMContext):
    """Show search result."""
    if not database.is_user_admin(msg.from_user.id):
        await state.clear()
        return
    try:
        uid = msg.text.strip()
        user_data = database.get_user_data(uid)
        if not user_data:
             await msg.answer("❌ المستخدم غير موجود.", reply_markup=kb.back_to_admin())
             return

        await open_user_control(msg, uid)
        await state.clear()
    except Exception as e:
        print(f"Error in search: {e}")
        await msg.answer("❌ حدث خطأ غير متوقع.")


@router.callback_query(F.data.startswith("mang_usr:"))
async def manage_user_profile(call: types.CallbackQuery):
    """Open user management profile."""
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    try:
        uid = call.data.split(":")[1]
        await open_user_control(call.message, uid, is_edit=True)
    except Exception as e:
        print(f"ERROR in manage_user_profile: {e}")
        await call.answer("حدث خطأ أثناء فتح الملف!", show_alert=True)


async def open_user_control(msg_or_call, user_id, is_edit=False):
    """Show user control panel."""
    try:
        data = database.get_user_data(user_id)
        markup = kb.back_to_admin()

        if not data:
            text = "❌ مستخدم غير موجود"
            if is_edit:
                if msg_or_call.photo:
                     await msg_or_call.edit_caption(caption=text, reply_markup=markup)
                else:
                     await msg_or_call.edit_text(text, reply_markup=markup)
            else:
                await msg_or_call.answer(text, reply_markup=markup)
            return

        bal = data.get('balance', 0)
        name = html.escape(str(data.get('name', 'غير معروف')))
        username = f"@{html.escape(data.get('username'))}" if data.get('username') else "لا يوجد"
        status = "🔴 <b>محظور</b>" if data.get('banned') else "🟢 <b>نشط</b>"

        is_admin = database.is_user_admin(user_id)
        role = "👮‍♂️ <b>Admin</b>" if is_admin else "👤 <b>User</b>"

        txt = (
            f"👤 <b>ملف المستخدم:</b>\n"
            f"🆔 <code>{user_id}</code>\n"
            f"📝 {name}\n"
            f"🔗 {username}\n"
            f"💰 الرصيد: <b>{bal:.2f}$</b>\n"
            f"📊 الحالة: {status}\n"
            f"🔑 الرتبة: {role}\n"
            f"━━━━━━━━━━━━"
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            types.InlineKeyboardButton(text="➕ إضافة رصيد", callback_data=f"admin_add_bal:{user_id}"),
            types.InlineKeyboardButton(text="➖ خصم رصيد", callback_data=f"admin_sub_bal:{user_id}")
        )
        keyboard.row(types.InlineKeyboardButton(text="📜 سجل الطلبات", callback_data=f"admin_history:{user_id}"))

        ban_txt = "🟢 فك الحظر" if data.get('banned') else "⛔ حظر"
        ban_act = f"admin_unban:{user_id}" if data.get('banned') else f"admin_ban:{user_id}"

        admin_txt = "🔽 إزالة من الأدمن" if is_admin else "👮‍♂️ ترقية لأدمن"
        admin_act = f"demote_admin:{user_id}" if is_admin else f"promote_admin:{user_id}"

        keyboard.row(
            types.InlineKeyboardButton(text=ban_txt, callback_data=ban_act),
            types.InlineKeyboardButton(text=admin_txt, callback_data=admin_act)
        )
        keyboard.row(types.InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="list_users:0"))

        if is_edit:
            if msg_or_call.photo:
                await msg_or_call.edit_caption(caption=txt, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            else:
                await msg_or_call.edit_text(text=txt, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await msg_or_call.answer(text=txt, reply_markup=keyboard.as_markup(), parse_mode="HTML")

    except Exception as e:
        print(f"ERROR in open_user_control: {e}")
        pass


# ==================== قسم إضافة الرصيد ====================

# 1. عند الضغط على زر إضافة رصيد
@router.callback_query(F.data.startswith("admin_add_bal:"))
async def ask_balance_currency_step(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    user_id = call.data.split(":")[1]

    await smart_edit(
        call,
        "💱 <b>اختر عملة الإضافة:</b>\n"
        "هل تريد إضافة الرصيد بالدولار المباشر أم بالليرة السورية (سيتم التحويل)؟",
        kb.admin_balance_currency(user_id)
    )

# 2. بعد اختيار العملة للإضافة
@router.callback_query(F.data.startswith("add_bal_curr:"))
async def ask_balance_amount_final(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    currency = parts[1] # syp أو usd
    user_id = parts[2]

    await state.update_data(target_user_id=user_id, currency_mode=currency)

    curr_text = "ليرة سورية (SYP)" if currency == "syp" else "دولار ($)"
    rate_info = ""

    if currency == "syp":
        rate = settings.get_setting("exchange_rate")
        rate_info = f"\nℹ️ سعر الصرف الحالي: <b>{rate}</b>"

    back_btn = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="❌ إلغاء", callback_data=f"mang_usr:{user_id}")
    ]])

    await smart_edit(
        call,
        f"💰 <b>إضافة رصيد ({curr_text}):</b>\n"
        f"أرسل القيمة المراد إضافتها الآن (أرقام فقط).{rate_info}",
        back_btn
    )
    await state.set_state(AdminState.waiting_for_balance_amount)

# 3. تنفيذ الإضافة
@router.message(AdminState.waiting_for_balance_amount)
async def perform_add_balance(msg: types.Message, state: FSMContext):
    if not database.is_user_admin(msg.from_user.id):
        await state.clear()
        return

    try:
        amount_input = float(msg.text)
    except:
        return await msg.answer("❌ أرقام فقط!")

    data = await state.get_data()
    user_id = data['target_user_id']
    currency = data.get('currency_mode', 'usd')

    final_usd_amount = 0.0
    msg_details = ""

    if currency == 'syp':
        rate = settings.get_setting("exchange_rate")
        if rate <= 0: rate = 1
        final_usd_amount = amount_input / rate
        msg_details = f"({amount_input:,} ل.س)"
    else:
        final_usd_amount = amount_input
        msg_details = ""

    new_bal = database.add_balance(user_id, final_usd_amount)

    await msg.answer(
        f"✅ <b>تمت الإضافة بنجاح!</b>\n"
        f"👤 للمستخدم: <code>{user_id}</code>\n"
        f"➕ المبلغ المضاف: <b>{final_usd_amount:.2f}$</b> {msg_details}\n"
        f"💰 الرصيد الجديد: <b>{new_bal:.2f}$</b>",
        parse_mode="HTML"
    )

    await open_user_control(msg, user_id, is_edit=False)

    try:
        await msg.bot.send_message(
            user_id,
            f"➕ تم إضافة رصيد لحسابك\n"
            f"المبلغ: {final_usd_amount:.2f}$\n"
            f"رصيدك الحالي: {new_bal:.2f}$"
        )
    except:
        pass

    await state.clear()


# ==================== قسم خصم الرصيد (الجديد) ====================

# 1. عند الضغط على زر خصم رصيد (نسأل عن العملة)
@router.callback_query(F.data.startswith("admin_sub_bal:"))
async def ask_sub_balance_currency_step(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    user_id = call.data.split(":")[1]

    # استخدام الدالة الجديدة للخصم
    await smart_edit(
        call,
        "💱 <b>اختر عملة الخصم:</b>\n"
        "هل تريد خصم الرصيد بالدولار المباشر أم بالليرة السورية (سيتم التحويل)؟",
        kb.admin_sub_balance_currency(user_id)
    )

# 2. بعد اختيار العملة للخصم
@router.callback_query(F.data.startswith("sub_bal_curr:"))
async def ask_sub_balance_amount_final(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    currency = parts[1] # syp أو usd
    user_id = parts[2]

    await state.update_data(target_user_id=user_id, currency_mode=currency)

    curr_text = "ليرة سورية (SYP)" if currency == "syp" else "دولار ($)"
    rate_info = ""

    if currency == "syp":
        rate = settings.get_setting("exchange_rate")
        rate_info = f"\nℹ️ سيتم التحويل على سعر صرف: <b>{rate}</b>"

    back_btn = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="❌ إلغاء", callback_data=f"mang_usr:{user_id}")
    ]])

    await smart_edit(
        call,
        f"➖ <b>خصم رصيد ({curr_text}):</b>\n"
        f"أرسل القيمة المراد خصمها الآن (أرقام فقط).{rate_info}",
        back_btn
    )
    # استخدام الحالة الجديدة للخصم
    await state.set_state(AdminState.waiting_for_sub_balance_amount)

# 3. تنفيذ الخصم
@router.message(AdminState.waiting_for_sub_balance_amount)
async def perform_sub_balance(msg: types.Message, state: FSMContext):
    if not database.is_user_admin(msg.from_user.id):
        await state.clear()
        return

    try:
        amount_input = float(msg.text)
    except:
        return await msg.answer("❌ أرقام فقط!")

    data = await state.get_data()
    user_id = data['target_user_id']
    currency = data.get('currency_mode', 'usd')

    final_usd_amount = 0.0
    msg_details = ""

    if currency == 'syp':
        rate = settings.get_setting("exchange_rate")
        if rate <= 0: rate = 1
        final_usd_amount = amount_input / rate
        msg_details = f"({amount_input:,} ل.س)"
    else:
        final_usd_amount = amount_input
        msg_details = ""

    # تنفيذ الخصم
    if database.deduct_balance(user_id, final_usd_amount):
        new_bal = database.get_balance(user_id)

        await msg.answer(
            f"✅ <b>تم الخصم بنجاح!</b>\n"
            f"👤 من المستخدم: <code>{user_id}</code>\n"
            f"➖ المبلغ المخصوم: <b>{final_usd_amount:.2f}$</b> {msg_details}\n"
            f"💰 الرصيد الجديد: <b>{new_bal:.2f}$</b>",
            parse_mode="HTML"
        )

        # إشعار المستخدم
        try:
            await msg.bot.send_message(
                user_id,
                f"➖ تم خصم رصيد من حسابك\n"
                f"المبلغ: {final_usd_amount:.2f}$\n"
                f"رصيدك الحالي: {new_bal:.2f}$"
            )
        except:
            pass
    else:
        await msg.answer("❌ <b>فشلت العملية:</b> رصيد المستخدم غير كافٍ.", parse_mode="HTML")

    await open_user_control(msg, user_id, is_edit=False)
    await state.clear()


# ==================== دوال إدارية أخرى ====================

@router.callback_query(F.data.startswith("promote_admin:"))
async def promote_user_to_admin(call: types.CallbackQuery):
    if not database.is_super_admin(call.from_user.id):
        return await call.answer("❌ فقط السوبر أدمن يمكنه ترقية المستخدمين!", show_alert=True)
    uid = call.data.split(":")[1]
    database.set_admin(uid, True)
    await call.answer("✅ تم ترقية المستخدم إلى أدمن بنجاح!", show_alert=True)
    await open_user_control(call.message, uid, is_edit=True)

@router.callback_query(F.data.startswith("demote_admin:"))
async def demote_user_from_admin(call: types.CallbackQuery):
    if not database.is_super_admin(call.from_user.id):
        return await call.answer("❌ فقط السوبر أدمن يمكنه تنزيل المستخدمين!", show_alert=True)
    uid = call.data.split(":")[1]
    if str(uid) == str(call.from_user.id):
        return await call.answer("❌ لا يمكنك إزالة نفسك من الأدمن!", show_alert=True)
    try:
        if database.is_super_admin(int(uid)):
            return await call.answer("❌ لا يمكن إزالة سوبر أدمن!", show_alert=True)
    except: pass

    database.set_admin(uid, False)
    await call.answer("✅ تم إزالة صلاحيات الأدمن.", show_alert=True)
    await open_user_control(call.message, uid, is_edit=True)

@router.callback_query(F.data.startswith("admin_ban:"))
async def ban_user_exec(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    uid = call.data.split(":")[1]
    database.ban_user(uid, True)
    await call.answer("تم الحظر ⛔")
    await open_user_control(call.message, uid, is_edit=True)

@router.callback_query(F.data.startswith("admin_unban:"))
async def unban_user_exec(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    uid = call.data.split(":")[1]
    database.ban_user(uid, False)
    await call.answer("تم فك الحظر ✅")
    await open_user_control(call.message, uid, is_edit=True)

@router.callback_query(F.data.startswith("admin_history:"))
async def user_history(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    try:
        uid = call.data.split(":")[1]
        txt = f"📜 <b>سجل طلبات المستخدم {uid}:</b>\n━━━━━━━━━━━━\n"
        has_orders = False

        local_orders = database.get_user_local_orders(uid)
        if local_orders:
            has_orders = True
            txt += "<b>📦 الطلبات المحلية:</b>\n"
            for o in local_orders[:10]:
                status_icon = "✅" if o['status'] == 'completed' else "⏳"
                price_disp = o['product'].get('price', 0)
                txt += f"{status_icon} <b>{o['product'].get('name', 'منتج')}</b>\n🔢 {o['id']} | 💰 {price_disp}$\n----------------\n"

        if not has_orders: txt += "📂 السجل فارغ"
        back_markup = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔙 رجوع", callback_data=f"mang_usr:{uid}")]])
        await smart_edit(call, txt, back_markup)
    except Exception as e:
        print(f"Error in history: {e}")
        await call.answer("خطأ في السجل", show_alert=True)