import asyncio
import services.database as database
import services.api_manager as api_manager
from aiogram import Bot


# ✅ مهمة مراقبة الطلبات (موجودة سابقاً)
async def check_pending_orders_task(bot: Bot):
    print("👀 Background Task Started: Monitoring API orders...")
    while True:
        try:
            pending_orders = database.get_pending_api_orders()
            if pending_orders:
                uuids = [o['uuid'] for o in pending_orders]
                stats = await asyncio.to_thread(api_manager.check_orders_status, uuids)

                for stat in stats:
                    s_uuid = stat.get('order_uuid') or stat.get('custom_uuid')
                    # محاولة البحث العميق في data
                    if not s_uuid:
                        api_data = stat.get('data')
                        if isinstance(api_data, dict):
                            s_uuid = api_data.get('custom_uuid') or api_data.get('order_uuid')

                    local_order = None
                    if s_uuid:
                        local_order = next((o for o in pending_orders if o['uuid'] == s_uuid), None)

                    # محاولة المطابقة عبر order_id
                    if not local_order:
                        ext_id = stat.get('order_id') or stat.get('id')
                        if ext_id:
                            local_order = next((o for o in pending_orders if str(o['order_id']) == str(ext_id)), None)

                    if not local_order: continue

                    user_id = local_order['user_id']
                    status = stat.get('status')

                    if status in ['completed', 'Success', 'accept']:
                        codes = stat.get('replay_api')
                        code_txt = codes[0] if (codes and isinstance(codes, list) and len(codes) > 0) else ""
                        database.update_api_order_status(local_order['uuid'], "completed", code=code_txt, notified=1)
                        msg = f"✅ <b>تم تنفيذ طلبك بنجاح!</b>\n📦 المنتج: {stat.get('product_name')}\n🔑 <b>الكود:</b> <code>{code_txt}</code>"
                        try:
                            await bot.send_message(user_id, msg, parse_mode="HTML")
                        except:
                            pass

                    elif status in ['Canceled', 'Fail', 'rejected', 'reject']:
                        if local_order['notified'] == 0:
                            database.update_api_order_status(local_order['uuid'], "rejected", notified=1)
                            price = float(local_order['price'])
                            database.add_balance(user_id, price)
                            try:
                                await bot.send_message(user_id,
                                                       f"❌ تم رفض طلبك ({local_order['product_name']}) وإعادة {price}$ لرصيدك.",
                                                       parse_mode="HTML")
                            except:
                                pass

        except Exception as e:
            print(f"⚠️ Order Check Error: {e}")

        await asyncio.sleep(60)


# ✅ المهمة الجديدة: تحديث المنتجات كل 30 دقيقة
async def auto_refresh_products_task():
    print("🔄 Auto-Refresh Task Started: Updating products every 30 mins...")
    while True:
        try:
            # نستخدم to_thread لكي لا يتجمد البوت أثناء الاتصال
            print("⏳ جاري تحديث قائمة المنتجات في الخلفية...")
            await asyncio.to_thread(api_manager.refresh_data)
            print("✅ تم تحديث المنتجات بنجاح!")
        except Exception as e:
            print(f"⚠️ Product Refresh Error: {e}")

        # الانتظار 30 دقيقة (1800 ثانية)
        await asyncio.sleep(1800)