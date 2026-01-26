"""Shop navigation handlers."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import data.mappings as mappings
import data.keyboards as kb
import services.api_manager as api_manager
import services.settings as settings
from bot.utils.helpers import smart_edit

router = Router()


@router.callback_query(F.data.startswith("nav_"))
async def navigation(call: types.CallbackQuery):
    """Handle navigation to games/apps/white sections."""
    key = call.data.split("_")[1]
    if key == "white":
        txt = "💎 <b>قسم White للوساطة</b>\n━━━━━━━━━━━━\nمتوفر الآن بأفضل الأسعار.\n👇 اختر الخدمة:"
        return await smart_edit(call, txt, kb.white_section_menu())
    
    mapping = mappings.GAMES_MAP if key == "games" else mappings.APPS_MAP
    prefix = "srch_g" if key == "games" else "srch_a"
    
    # Build mapping with custom names but keep original keys for callback
    display_mapping = {}
    for cat_key in mapping.keys():
        display_name = settings.get_category_name(cat_key)
        # Store original key with display name
        display_mapping[display_name] = (cat_key, mapping[cat_key])
    
    # Create custom keyboard builder
    builder = InlineKeyboardBuilder()
    for display_name, (original_key, keywords) in display_mapping.items():
        builder.button(text=display_name, callback_data=f"{prefix}:{original_key}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 رجوع للرئيسية", callback_data="home"))
    
    await smart_edit(call, f"📂 قسم {key}:", builder.as_markup())


@router.callback_query(F.data.contains("srch_"))
async def subcats(call: types.CallbackQuery):
    """Handle subcategory search."""
    data_parts = call.data.split(":")
    prefix = data_parts[0]
    key = data_parts[1]
    
    kws = mappings.GAMES_MAP.get(key, []) if prefix == "srch_g" else mappings.APPS_MAP.get(key, [])
    res = api_manager.search_subcategories(kws)
    if not res:
        return await call.answer("غير متوفر حالياً!", show_alert=True)
    
    back_to = "nav_games" if prefix == "srch_g" else "nav_apps"
    builder = kb.build_sub_cats(res, key)
    markup = kb.add_back_button(builder, back_to)
    await smart_edit(call, f"📂 <b>{key}</b> - اختر الفئة:", markup)
