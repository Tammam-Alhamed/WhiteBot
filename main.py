import asyncio
import logging
from aiogram import Bot, Dispatcher
import config
from bot.middlewares.maintenance import MaintenanceMiddleware
from bot.middlewares.subscription import StrictSubscriptionMiddleware

# Import routers from new structure
from handlers.common import router as common_router
from handlers.shop import router as shop_router
from handlers.admin import router as admin_router

# Setup logging
logging.basicConfig(level=logging.INFO)

async def main():
    # 1. Initialize bot
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # 2. Register routers (common first, then shop, then admin)
    dp.include_router(common_router)
    dp.include_router(shop_router)
    dp.include_router(admin_router)

    # Apply Maintenance middleware
    dp.message.middleware(MaintenanceMiddleware())
    dp.callback_query.middleware(MaintenanceMiddleware())

    # Apply subscription middleware
    dp.message.middleware(StrictSubscriptionMiddleware())
    dp.callback_query.middleware(StrictSubscriptionMiddleware())

    # 3. Delete webhook and start polling
    print("🚀 Bot is starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped.")
