ORDER_SOURCE_LOCAL = "LOCAL"
ORDER_SOURCE_API = "API"


def norm_order_status(s: str) -> str:
    s = (s or '').lower()
    if s in ('pending', 'processing', 'in progress'):
        return 'pending'
    if s in ('completed', 'complete', 'success', 'accept'):
        return 'completed'
    if s in ('rejected', 'canceled', 'fail', 'refunded'):
        return 'rejected'
    return 'unknown'


ADMIN_STATUS_LABELS = {
    'pending': '⏳ معلّقة',
    'completed': '✅ مكتملة',
    'rejected': '❌ مرفوضة',
}
