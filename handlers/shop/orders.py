"""Order history handlers."""
from aiogram import Router, types, F
import services.database as database
import services.api_manager as api_manager
import data.keyboards as kb
from bot.utils.helpers import smart_edit, format_price

router = Router()


@router.callback_query(F.data == "my_orders")
async def my_orders(call: types.CallbackQuery):
    """Show user's order history."""
    uid = call.from_user.id
    txt = "📦 <b>سجل طلباتك:</b>\n━━━━━━━━━━━━\n"
    has_orders = False
    
    local_orders = database.get_user_local_orders(uid)
    if local_orders:
        has_orders = True
        for o in local_orders:
            total_price = float(o['product']['price']) * int(o['qty'])
            price_str = format_price(total_price)
            if o['status'] == 'completed':
                icon = "✅"
                status_txt = "مكتمل"
            else:
                icon = "⏳"
                status_txt = "قيد التنفيذ"
            txt += (
                f"{icon} <b>{o['product']['name']}</b>\n"
                f"🔢 رقم: <code>{o['id']}</code>\n"
                f"📊 الحالة: {status_txt}\n"
                f"💰 السعر: {price_str}\n"
                f"----------------\n"
            )
    
    uuids = api_manager.get_user_uuids(uid)
    if uuids:
        stats = api_manager.check_orders_status(uuids)
        if stats:
            has_orders = True
            for s in stats:
                icon = "✅" if s.get('status') in ['completed', 'accept'] else "❌" if s.get('status') in ['canceled', 'reject'] else "⏳"
                price = format_price(s.get('price', 0))
                txt += f"{icon} {s.get('product_name')}\n💰 {price}\n----------------\n"
    
    if not has_orders:
        txt = "📂 السجل فارغ"
    await smart_edit(call, txt, kb.back_btn("home"))
