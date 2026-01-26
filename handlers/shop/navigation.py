"""Shop navigation handlers."""
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, FSInputFile, InputMediaPhoto # 👈 أضفنا InputMediaPhoto
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

    # ✅ قسم الوساطة: يغير الصورة إلى white.jpg
    if key == "white":
        txt = "💎 <b>قسم White للوساطة</b>\n━━━━━━━━━━━━\nمتوفر الآن بأفضل الأسعار.\n👇 اختر الخدمة:"

        media = InputMediaPhoto(
            media=FSInputFile("assets/white.jpg"),
            caption=txt,
            parse_mode="HTML"
        )
        # نستخدم edit_media بدلاً من الحذف والإرسال
        await call.message.edit_media(media=media, reply_markup=kb.white_section_menu())
        return

    # ✅ باقي الأقسام (ألعاب وتطبيقات): تبقى الصورة كما هي (store.jpg)
    mapping = mappings.GAMES_MAP if key == "games" else mappings.APPS_MAP
    prefix = "srch_g" if key == "games" else "srch_a"

    display_mapping = {}
    for cat_key in mapping.keys():
        display_name = settings.get_category_name(cat_key)
        display_mapping[display_name] = (cat_key, mapping[cat_key])

    builder = InlineKeyboardBuilder()
    for display_name, (original_key, keywords) in display_mapping.items():
        builder.button(text=display_name, callback_data=f"{prefix}:{original_key}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 رجوع للرئيسية", callback_data="home"))

    # هنا نستخدم smart_edit العادية، لأننا قادمون من الرئيسية (store.jpg)
    # فلا داعي لتغيير الصورة، فقط نغير النص والأزرار
    await smart_edit(call, f"📂 قسم {key}:", builder.as_markup())


@router.callback_query(F.data.contains("srch_"))
async def subcats(call: types.CallbackQuery):
    # ... (باقي الملف كما هو بدون تغيير) ...
    # فقط تأكد أنك نسخت الجزء العلوي بشكل صحيح
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