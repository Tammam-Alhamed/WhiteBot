"""Subscription middleware for channel verification."""
from aiogram import BaseMiddleware, types
from typing import Callable, Dict, Any, Awaitable
import config
import services.database as database


class StrictSubscriptionMiddleware(BaseMiddleware):
    """Middleware to enforce channel subscription."""
    
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        bot = data.get('bot')
        
        # 1. Admin bypass (ديناميكي: من الكونفج + قاعدة البيانات)
        if user and database.is_user_admin(user.id):
            return await handler(event, data)

        # 2. Check subscription via Telegram API
        try:
            member = await bot.get_chat_member(chat_id=config.CHANNEL_ID, user_id=user.id)
            
            # User is not subscribed
            if member.status in ['left', 'kicked', 'restricted']:
                markup = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="📢 اشترك في القناة للاستخدام", url=config.FORCE_SUB_CHANNEL_URL)],
                    [types.InlineKeyboardButton(text="✅ تم الاشتراك", callback_data="check_sub")]
                ])
                
                txt_msg = (
                    f"⛔ <b>عذراً {user.first_name}</b>\n\n"
                    "⚠️ <b>يجب عليك الاشتراك في القناة لاستخدام البوت.</b>\n\n"
                    "نحن نتحقق من الاشتراك بشكل مستمر.\n"
                    "اشترك الآن ثم اضغط زر التحقق 👇"
                )

                if isinstance(event, types.Message):
                    await event.answer(txt_msg, reply_markup=markup, parse_mode="HTML")
                elif isinstance(event, types.CallbackQuery):
                    if event.data == "check_sub":
                        await event.answer("❌ ما زلت غير مشترك! انضم للقناة أولاً.", show_alert=True)
                    else:
                        await event.answer("⚠️ اشترك في القناة أولاً!", show_alert=True)
                        try:
                            await event.message.answer(txt_msg, reply_markup=markup, parse_mode="HTML")
                        except:
                            pass
                
                return  # Stop execution

        except Exception as e:
            print(f"⚠️ Subscription Check Error: {e}")

        # 3. User is subscribed, allow passage
        return await handler(event, data)
