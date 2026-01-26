"""Shop and deposit FSM states."""
from aiogram.fsm.state import State, StatesGroup


class ShopState(StatesGroup):
    """States for shop operations."""
    waiting_for_quantity = State()
    waiting_for_input = State()


class DepositState(StatesGroup):
    """States for deposit operations."""
    waiting_for_amount = State()  # Step 1: Ask for amount first
    waiting_for_txn_id = State()  # Step 2: Ask for transaction number
    waiting_for_proof = State()   # Step 3: Ask for proof image (optional)
