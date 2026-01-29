"""Admin FSM states."""
from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    """States for admin operations."""
    waiting_for_rate = State()        # لسعر الصرف
    waiting_for_margin = State()      # لنسبة الربح
    waiting_for_commission = State()  # لعمولة الإيداع
    waiting_for_user_id = State()     # للبحث عن مستخدم

    # ✅ الحالات الجديدة للإضافة والخصم
    waiting_for_user_search = State()
    waiting_for_balance_amount = State()      # لإضافة الرصيد
    waiting_for_sub_balance_amount = State()  # لخصم الرصيد (الجديدة)

    waiting_for_amount_add = State()  # (لم تعد مستخدمة لكن نتركها للاحتياط)
    waiting_for_broadcast_msg = State() # للإرسال الجماعي
    waiting_for_category_rename = State()  # لإعادة تسمية الفئة