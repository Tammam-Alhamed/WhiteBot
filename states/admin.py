"""Admin FSM states."""
from aiogram.fsm.state import State, StatesGroup


class AdminState(StatesGroup):
    """States for admin operations."""
    waiting_for_rate = State()        # لسعر الصرف
    waiting_for_margin = State()      # لنسبة الربح
    waiting_for_commission = State()  # لعمولة الإيداع
    waiting_for_user_id = State()     # للبحث عن مستخدم
    waiting_for_amount_add = State()  # لإضافة الرصيد
    waiting_for_broadcast_msg = State() # للإرسال الجماعي
    waiting_for_category_rename = State()  # لإعادة تسمية الفئة
