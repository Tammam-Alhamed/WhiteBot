from constants.orders import ORDER_SOURCE_API, ORDER_SOURCE_LOCAL


def format_admin_order_status(status: str) -> tuple:
    status_lower = (status or '').lower()
    if status_lower == 'completed':
        return "✅ مكتمل", "completed"
    if status_lower == 'pending':
        return "⏳ معلق", "pending"
    if status_lower == 'rejected':
        return "❌ مرفوض", "rejected"
    return f"❔ {status}", "unknown"


def format_api_admin_status(status: str) -> tuple:
    status_lower = (status or '').lower()
    if status_lower in ['completed', 'success', 'complete', 'accept']:
        return "✅ مكتمل", "completed"
    if status_lower in ['canceled', 'fail', 'refunded', 'rejected']:
        return "❌ مرفوض", "rejected"
    if status_lower in ['pending', 'processing', 'in progress']:
        return "⏳ معلق", "pending"
    return f"❔ {status}", "unknown"


def get_order_source_label(source: str) -> str:
    if source == ORDER_SOURCE_API:
        return "🌐 طلب عبر API"
    return "📱 طلب محلي"


def build_compact_admin_order_card(order: dict, is_api: bool = False) -> str:
    if is_api:
        order_id = order.get('order_id') or order.get('id', '---')
        service_name = order.get('product', {}).get('name', order.get('product_name', 'خدمة'))
        price = order.get('product', {}).get('price', order.get('price', 0))
        date = order.get('date', order.get('created_at', '---'))

        card = f"🆔\n<code>{order_id}</code>\n🌐\n"
        card += f"🛒 {service_name}\n"
        card += "📦 الكمية: 1\n"
        card += f"💰 {price}$\n"
        card += f"🕒 {date}\n"

        if order.get('code'):
            card += f"🔑 <code>{order['code']}</code>\n"
        return card

    order_id = order.get('id', '---')
    service_name = order.get('product', {}).get('name', 'منتج')
    qty = order.get('qty', 1)
    price = order.get('product', {}).get('price', 0)
    total = float(price) * int(qty)
    date = order.get('date', '---')

    card = f"🆔\n<code>{order_id}</code>\n🏠\n"
    card += f"🛒 {service_name}\n"
    card += f"📦 الكمية: {qty}\n"
    card += f"💰 {total}$\n"
    card += f"🕒 {date}\n"

    return card
