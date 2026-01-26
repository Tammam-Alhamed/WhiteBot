"""Shop and deposit FSM states."""
from aiogram.fsm.state import State, StatesGroup


class ShopState(StatesGroup):
    """States for shop operations."""
    waiting_for_quantity = State()
    waiting_for_input = State()


class DepositState(StatesGroup):
    """States for deposit operations."""
    waiting_for_txn_id = State()
    waiting_for_amount = State()
