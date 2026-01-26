"""Shop handlers router."""
from aiogram import Router
from bot.middlewares.maintenance import MaintenanceMiddleware
from bot.middlewares.subscription import StrictSubscriptionMiddleware

# Import all shop handlers
from . import navigation, products, orders, deposit, white

# Create main shop router
router = Router(name="shop")



# Include all sub-routers
router.include_router(navigation.router)
router.include_router(products.router)
router.include_router(orders.router)
router.include_router(deposit.router)
router.include_router(white.router)
