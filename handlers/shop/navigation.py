"""Shop navigation handlers."""
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext  # ✅ إضافة هامة

import data.mappings as mappings
import data.keyboards as kb
import services.api_manager as api_manager
import services.settings as settings
from bot.utils.helpers import smart_edit

router = Router()

@router.callback_query(F.data.startswith("nav_"))
async def navigation(call: types.CallbackQuery, state: FSMContext):
    """Handle navigation to games/apps/white sections."""
    await state.clear()  # ✅ تنظيف الحالة عند التنقل

    key = call.data.split("_")[1]

    if key == "white":
        txt = "💎 <b>قسم White للوساطة</b>\n━━━━━━━━━━━━\nمتوفر الآن بأفضل الأسعار.\n👇 اختر الخدمة:"
        media = InputMediaPhoto(media=FSInputFile("assets/white.jpg"), caption=txt, parse_mode="HTML")
        try:
            await call.message.edit_media(media=media, reply_markup=kb.white_section_menu())
        except:
            # في حال فشل تعديل الميديا (مثلاً الرسالة قديمة)، نرسل رسالة جديدة
            await call.message.delete()
            await call.message.answer_photo(FSInputFile("assets/white.jpg"), caption=txt, reply_markup=kb.white_section_menu())
        return

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

    await smart_edit(call, f"📂 قسم {key}:", builder.as_markup())


@router.callback_query(F.data.contains("srch_"))
async def subcats(call: types.CallbackQuery):
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


# ==================== ✅Handlers للإلغاء والعودة ====================

@router.callback_query(F.data == "home")
async def go_home(call: types.CallbackQuery, state: FSMContext):
    """العودة للرئيسية مع مسح الحالة"""
    await state.clear()

    # محاولة إرجاع الصورة الأصلية
    try:
        media = InputMediaPhoto(media=FSInputFile("assets/store.jpg"), caption="🏠 <b>القائمة الرئيسية:</b>", parse_mode="HTML")
        await call.message.edit_media(media=media, reply_markup=kb.main_menu())
    except:
        # إذا لم نكن في وضع الميديا، نعدل النص فقط أو نرسل جديداً
        try:
            await call.message.delete()
        except: pass
        await call.message.answer_photo(FSInputFile("assets/store.jpg"), caption="🏠 <b>القائمة الرئيسية:</b>", reply_markup=kb.main_menu())


@router.callback_query(F.data == "cancel_op")
async def cancel_operation(call: types.CallbackQuery, state: FSMContext):
    """إلغاء أي عملية جارية"""
    await state.clear()
    await call.answer("❌ تم الإلغاء")
    await go_home(call, state)