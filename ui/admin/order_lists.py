from constants.orders import ADMIN_STATUS_LABELS
from ui.admin.order_cards import build_compact_admin_order_card


def render_admin_orders_source_section(title: str, orders: list, is_api: bool) -> str:
    txt = f"🌐 <b>{title}</b>\n"
    txt += "─────────────────────\n"

    if not orders:
        if is_api:
            txt += "لا يوجد طلبات API في هذه الحالة\n"
        else:
            txt += "لا يوجد طلبات محلية في هذه الحالة\n"
        txt += "\n"
        return txt

    for i, o in enumerate(orders):
        txt += build_compact_admin_order_card(o, is_api=is_api)
        if i < len(orders) - 1:
            txt += "••••••••••••••••\n"

    txt += "\n"
    return txt


def render_admin_user_orders_all_statuses(
    user_id: str,
    buckets_api: dict,
    buckets_local: dict,
) -> str:
    txt = f"📜 <b>سجل طلبات المستخدم {user_id}:</b>\n"
    txt += "═══════════════════════\n\n"

    for status_key in ('pending', 'completed', 'rejected'):
        status_label = ADMIN_STATUS_LABELS.get(status_key, status_key)
        txt += f"📋 <b>الطلبات {status_label}</b>\n"
        txt += "═══════════════════════\n\n"

        txt += render_admin_orders_source_section("طلبات عبر API", buckets_api.get(status_key, []), True)
        txt += render_admin_orders_source_section("طلبات محلية", buckets_local.get(status_key, []), False)

    return txt
