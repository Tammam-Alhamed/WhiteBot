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
import html

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
        # حماية الاسم من الرموز التي تكسر HTML
        safe_name = html.escape(str(u['name']))
        btn_txt = f"{status} {safe_name} | {u['balance']}$"
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
    except ValueError:
        await msg.answer("❌ آيدي خاطئ، الرجاء إرسال أرقام فقط.")
    except Exception as e:
        print(f"Error in search: {e}")
        await msg.answer("❌ حدث خطأ غير متوقع.")


@router.callback_query(F.data.startswith("mang_usr:"))
async def manage_user_profile(call: types.CallbackQuery):
    """Open user management profile."""
    try:
        uid = call.data.split(":")[1]
        print(f"DEBUG: Opening profile for {uid}")
        await open_user_control(call.message, uid, is_edit=True)
    except Exception as e:
        print(f"ERROR in manage_user_profile: {e}")
        await call.answer("حدث خطأ أثناء فتح الملف!", show_alert=True)


async def open_user_control(msg_or_call, user_id, is_edit=False):
    """Show user control panel (Smart Handle for Photo/Text)."""
    try:
        data = database.get_user_data(user_id)
        markup = kb.back_to_admin()

        if not data:
            text = "❌ مستخدم غير موجود"
            if is_edit:
                # إذا كانت الرسالة صورة، نعدل الكابشن، وإذا نص نعدل النص
                if msg_or_call.photo:
                     await msg_or_call.edit_caption(caption=text, reply_markup=markup)
                else:
                     await msg_or_call.edit_text(text, reply_markup=markup)
            else:
                await msg_or_call.answer(text, reply_markup=markup)
            return

        bal = data.get('balance', 0)
        # حماية البيانات من رموز HTML
        name = html.escape(str(data.get('name', 'غير معروف')))
        username_raw = data.get('username')
        username = f"@{html.escape(username_raw)}" if username_raw else "لا يوجد"
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

        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            types.InlineKeyboardButton(text="➕ إضافة رصيد", callback_data=f"admin_add_bal:{user_id}"),
            types.InlineKeyboardButton(text="➖ خصم رصيد", callback_data=f"admin_sub_bal:{user_id}")
        )
        keyboard.row(types.InlineKeyboardButton(text="📜 سجل الطلبات", callback_data=f"admin_history:{user_id}"))
        keyboard.row(types.InlineKeyboardButton(text=ban_txt, callback_data=ban_act))
        keyboard.row(types.InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="list_users:0"))

        if is_edit:
            # 🔥🔥 هنا التعديل السحري 🔥🔥
            if msg_or_call.photo:
                # إذا كانت الرسالة الحالية صورة، نعدل الوصف (Caption) فقط
                await msg_or_call.edit_caption(caption=txt, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            else:
                # إذا كانت نصاً، نعدل النص
                await msg_or_call.edit_text(text=txt, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await msg_or_call.answer(text=txt, reply_markup=keyboard.as_markup(), parse_mode="HTML")

    except Exception as e:
        print(f"ERROR in open_user_control: {e}")
        error_text = f"حدث خطأ في عرض البيانات: {str(e)}"
        try:
            if is_edit:
                if msg_or_call.photo:
                    await msg_or_call.edit_caption(caption=error_text, reply_markup=markup)
                else:
                    await msg_or_call.edit_text(error_text, reply_markup=markup)
            else:
                await msg_or_call.answer(error_text, reply_markup=markup)
        except:
            pass


@router.callback_query(F.data.startswith("admin_sub_bal:"))
async def ask_sub_bal(call: types.CallbackQuery, state: FSMContext):
    """Ask for amount to subtract."""
    uid = call.data.split(":")[1]
    await state.update_data(target_uid=uid, action="sub")
    back_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔙 إلغاء", callback_data=f"mang_usr:{uid}")
    ]])
    await smart_edit(call, f"➖ أدخل المبلغ لخصمه من المستخدم {uid} (بالدولار):", back_markup)
    await state.set_state(AdminState.waiting_for_amount_add)


@router.callback_query(F.data.startswith("admin_add_bal:"))
async def ask_add_bal(call: types.CallbackQuery, state: FSMContext):
    """Ask for amount to add."""
    uid = call.data.split(":")[1]
    await state.update_data(target_uid=uid, action="add")
    back_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔙 إلغاء", callback_data=f"mang_usr:{uid}")
    ]])
    await smart_edit(call, f"➕ أدخل المبلغ لإضافته للمستخدم {uid} (بالدولار):", back_markup)
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
                    f"💰 <b>تحديث الرصيد</b>\n━━━━━━━━━━━━\n"
                    f"➕ <b>المبلغ المضاف:</b> {amount:.2f} $\n"
                    f"💎 <b>رصيدك الحالي:</b> {new_bal:.2f} $"
                )
                await msg.bot.send_message(uid, user_msg, parse_mode="HTML")
            except: pass
        else:
            if database.deduct_balance(uid, amount):
                new_bal = database.get_balance(uid)
                res_txt = f"✅ <b>تم خصم {amount:.2f}$</b>"
                # Notify user
                try:
                    user_msg = (
                        f"💰 <b>تحديث الرصيد</b>\n━━━━━━━━━━━━\n"
                        f"➖ <b>المبلغ المخصوم:</b> {amount:.2f} $\n"
                        f"💎 <b>رصيدك الحالي:</b> {new_bal:.2f} $"
                    )
                    await msg.bot.send_message(uid, user_msg, parse_mode="HTML")
                except: pass
            else:
                res_txt = "❌ <b>فشل الخصم:</b> الرصيد غير كافٍ."

        await msg.answer(res_txt, parse_mode="HTML")
        await open_user_control(msg, uid, is_edit=False)
        await state.clear()
    except ValueError:
        await msg.answer("❌ الرجاء إدخال أرقام فقط!")
    except Exception as e:
        print(f"Error in exec_balance_change: {e}")
        await msg.answer("❌ حدث خطأ غير متوقع.")


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
                txt += f"{status_icon} <b>{o['product']['name']}</b>\n🔢 {o['id']} | 💰 {o['product']['price']}$\n----------------\n"

        uuids = api_manager.get_user_uuids(uid)
        if uuids:
            stats = api_manager.check_orders_status(uuids[:10])
            if stats:
                has_orders = True
                txt += "\n<b>🌐 طلبات API:</b>\n"
                for s in stats:
                    icon = "✅" if s.get('status') in ['completed', 'accept'] else "⏳"
                    txt += f"{icon} {s.get('product_name', 'Unknown')}\n💰 {s.get('price', 0)}$\n----------------\n"

        if not has_orders:
            txt += "📂 السجل فارغ"

        back_markup = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔙 رجوع", callback_data=f"mang_usr:{uid}")]])
        await smart_edit(call, txt, back_markup)
    except Exception as e:
        print(f"Error in user_history: {e}")
        await call.answer("خطأ في السجل", show_alert=True)