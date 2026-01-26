from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config

# ==================== قوائم المستخدم ====================

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 شحن ألعاب", callback_data="nav_games")],
        [InlineKeyboardButton(text="📱 تطبيقات وخدمات", callback_data="nav_apps")],
        [InlineKeyboardButton(text="💎 White للوساطة", callback_data="nav_white")],
        [
            InlineKeyboardButton(text="📦 طلباتي", callback_data="my_orders"),
            InlineKeyboardButton(text="💰 المحفظة", callback_data="deposit_menu")
        ]
    ])

def white_section_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="شراء USDT ₮", callback_data="w_deal:usdt")],
        [InlineKeyboardButton(text="شراء شام كاش دولار ($)", callback_data="w_deal:sham_usd")],
        [InlineKeyboardButton(text="شراء شام كاش سوري (SYP)", callback_data="w_deal:sham_syr")],
        [InlineKeyboardButton(text="🔙 رجوع للرئيسية", callback_data="home")]
    ])

# في ملف keyboards.py

# --- قوائم الإيداع الجديدة ---

def deposit_menu():
    """القائمة الرئيسية طرق الإيداع"""
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 رصيدي", callback_data="check_my_balance"),
    kb.button(text="🔴 سيريتيل كاش (Syriatel)", callback_data="dep_syriatel")
    kb.button(text="🟣 شام كاش (Sham Cash)", callback_data="dep_sham_menu") # قائمة فرعية
    kb.button(text="🟢 USDT (Crypto)", callback_data="dep_usdt_menu")     # قائمة فرعية
    kb.button(text="🔙 رجوع", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()

def sham_deposit_types():
    """أنواع إيداع شام كاش"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🇸🇾 شام كاش (ليرة سوري)", callback_data="dep_sham_syp")
    kb.button(text="🇺🇸 شام كاش (دولار)", callback_data="dep_sham_usd")
    kb.button(text="🔙 رجوع", callback_data="deposit_menu")
    kb.adjust(1)
    return kb.as_markup()

def usdt_deposit_types():
    """أنواع إيداع USDT"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔸 USDT (BEP20)", callback_data="dep_usdt_bep20")
    kb.button(text="📧 USDT (CoinEx Email)", callback_data="dep_usdt_coinex")
    kb.button(text="🔙 رجوع", callback_data="deposit_menu")
    kb.adjust(1)
    return kb.as_markup()

# دالة زر رجوع مخصص (موجودة سابقاً ولكن للتأكيد)
def back_btn(target):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data=target)]])



def contact_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تواصل واتساب 💬", url=config.ADMIN_WHATSAPP)],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="home")]
    ])

# ==================== أزرار التنقل والرجوع ====================

def back_btn(target="home"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data=target)]])

def cancel_or_back_btn(back_target="home"):
    """
    زر مزدوج: إلغاء العملية بالكامل، أو الرجوع خطوة للخلف
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع للخلف", callback_data=back_target)],
        [InlineKeyboardButton(text="❌ إلغاء والقائمة الرئيسية", callback_data="cancel_op")]
    ])

def cancel_btn():
    """زر إلغاء بسيط (احتياطي)"""
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء العملية", callback_data="cancel_op")]])

# ==================== القوائم الديناميكية (ألعاب وتطبيقات) ====================

def build_main_cats(mapping_dict, prefix):
    builder = InlineKeyboardBuilder()
    for name in mapping_dict.keys():
        builder.button(text=name, callback_data=f"{prefix}:{name}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 رجوع للرئيسية", callback_data="home"))
    return builder.as_markup()

def build_sub_cats(cats_list, parent_key):
    builder = InlineKeyboardBuilder()
    for short_id, full_name in cats_list:
        # نمرر: open:cat_id:parent_key
        builder.button(text=full_name, callback_data=f"open:{short_id}:{parent_key}")
    builder.adjust(1)
    return builder 

def add_back_button(builder, target):
    builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data=target))
    return builder.as_markup()

def build_products(products, back_callback):
    builder = InlineKeyboardBuilder()
    for p in products:
        price_text = p.get('formatted_price', f"{p['price']}$")
        text = f"{p['name']} | {price_text}"
        builder.button(text=text, callback_data=f"buy:{p['id']}")
    
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data=back_callback))
    return builder.as_markup()

# ==================== 👑 لوحة الأدمن (الجزء المفقود) ====================

# في ملف keyboards.py

def admin_dashboard():
    kb = InlineKeyboardBuilder()

    # الصف الأول: العمليات الأساسية
    kb.button(text="👥 إدارة المستخدمين", callback_data="admin_users")
    kb.button(text="📦 إدارة الطلبات", callback_data="admin_orders")

    # الصف الثاني: المال والإيداع (جديد + قديم)
    kb.button(text="💰 طلبات الإيداع المعلقة", callback_data="admin_deposits")
    kb.button(text="💵 تعديل سعر الصرف", callback_data="admin_edit_rate")  # ✅ تم استرجاعه

    # الصف الثالث: إدارة الأسعار والأدوات
    kb.button(text="🏷️ إدارة نسبة الربح", callback_data="admin_edit_margin")  # ✅ تم استرجاعه
    kb.button(text="📢 إرسال رسالة للكل", callback_data="admin_broadcast")

    # الصف الرابع: النظام
    kb.button(text="🛠 وضع الصيانة", callback_data="admin_maintenance")
    kb.button(text="🔙 خروج", callback_data="close_admin")

    kb.adjust(2, 1, 2, 2)  # ترتيب الأزرار بشكل جميل (2 بجانب بعض)
    return kb.as_markup()

def user_manage_menu(user_id, is_banned):
    ban_text = "🟢 فك الحظر" if is_banned else "🔴 حظر المستخدم"
    ban_call = f"admin_unban:{user_id}" if is_banned else f"admin_ban:{user_id}"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة رصيد", callback_data=f"admin_add_bal:{user_id}")],
        [InlineKeyboardButton(text="➖ خصم رصيد", callback_data=f"admin_sub_bal:{user_id}")],
        [InlineKeyboardButton(text="📜 كشف السجل", callback_data=f"admin_history:{user_id}")],
        [InlineKeyboardButton(text=ban_text, callback_data=ban_call)],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_users_menu")]
    ])

def back_to_admin():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 للأدمن", callback_data="admin_home")]])