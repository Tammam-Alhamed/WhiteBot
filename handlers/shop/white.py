"""White section handlers."""
from aiogram import Router, types, F
import data.keyboards as kb
from bot.utils.helpers import smart_edit

router = Router()


@router.callback_query(F.data.startswith("w_deal:"))
async def white_deals(call: types.CallbackQuery):
    """Handle white section deals."""
    await smart_edit(call, "✅ <b>لتثبيت الطلب:</b>\nيرجى التواصل مع الإدارة", kb.contact_admin())


@router.callback_query(F.data == "check_sub")
async def check_subscription_btn(call: types.CallbackQuery):
    """Handle subscription check button."""
    await call.message.delete()
    await call.message.answer(
        "✅ <b>شكراً لاشتراكك!</b>\nيمكنك استخدام البوت الآن 🚀",
        reply_markup=kb.main_menu(),
        parse_mode="HTML"
    )
