"""Maintenance mode middleware."""
from aiogram import BaseMiddleware, types
from typing import Callable, Dict, Any, Awaitable
import config
import services.settings as settings
import services.database as database


class MaintenanceMiddleware(BaseMiddleware):
    """Middleware to block non-admin users during maintenance."""
    
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        
        # If maintenance is enabled and user is not admin (ديناميكي: من الكونفج + قاعدة البيانات)
        if user and settings.get_setting("maintenance_mode") and not database.is_user_admin(user.id):
            if isinstance(event, types.CallbackQuery):
                await event.answer("🛠 نعتذر، المتجر تحت الصيانة حالياً.", show_alert=True)
            elif isinstance(event, types.Message):
                await event.answer(config.MSG_MAINTENANCE, parse_mode="HTML")
            return None  # Stop execution
        
        # Allow passage
        return await handler(event, data)
