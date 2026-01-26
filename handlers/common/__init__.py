"""Common handlers router."""
from aiogram import Router
from . import start

# Create common router
router = Router(name="common")

# Include common handlers
router.include_router(start.router)
