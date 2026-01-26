"""Admin settings management handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.settings as settings
import services.api_manager as api_manager
import data.mappings as mappings
import data.keyboards as kb
from bot.utils.helpers import smart_edit
from states.admin import AdminState

router = Router()


@router.callback_query(F.data == "admin_edit_rate")
async def ask_new_rate(call: types.CallbackQuery, state: FSMContext):
    """Ask for new exchange rate."""
    current_rate = settings.get_setting("exchange_rate")
    await smart_edit(
        call,
        f"💵 <b>سعر الصرف الحالي:</b> {current_rate} ل.س\n\nأرسل السعر الجديد الآن (أرقام فقط):",
        kb.back_to_admin()
    )
    await state.set_state(AdminState.waiting_for_rate)


@router.message(AdminState.waiting_for_rate)
async def set_new_rate(msg: types.Message, state: FSMContext):
    """Set new exchange rate."""
    try:
        new_rate = float(msg.text)
        settings.update_setting("exchange_rate", new_rate)

        await msg.answer(
            f"✅ تم تحديث سعر الصرف إلى: <b>{new_rate} ل.س</b>",
            reply_markup=kb.admin_dashboard(),
            parse_mode="HTML"
        )
        await state.clear()
    except:
        await msg.answer("❌ يرجى إرسال أرقام فقط!")


@router.callback_query(F.data == "admin_edit_margin")
async def show_margins_menu(call: types.CallbackQuery, state: FSMContext):
    """Show margins management menu."""
    await state.clear()
    keyboard = InlineKeyboardBuilder()

    def to_perc(val):
        return round((val - 1) * 100)

    current_default = settings.get_margin_for_category("default")
    keyboard.button(
        text=f"🌐 الربح العام ({to_perc(current_default)}%)",
        callback_data="set_margin:default"
    )

    def add_section(title, mapping_dict):
        keyboard.button(text=f"━━ {title} ━━", callback_data="ignore")
        for cat in mapping_dict.keys():
            m = settings.get_margin_for_category(cat)
            keyboard.button(text=f"{cat} ({to_perc(m)}%)", callback_data=f"set_margin:{cat}")

    add_section("🎮 الألعاب", mappings.GAMES_MAP)
    add_section("📱 التطبيقات والخدمات", mappings.APPS_MAP)

    keyboard.button(text="🔙 رجوع", callback_data="admin_home")
    keyboard.adjust(1)

    await smart_edit(
        call,
        "🏷️ <b>إدارة نسب الربح:</b>\nتم تحديث الأقسام بناءً على الملف الجديد.",
        keyboard.as_markup()
    )


@router.callback_query(F.data.startswith("set_margin:"))
async def ask_margin_value(call: types.CallbackQuery, state: FSMContext):
    """Ask for margin value."""
    target_cat = call.data.split(":")[1]

    await state.update_data(target_cat=target_cat)

    cat_name = "الكل (عام)" if target_cat == "default" else target_cat

    txt = (
        f"🏷️ <b>تعديل نسبة ربح: {cat_name}</b>\n\n"
        "أرسل نسبة الربح التي تريدها (أرقام فقط):\n"
        "• اكتب <b>10</b> لربح 10%\n"
        "• اكتب <b>20</b> لربح 20%\n"
        "• اكتب <b>5</b> لربح 5%\n"
        "• اكتب <b>0</b> لبيع المنتج بسعر التكلفة"
    )
    await smart_edit(call, txt, kb.back_btn("admin_edit_margin"))

    await state.set_state(AdminState.waiting_for_margin)


@router.message(AdminState.waiting_for_margin)
async def save_new_margin(msg: types.Message, state: FSMContext):
    """Save new margin value."""
    try:
        user_input = float(msg.text)
        if user_input < 0:
            return await msg.answer("❌ لا يمكن أن تكون النسبة سالبة!")

    except:
        return await msg.answer("❌ أرقام فقط (مثال: 10 أو 20)!")

    data = await state.get_data()
    cat = data['target_cat']

    multiplier = 1 + (user_input / 100)

    settings.set_category_margin(cat, multiplier)

    await msg.answer("🔄 جاري تحديث الأسعار في المتجر... لحظة من فضلك.")

    try:
        api_manager.refresh_data()
    except Exception as e:
        print(f"Error refreshing data: {e}")

    await msg.answer(
        f"✅ <b>تم التحديث بنجاح!</b>\n"
        f"تم تغيير نسبة ربح <b>{cat}</b> إلى: <b>{user_input}%</b>\n"
        f"الأسعار الجديدة ظهرت الآن في المتجر.",
        reply_markup=kb.admin_dashboard(),
        parse_mode="HTML"
    )
    await state.clear()
