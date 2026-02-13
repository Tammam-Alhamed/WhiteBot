from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, InputMediaPhoto  # 👈 (مهم) استدعاء InputMediaPhoto
from contextlib import suppress
import services.database as database
import data.keyboards as kb

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    database.register_user(user.id, user.first_name, user.username)

    if database.is_user_admin(user.id):
        await message.answer(
            "اختر الوضع:",
            reply_markup=kb.start_mode_menu()
        )
        return

    WELCOME_MESSAGE = f"""
🤍 مرحبًا بك{user.first_name} في متجرنا الرسمي!
🎮 متخصصون في:
⚡️ شحن الألعاب
⚡️ الخدمات الإلكترونية
⚡️ الدفع الإلكتروني
🔸 نتمنى لك تجربة ممتعة وموفّقة!
    """

    try:
        photo = FSInputFile("assets/store.jpg")
        await message.answer_photo(
            photo=photo,
            caption=WELCOME_MESSAGE,
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )
    except Exception:
        await message.answer(WELCOME_MESSAGE, reply_markup=kb.main_menu(), parse_mode="HTML")


@router.callback_query(F.data == "start_user_mode")
async def start_user_mode(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await call.message.answer("🏠 القائمة الرئيسية:", reply_markup=kb.main_menu())


@router.callback_query(F.data == "start_admin_mode")
async def start_admin_mode(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)
    await call.answer()
    await call.message.answer("👑 لوحة الإدارة:", reply_markup=kb.admin_dashboard())


@router.callback_query(F.data == "home")
async def back_to_home(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user = call.from_user

    WELCOME_MESSAGE = f"""
🤍 مرحبًا بك{user.first_name} في متجرنا الرسمي!
🎮 متخصصون في:
⚡️ شحن الألعاب
⚡️ الخدمات الإلكترونية
⚡️ الدفع الإلكتروني
🔸 نتمنى لك تجربة ممتعة وموفّقة!
"""

    # ✅ الحل السحري: نستخدم edit_media لنغير الصورة لنوع store.jpg في نفس المكان
    try:
        media = InputMediaPhoto(
            media=FSInputFile("assets/store.jpg"),
            caption=WELCOME_MESSAGE,
            parse_mode="HTML"
        )
        await call.message.edit_media(media=media, reply_markup=kb.main_menu())
    except Exception:
        # احتياط: لو كانت الرسالة السابقة نصية فقط ولا يمكن تعديل الميديا
        with suppress(Exception):
            await call.message.delete()
        photo = FSInputFile("assets/store.jpg")
        await call.message.answer_photo(photo=photo, caption=WELCOME_MESSAGE, reply_markup=kb.main_menu(),
                                        parse_mode="HTML")
