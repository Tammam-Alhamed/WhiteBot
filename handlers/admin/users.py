"""Admin user management handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.database as database
import services.settings as settings
import services.api_manager as api_manager
import data.keyboards as kb
from bot.utils.helpers import smart_edit
from states.admin import AdminState
import html
import asyncio  # ضروري جداً
import math

from ui.admin.order_cards import format_api_admin_status, format_admin_order_status
from constants.orders import ORDER_SOURCE_API, ORDER_SOURCE_LOCAL
from constants.orders import norm_order_status
from ui.admin.order_lists import render_admin_user_orders_all_statuses

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

    # تسريع جلب المستخدمين
    users = await asyncio.to_thread(database.get_all_users_list)

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
        # تسريع البحث
        user_data = await asyncio.to_thread(database.get_user_data, uid)

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
        # تسريع جلب البيانات
        data = await asyncio.to_thread(database.get_user_data, user_id)
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

        bal = float(data.get('balance', 0) or 0.0)
        name = html.escape(str(data.get('name', 'غير معروف')))
        username = f"@{html.escape(data.get('username'))}" if data.get('username') else "لا يوجد"
        status = "🔴 <b>محظور</b>" if data.get('banned') else "🟢 <b>نشط</b>"

        is_admin = database.is_user_admin(user_id)
        role = "👮‍♂️ <b>Admin</b>" if is_admin else "👤 <b>User</b>"

        # Stats
        rate = settings.get_setting("exchange_rate") or 1
        if rate == 0:
            rate = 1
        commission = settings.get_deposit_commission()
        total_deposited_usd = await asyncio.to_thread(database.get_total_deposited, user_id)
        user_deposits = await asyncio.to_thread(database.get_user_deposits, user_id)
        approved_deps = [d for d in user_deposits if (d.get("status") or "").lower() == "approved"]

        dep_sum_usd = 0.0
        usd_methods = ["sham_usd", "usdt_bep20", "usdt_coinex"]
        for d in approved_deps:
            try:
                amount = float(d.get("amount", 0) or 0)
                method = d.get("method")
                if method in usd_methods:
                    deposit_usd = amount
                else:
                    deposit_usd = amount / rate
                commission_amount = deposit_usd * (commission / 100)
                dep_sum_usd += max(0.0, deposit_usd - commission_amount)
            except Exception:
                continue

        # Orders stats (completed only)
        local_orders = await asyncio.to_thread(database.get_user_local_orders, user_id)
        api_orders = await asyncio.to_thread(database.get_user_api_history, user_id, 200)
        completed_statuses = {"completed", "success", "accept"}
        local_completed = [o for o in local_orders if (o.get("status") or "").lower() in completed_statuses]
        api_completed = [o for o in api_orders if (o.get("status") or "").lower() in completed_statuses]

        local_amount = 0.0
        for o in local_completed:
            try:
                qty = int(o.get("qty", 1) or 1)
                unit = float((o.get("product") or {}).get("price", 0) or 0)
                local_amount += unit * qty
            except Exception:
                continue
        api_amount = sum(float(o.get("price", 0) or 0) for o in api_completed)

        global_balance = await asyncio.to_thread(database.get_total_users_balance)

        txt = (
            f"👤 <b>ملف المستخدم:</b>\n"
            f"🆔 <code>{user_id}</code>\n"
            f"📝 {name}\n"
            f"🔗 {username}\n"
            f"💰 الرصيد: <b>{bal:.2f}$</b>\n"
            f"📊 الحالة: {status}\n"
            f"🔑 الرتبة: {role}\n"
            f"━━━━━━━━━━━━\n"
            f"💳 <b>إحصائيات:</b>\n"
            f"• إجمالي الإيداعات: <b>{len(approved_deps)}</b> | <b>{dep_sum_usd:.2f}$</b>\n"
            f"• إجمالي الطلبات: <b>{len(local_completed) + len(api_completed)}</b> | <b>{(local_amount + api_amount):.2f}$</b>\n"
            f"• إجمالي رصيد جميع المستخدمين: <b>{global_balance:.2f}$</b>\n"
            f"━━━━━━━━━━━━"
        )

        keyboard = InlineKeyboardBuilder()

        # الصف الأول: إضافة وخصم
        keyboard.row(
            types.InlineKeyboardButton(text="➕ إضافة رصيد", callback_data=f"admin_add_bal:{user_id}"),
            types.InlineKeyboardButton(text="➖ خصم رصيد", callback_data=f"admin_sub_bal:{user_id}")
        )

        # الصف الثاني: السجل
        keyboard.row(types.InlineKeyboardButton(text="📜 سجل الطلبات", callback_data=f"admin_history:{user_id}"))

        keyboard.row(
            types.InlineKeyboardButton(text="✉️ إرسال رسالة لهذا المستخدم", callback_data=f"admin_msg_user:{user_id}"),
            types.InlineKeyboardButton(text="💳 سجل الإيداعات", callback_data=f"admin_dep_hist:{user_id}")
        )

        # الصف الثالث: الحظر والترقية
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


@router.callback_query(F.data.startswith("admin_msg_user:"))
async def admin_msg_user_start(call: types.CallbackQuery, state: FSMContext):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    uid = call.data.split(":")[1]
    await state.update_data(target_user_id=uid)
    await state.set_state(AdminState.waiting_for_user_message)
    await smart_edit(call, f"✉️ أرسل الرسالة الآن للمستخدم:\n<code>{uid}</code>", kb.back_to_admin())


@router.message(AdminState.waiting_for_user_message)
async def admin_msg_user_send(msg: types.Message, state: FSMContext):
    if not database.is_user_admin(msg.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    uid = data.get("target_user_id")
    if not uid:
        await state.clear()
        return
    if not msg.text:
        return await msg.answer("❌ يرجى إرسال نص الرسالة فقط.")
    try:
        await msg.bot.send_message(int(uid), msg.text)
        await msg.answer("✅ تم الإرسال.", reply_markup=kb.back_to_admin())
    except Exception:
        await msg.answer("❌ فشل الإرسال (ربما المستخدم حظر البوت).", reply_markup=kb.back_to_admin())
    await state.clear()


@router.callback_query(F.data.startswith("admin_dep_hist:"))
async def admin_user_deposits(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    uid = call.data.split(":")[1]
    deps = await asyncio.to_thread(database.get_user_deposits, uid)

    if not deps:
        return await smart_edit(call, "💳 لا يوجد إيداعات لهذا المستخدم.", kb.back_btn(f"mang_usr:{uid}"))

    pending = [d for d in deps if (d.get("status") or "").lower() == "pending"]
    approved = [d for d in deps if (d.get("status") or "").lower() == "approved"]

    txt = f"💳 <b>سجل الإيداعات:</b> <code>{uid}</code>\n"
    txt += "━━━━━━━━━━━━\n"
    txt += f"⏳ Pending: <b>{len(pending)}</b>\n"
    txt += f"✅ Approved: <b>{len(approved)}</b>\n"
    txt += "━━━━━━━━━━━━\n"
    txt += "\n".join(
        f"- #{d.get('id')} | {d.get('method')} | {d.get('amount')} | {d.get('date')} | {d.get('status')}"
        for d in deps[:25]
    )

    await smart_edit(call, txt, kb.back_btn(f"mang_usr:{uid}"))


# ==================== إضافة الرصيد (محدث) ====================

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
        msg_details = "($)"

    # تسريع الإضافة
    new_bal = await asyncio.to_thread(database.add_balance, user_id, final_usd_amount)

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


# ==================== خصم الرصيد (محدث) ====================

@router.callback_query(F.data.startswith("admin_sub_bal:"))
async def ask_sub_balance_currency_step(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    user_id = call.data.split(":")[1]
    await smart_edit(
        call,
        "💱 <b>اختر عملة الخصم:</b>\n"
        "هل تريد خصم الرصيد بالدولار المباشر أم بالليرة السورية (سيتم التحويل)؟",
        kb.admin_sub_balance_currency(user_id)
    )

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
    await state.set_state(AdminState.waiting_for_sub_balance_amount)

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
        msg_details = "($)"

    # تنفيذ الخصم بسرعة
    success = await asyncio.to_thread(database.deduct_balance, user_id, final_usd_amount)

    if success:
        new_bal = await asyncio.to_thread(database.get_balance, user_id)

        await msg.answer(
            f"✅ <b>تم الخصم بنجاح!</b>\n"
            f"👤 من المستخدم: <code>{user_id}</code>\n"
            f"➖ المبلغ المخصوم: <b>{final_usd_amount:.2f}$</b> {msg_details}\n"
            f"💰 الرصيد الجديد: <b>{new_bal:.2f}$</b>",
            parse_mode="HTML"
        )

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


# ==================== الإجراءات الأخرى ====================

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

# 🔥🔥 هنا تم إصلاح عرض السجل 🔥🔥
# ==================== معالجات السجل الجديدة ====================

@router.callback_query(F.data.startswith("admin_history:"))
async def user_history_entry(call: types.CallbackQuery):
    """نقطة الدخول لسجل المستخدم."""
    if not database.is_user_admin(call.from_user.id): return
    uid = call.data.split(":")[1]
    await render_user_history_page(call, uid, 1)


@router.callback_query(F.data.startswith("hist_page:"))
async def user_history_pagination(call: types.CallbackQuery):
    """التعامل مع التنقل بين الصفحات."""
    if not database.is_user_admin(call.from_user.id): return
    parts = call.data.split(":")
    uid = parts[1]
    page = int(parts[2])
    await render_user_history_page(call, uid, page)


@router.callback_query(F.data.startswith("view_u_ord:"))
async def view_user_order_details(call: types.CallbackQuery):
    """عرض تفاصيل طلب معين من السجل مع زر رجوع ذكي."""
    if not database.is_user_admin(call.from_user.id): return

    parts = call.data.split(":")
    user_id = parts[1]
    order_id = parts[2]
    page = parts[3]  # رقم الصفحة للعودة إليها

    # البحث عن الطلب
    all_local = database.get_user_local_orders(user_id)
    target_order = next((o for o in all_local if str(o.get('id')) == str(order_id)), None)
    is_api = False

    if not target_order:
        # بحث في API
        all_api = database.get_user_api_history(user_id, 200)
        target_order = next(
            (o for o in all_api if str(o.get('uuid')) == str(order_id) or str(o.get('order_id')) == str(order_id)),
            None)
        if target_order:
            is_api = True

    if not target_order:
        return await call.answer("❌ الطلب غير موجود", show_alert=True)

    # عرض البطاقة
    txt = _build_user_history_card(target_order, is_api=is_api)

    markup = InlineKeyboardBuilder()
    markup.button(text="🔙 رجوع للسجل", callback_data=f"hist_page:{user_id}:{page}")

    await smart_edit(call, txt, markup.as_markup())


# ==================== دوال مساعدة للعرض (جديد) ====================

def _build_user_history_card(order: dict, is_api: bool = False) -> str:
    """بناء بطاقة تفاصيل الطلب لسجل المستخدم."""
    if is_api:
        # تنسيق طلب API
        oid = order.get('uuid', order.get('id', '---'))
        status_label, _ = format_api_admin_status(order.get('status', 'Unknown'))
        service = order.get('product_name', order.get('product', {}).get('name', 'خدمة API'))
        price = order.get('price', 0)
        date = order.get('created_at', order.get('date', '---'))
        code = order.get('code')

        txt = (
            f"📦 <b>طلب API</b>\n"
            f"🆔 <b>رقم الطلب:</b> <code>{oid}</code>\n"
            f"────────────────\n"
            f"🔹 <b>الخدمة:</b> {service}\n"
            f"🔹 <b>السعر:</b> {price}$\n"
            f"🔹 <b>الحالة:</b> {status_label}\n"
            f"📅 <b>التاريخ:</b> {date}\n"
        )
        if code:
            txt += f"🔑 <b>الكود:</b>\n<pre>{code}</pre>"
    else:
        # تنسيق طلب محلي
        oid = order.get('id', '---')
        status_label, _ = format_admin_order_status(order.get('status', ''))
        service = order.get('product', {}).get('name', 'منتج محلي')
        qty = order.get('qty', 1)
        total = float(order.get('product', {}).get('price', 0)) * int(qty)
        date = order.get('date', '---')

        txt = (
            f"🏠 <b>طلب محلي</b>\n"
            f"🆔 <b>رقم الطلب:</b> <code>{oid}</code>\n"
            f"────────────────\n"
            f"🔸 <b>الخدمة:</b> {service}\n"
            f"🔸 <b>الإجمالي:</b> {total}$ ({qty} قطعة)\n"
            f"🔸 <b>الحالة:</b> {status_label}\n"
            f"📅 <b>التاريخ:</b> {date}\n"
        )
        # عرض المدخلات إن وجدت
        inputs = order.get('inputs')
        if inputs:
            txt += f"\n📝 <b>البيانات:</b> {inputs}"

    return txt


async def render_user_history_page(call: types.CallbackQuery, user_id: str, page: int):
    """عرض صفحة من سجل طلبات المستخدم."""
    PAGE_SIZE = 10

    # 1. جلب البيانات من المصدرين
    local_orders = await asyncio.to_thread(database.get_user_local_orders, user_id)
    api_orders = await asyncio.to_thread(database.get_user_api_history, user_id, 100)  # جلب آخر 100 طلب API

    # 2. توحيد البيانات
    all_orders = []

    for o in local_orders:
        o['order_source'] = ORDER_SOURCE_LOCAL
        o['sort_date'] = o.get('date', '')
        all_orders.append(o)

    for o in api_orders:
        o['order_source'] = ORDER_SOURCE_API
        o['sort_date'] = o.get('created_at', '')
        # التأكد من وجود Product Name
        if 'product' not in o:
            o['product'] = {'name': o.get('product_name', 'API Service')}
        all_orders.append(o)

    # 3. الترتيب (الأحدث أولاً)
    all_orders.sort(key=lambda x: x.get('sort_date', ''), reverse=True)

    # 4. تقسيم الصفحات
    if not all_orders:
        await call.answer("📂 السجل فارغ لهذا المستخدم.", show_alert=True)
        return

    total_items = len(all_orders)
    total_pages = math.ceil(total_items / PAGE_SIZE)

    if page > total_pages: page = total_pages
    if page < 1: page = 1

    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_items = all_orders[start_idx:end_idx]

    # 5. بناء القائمة
    txt = f"📜 <b>سجل طلبات المستخدم:</b> <code>{user_id}</code>\n"
    txt += f"📄 صفحة <b>{page}</b> من <b>{total_pages}</b>\n"
    txt += f"📦 إجمالي الطلبات: {total_items}"
    txt += "\n═══════════════════════"

    builder = InlineKeyboardBuilder()

    for order in page_items:
        is_api = order.get('order_source') == ORDER_SOURCE_API
        oid = order.get('uuid') if is_api else order.get('id')

        # تحديد الأيقونة والسعر
        if is_api:
            icon = "🌐"
            price = order.get('price', 0)
            p_name = order.get('product_name', 'API')
        else:
            icon = "🏠"
            price = float(order.get('product', {}).get('price', 0)) * int(order.get('qty', 1))
            p_name = order.get('product', {}).get('name', 'Local')

        # زر مختصر: أيقونة | رقم الطلب | الخدمة | السعر
        # تقصير اسم الخدمة ليناسب الزر
        short_name = (p_name[:15] + '..') if len(p_name) > 15 else p_name
        btn_text = f"{icon} #{str(oid)[-6:]} | {short_name} | {price}$"

        # Callback: view_u_ord:USER_ID:ORDER_ID:PAGE
        builder.button(text=btn_text, callback_data=f"view_u_ord:{user_id}:{oid}:{page}")

    builder.adjust(1)

    # أزرار التنقل
    nav_row = []
    if page > 1:
        nav_row.append(types.InlineKeyboardButton(text="⬅️ سابق", callback_data=f"hist_page:{user_id}:{page - 1}"))

    nav_row.append(types.InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))

    if page < total_pages:
        nav_row.append(types.InlineKeyboardButton(text="تالي ➡️", callback_data=f"hist_page:{user_id}:{page + 1}"))

    builder.row(*nav_row)
    builder.row(types.InlineKeyboardButton(text="🔙 رجوع للملف الشخصي", callback_data=f"mang_usr:{user_id}"))

    await smart_edit(call, txt, builder.as_markup())
