"""Admin handlers router."""
from aiogram import Router

# Import all admin handlers
from . import dashboard, users, orders, deposits, settings

# Create main admin router
router = Router(name="admin")

# Include all sub-routers
router.include_router(dashboard.router)
router.include_router(users.router)
router.include_router(orders.router)
router.include_router(deposits.router)
router.include_router(settings.router)
