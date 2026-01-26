"""Helper utilities for the bot."""
from aiogram import types
from aiogram.types import CallbackQuery, Message
import services.settings as settings


def format_price(usd):
    """Format USD price to SYP."""
    try:
        if usd is None:
            return "0"
        rate = settings.get_setting("exchange_rate")
        val = float(usd)
        syp = val * rate
        return f"{int(syp):,} ل.س"
    except:
        return "غير متوفر"


async def smart_edit(call: CallbackQuery, text: str, markup):
    """Smart edit that handles both text and photo messages."""
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text, reply_markup=markup, parse_mode="HTML")
        else:
            await call.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=markup, parse_mode="HTML")
