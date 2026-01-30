"""Shop orders handlers."""
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.database as database
import services.api_manager as api_manager
import data.keyboards as kb
from bot.utils.helpers import smart_edit
import asyncio

router = Router()

@router.callback_query(F.data == "my_orders")
async def show_my_orders(call: types.CallbackQuery):
    """Show user's order history (Local + API)."""
    user_id = call.from_user.id

    # رسالة انتظار لأن العملية قد تأخذ ثانية
    await call.answer("⏳ جاري جلب سجل طلباتك...")

    # 1. جلب الطلبات المحلية (من قاعدة البيانات)
    # نستخدم to_thread لتجنب تجميد البوت
    local_orders = await asyncio.to_thread(database.get_user_local_orders, user_id)

    # 2. جلب طلبات API (من الموقع)
    api_uuids = await asyncio.to_thread(api_manager.get_user_uuids, user_id)
    api_stats = []
    if api_uuids:
        # فحص آخر 10 طلبات فقط لتسريع العرض
        api_stats = await asyncio.to_thread(api_manager.check_orders_status, api_uuids[:10])

    if not local_orders and not api_stats:
        return await smart_edit(call, "📂 <b>سجل طلباتك فارغ.</b>", kb.back_btn("home"))

    # إعداد الرسالة
    txt = "📦 <b>سجل طلباتك (آخر 10):</b>\n━━━━━━━━━━━━\n"

    # عرض الطلبات المحلية (الأحدث أولاً)
    # نقوم بقلب القائمة لعرض الجديد في الأعلى
    for order in reversed(local_orders[-10:]):
        status = order['status']
        icon = "✅" if status == 'completed' else "⏳" if status == 'pending' else "❌"

        p_name = order.get('product', {}).get('name', 'منتج')
        price = order.get('product', {}).get('price', 0)

        txt += f"{icon} <b>{p_name}</b>\n"
        txt += f"🔢 رقم: <code>{order['id']}</code>\n"
        txt += f"💰 السعر: {price}$\n"

        if status == 'pending':
            txt += f"📊 الحالة: <b>قيد المعالجة</b>\n"
        elif status == 'completed':
            txt += f"📊 الحالة: <b>مكتمل</b>\n"
        else:
            txt += f"📊 الحالة: <b>مرفوض/ملغي</b>\n"

        txt += "----------------\n"

    # عرض طلبات API
    for stat in api_stats:
        status = stat.get('status', 'Unknown')

        # تحديد الأيقونة حسب حالة الموقع
        if status in ['completed', 'Success', 'Complete']:
            icon = "✅"
            status_ar = "مكتمل"
        elif status in ['Canceled', 'Fail', 'Refunded', 'Rejected']:
            icon = "❌"
            status_ar = "مرفوض"
        elif status in ['Pending', 'Processing', 'In progress']:
            icon = "⏳"
            status_ar = "قيد التنفيذ"
        else:
            icon = "❔"
            status_ar = status

        p_name = stat.get('product_name', 'خدمة الكترونية')
        price = stat.get('price', 0)

        txt += f"{icon} <b>{p_name}</b>\n"
        txt += f"💰 السعر: {price}$\n"
        txt += f"📊 الحالة: <b>{status_ar}</b>\n"

        # عرض الكود أو الملاحظة إذا وجدت
        codes = stat.get('replay_api')
        code_txt = f"{codes[0]}" if (codes and isinstance(codes, list) and len(codes)>0) else ""
        txt += f"| 🔑 <code>{code_txt}</code>\n"
        txt += "----------------\n"

    # زر تحديث وتواصل
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔄 تحديث السجل", callback_data="my_orders")
    keyboard.button(text="🔙 القائمة الرئيسية", callback_data="home")
    keyboard.adjust(1)

    await smart_edit(call, txt, keyboard.as_markup())