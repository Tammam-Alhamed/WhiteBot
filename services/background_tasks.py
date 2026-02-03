import asyncio
import services.database as database
import services.api_manager as api_manager
import services.settings as settings
from aiogram import Bot


# ✅ مهمة مراقبة الطلبات (مع إصلاح مشكلة التكرار المزدوج)
async def check_pending_orders_task(bot: Bot):
    print("👀 Background Task Started: Monitoring API orders...")
    while True:
        try:
            # 1. جلب الطلبات المعلقة
            pending_orders = database.get_pending_api_orders()
            if pending_orders:
                # تجميع الـ UUIDs للفحص الجماعي
                uuids = [o['uuid'] for o in pending_orders]
                stats = await asyncio.to_thread(api_manager.check_orders_status, uuids)

                for stat in stats:
                    # --- منطق الربط (Matching Logic) ---
                    s_uuid = stat.get('order_uuid') or stat.get('custom_uuid')
                    if not s_uuid:
                        api_data = stat.get('data')
                        if isinstance(api_data, dict):
                            s_uuid = api_data.get('custom_uuid') or api_data.get('order_uuid')

                    local_order = None
                    if s_uuid:
                        local_order = next((o for o in pending_orders if o['uuid'] == s_uuid), None)

                    if not local_order:
                        ext_id = stat.get('order_id') or stat.get('id')
                        if ext_id:
                            local_order = next((o for o in pending_orders if str(o['order_id']) == str(ext_id)), None)

                    if not local_order: continue

                    # 🛡️ حماية قصوى: جلب حالة الطلب الحالية من الداتابيز مباشرة
                    # هذا يمنع التكرار في حال تم معالجة الطلب في دورة سابقة أو ب thread آخر
                    current_db_order = database.get_order_by_uuid(local_order['uuid'])
                    if not current_db_order or current_db_order['status'] != 'pending':
                        continue  # تخطي إذا لم يعد معلقاً

                    user_id = local_order['user_id']
                    new_status = stat.get('status')

                    # 1. حالة النجاح
                    if new_status in ['completed', 'Success', 'accept']:
                        codes = stat.get('replay_api')
                        code_txt = codes[0] if (codes and isinstance(codes, list) and len(codes) > 0) else ""

                        # تحديث الحالة أولاً لمنع التكرار
                        database.update_api_order_status(local_order['uuid'], "completed", code=code_txt, notified=1)

                        msg = f"✅ <b>تم تنفيذ طلبك بنجاح!</b>\n📦 المنتج: {stat.get('product_name')}\n🔑 <b>الكود:</b> <code>{code_txt}</code>"
                        try:
                            await bot.send_message(user_id, msg, parse_mode="HTML")
                        except:
                            pass

                    # 2. حالة الفشل/الرفض
                    elif new_status in ['Canceled', 'Fail', 'rejected', 'reject']:
                        # ⛔️ الخطوة الحاسمة: تحديث الحالة إلى rejected فوراً قبل لمس المال
                        # إذا نجح التحديث (أي كانت الحالة pending)، ننفذ الإرجاع.
                        # سنقوم بتحديث الحالة يدوياً هنا لضمان عدم دخول دالة أخرى
                        database.update_api_order_status(local_order['uuid'], "rejected", notified=1)

                        # الآن الآمان: نرجع المصاري
                        price = float(local_order['price'])

                        # أ) استرجاع الرصيد
                        new_bal_usd = database.add_balance(user_id, price)

                        # ب) الحسابات للعرض
                        rate = settings.get_setting("exchange_rate")
                        old_bal_usd = new_bal_usd - price

                        price_syp = round(price * rate)
                        old_bal_syp = round(old_bal_usd * rate)
                        new_bal_syp = round(new_bal_usd * rate)

                        # ج) إرسال الرسالة
                        msg = (
                            f"❌ <b>تم رفض طلبك ({local_order.get('product_name', 'API')})</b>\n"
                            f"💸 <b>تم استعادة:</b> {price}$ ({price_syp:,.0f} ل.س)\n"
                            f"────────────────\n"
                            f"📉 <b>رصيدك السابق:</b> {old_bal_usd:.2f}$ ({old_bal_syp:,.0f} ل.س)\n"
                            f"📈 <b>رصيدك الحالي:</b> {new_bal_usd:.2f}$ ({new_bal_syp:,.0f} ل.س)"
                        )
                        try:
                            await bot.send_message(user_id, msg, parse_mode="HTML")
                        except:
                            pass

        except Exception as e:
            print(f"⚠️ Order Check Error: {e}")

        await asyncio.sleep(60)


# ✅ مهمة تحديث المنتجات (كما هي)
async def auto_refresh_products_task():
    print("🔄 Auto-Refresh Task Started: Updating products every 30 mins...")
    while True:
        try:
            print("⏳ جاري تحديث قائمة المنتجات في الخلفية...")
            await asyncio.to_thread(api_manager.refresh_data)
            print("✅ تم تحديث المنتجات بنجاح!")
        except Exception as e:
            print(f"⚠️ Product Refresh Error: {e}")
        await asyncio.sleep(1800)