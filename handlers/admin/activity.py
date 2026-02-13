"""معالجات نشاط الأدمن (يومي/أسبوعي/شهري)."""
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import services.database as database
import data.keyboards as kb
from bot.utils.helpers import smart_edit

router = Router()


def _date_prefix(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _parse_any_date_prefix(s: str) -> str | None:
    if not s:
        return None
    # deposits.date / orders.date are stored like "YYYY-MM-DD ..."
    try:
        return str(s).split()[0]
    except Exception:
        return None


def _sum_local_orders_usd(orders: list[dict]) -> float:
    total = 0.0
    for o in orders:
        try:
            qty = int(o.get("qty", 1) or 1)
            price_unit = float((o.get("product") or {}).get("price", 0) or 0)
            total += price_unit * qty
        except Exception:
            continue
    return float(total)


@router.callback_query(F.data == "admin_activity")
async def activity_menu(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    k = InlineKeyboardBuilder()
    k.button(text="📅 النشاط اليومي", callback_data="admin_activity_daily")
    k.button(text="📆 النشاط الأسبوعي", callback_data="admin_activity_weekly")
    k.button(text="🗓 النشاط الشهري", callback_data="admin_activity_monthly")
    k.button(text="🔙 رجوع", callback_data="admin_home")
    k.adjust(1)

    await smart_edit(call, "📊 <b>النشاط</b>\nاختر القسم:", k.as_markup())


@router.callback_query(F.data == "admin_activity_daily")
async def activity_daily(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    today = _date_prefix(datetime.now())

    deps = [d for d in database.get_all_deposit_requests() if (d.get("status") or "").lower() == "approved"]
    deps_today = [d for d in deps if _parse_any_date_prefix(d.get("date")) == today]

    local_orders = [o for o in database.get_all_orders() if (o.get("status") or "").lower() in ["completed", "success", "accept"]]
    local_today = [o for o in local_orders if _parse_any_date_prefix(o.get("date")) == today]

    api_orders = [o for o in database.get_all_recent_api_orders(500) if (o.get("status") or "").lower() in ["completed", "success", "accept"]]
    api_today = [o for o in api_orders if _parse_any_date_prefix(o.get("created_at")) == today]

    dep_amount_sum = sum(float(d.get("amount", 0) or 0) for d in deps_today)
    orders_amount_sum = _sum_local_orders_usd(local_today) + sum(float(o.get("price", 0) or 0) for o in api_today)

    active_users = set()
    for d in deps_today:
        active_users.add(str(d.get("user_id")))
    for o in local_today:
        active_users.add(str(o.get("user_id")))
    for o in api_today:
        active_users.add(str(o.get("user_id")))

    txt = (
        f"📅 <b>النشاط اليومي</b> ({today})\n"
        f"━━━━━━━━━━━━\n"
        f"💳 الإيداعات: <b>{len(deps_today)}</b> | المبلغ (خام): <b>{dep_amount_sum}</b>\n"
        f"📦 الطلبات: <b>{len(local_today) + len(api_today)}</b> | المبلغ: <b>{orders_amount_sum:.2f}$</b>\n"
        f"👥 المستخدمون النشطون اليوم: <b>{len(active_users)}</b>\n"
        f"━━━━━━━━━━━━\n"
    )

    if deps_today:
        txt += "💳 <b>قائمة الإيداعات:</b>\n"
        txt += "\n".join(f"- #{d.get('id')} | {d.get('user_id')} | {d.get('method')} | {d.get('amount')}" for d in deps_today[:15])
        txt += "\n\n"

    if local_today or api_today:
        txt += "📦 <b>قائمة الطلبات:</b>\n"
        for o in (local_today[:10]):
            txt += f"- L#{o.get('id')} | {o.get('user_id')} | {(o.get('product') or {}).get('name','')}\n"
        for o in (api_today[:10]):
            txt += f"- A#{str(o.get('uuid'))[-8:]} | {o.get('user_id')} | {o.get('product_name','')}\n"

    if active_users:
        txt += "\n\n👥 <b>قائمة المستخدمين النشطين:</b>\n"
        txt += "\n".join(f"- <code>{uid}</code>" for uid in list(active_users)[:20])

    await smart_edit(call, txt, kb.back_btn("admin_activity"))


@router.callback_query(F.data == "admin_activity_weekly")
async def activity_weekly(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    start = datetime.now() - timedelta(days=7)
    deps = [d for d in database.get_all_deposit_requests() if (d.get("status") or "").lower() == "approved"]
    deps_week = []
    for d in deps:
        dp = _parse_any_date_prefix(d.get("date"))
        if not dp:
            continue
        try:
            dt = datetime.strptime(dp, "%Y-%m-%d")
        except Exception:
            continue
        if dt.date() >= start.date():
            deps_week.append(d)

    dep_amount_sum = sum(float(d.get("amount", 0) or 0) for d in deps_week)
    txt = (
        "📆 <b>النشاط الأسبوعي</b> (آخر 7 أيام)\n"
        "━━━━━━━━━━━━\n"
        f"💳 الإيداعات: <b>{len(deps_week)}</b> | المبلغ (خام): <b>{dep_amount_sum}</b>\n"
    )
    await smart_edit(call, txt, kb.back_btn("admin_activity"))


@router.callback_query(F.data == "admin_activity_monthly")
async def activity_monthly(call: types.CallbackQuery):
    if not database.is_user_admin(call.from_user.id):
        return await call.answer("❌ صلاحيات غير كافية.", show_alert=True)

    now = datetime.now()
    month_prefix = now.strftime("%Y-%m")

    deps = [d for d in database.get_all_deposit_requests() if (d.get("status") or "").lower() == "approved"]
    deps_month = [d for d in deps if (_parse_any_date_prefix(d.get("date")) or "").startswith(month_prefix)]
    dep_amount_sum = sum(float(d.get("amount", 0) or 0) for d in deps_month)

    txt = (
        f"🗓 <b>النشاط الشهري</b> ({month_prefix})\n"
        "━━━━━━━━━━━━\n"
        f"💳 الإيداعات: <b>{len(deps_month)}</b> | المبلغ (خام): <b>{dep_amount_sum}</b>\n"
    )
    await smart_edit(call, txt, kb.back_btn("admin_activity"))
