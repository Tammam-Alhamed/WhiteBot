"""Helper utilities for the bot."""
from aiogram import types
from aiogram.types import CallbackQuery, Message
import services.settings as settings
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest

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
    """
    Smart edit that handles both text and photo messages.
    Prevents 'Message is not modified' errors on double clicks.
    """
    try:
        # 1. نحاول التعديل أولاً
        if call.message.photo:
            await call.message.edit_caption(caption=text, reply_markup=markup, parse_mode="HTML")
        else:
            await call.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")

    except TelegramBadRequest as e:
        # 2. إذا كان الخطأ "الرسالة لم تتغير" (بسبب ضغطة مزدوجة)، نتجاهله
        if "message is not modified" in str(e):
            return

        # 3. إذا كان الخطأ آخر (مثلاً تحويل صورة لنص)، نحذف ونرسل جديد
        # ولكن نتأكد من حذف القديمة أولاً لكي لا تتكرر
        with suppress(Exception):
            await call.message.delete()
        await call.message.answer(text, reply_markup=markup, parse_mode="HTML")

    except Exception:
        # 4. أي خطأ غير متوقع، نحذف ونرسل
        with suppress(Exception):
            await call.message.delete()
        await call.message.answer(text, reply_markup=markup, parse_mode="HTML")