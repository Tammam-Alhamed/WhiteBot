"""Common handlers: start, home, cancel."""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import config
import services.database as database
import data.keyboards as kb

router = Router()


@router.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    """Handle /start command."""
    uid = msg.from_user.id
    
    # تحديث بيانات المستخدم
    database.update_user_info(uid, msg.from_user.first_name, msg.from_user.username)
    
    if database.is_banned(uid):
        return await msg.answer(config.MSG_BANNED, parse_mode="HTML")
    
    database.ensure_user_exists(uid)
    await state.clear()
    await msg.answer_photo(
        config.WELCOME_PHOTO,
        caption=config.WELCOME_MESSAGE,
        reply_markup=kb.main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "home")
async def home(call: types.CallbackQuery, state: FSMContext):
    """Handle home button."""
    await state.clear()
    await call.message.delete()
    await call.message.answer_photo(
        config.WELCOME_PHOTO,
        caption="القائمة الرئيسية:",
        reply_markup=kb.main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel_op")
async def cancel_operation(call: types.CallbackQuery, state: FSMContext):
    """Cancel current operation."""
    await call.answer("تم الإلغاء ❌")
    await state.clear()
    await call.message.delete()
    await call.message.answer("❌ <b>تم الإلغاء.</b>", reply_markup=kb.main_menu(), parse_mode="HTML")
