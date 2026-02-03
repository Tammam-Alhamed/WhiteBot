# 🎯 Quick Reference - Admin Order Management

## Order Source Classification

| Source | Label | Icon | Meaning |
|--------|-------|------|---------|
| LOCAL | طلب محلي | 📱 | Manual/internal order |
| API | طلب عبر API | 🌐 | External provider order |

---

## Control Button Rules

### API Orders (ANY Status)
```
Status: pending, completed, or rejected
Controls: NONE (read-only)
Buttons: Back only
```

### Local Orders - PENDING
```
Status: pending
Controls: FULL
Buttons:
  🔄 إعادة المحاولة (API)
  ✅ تم التنفيذ يدوياً
  ❌ إلغاء وإرجاع الرصيد
  🔙 رجوع
```

### Local Orders - COMPLETED/REJECTED
```
Status: completed or rejected
Controls: NONE (read-only)
Buttons: Back only
```

---

## Admin Workflows

### View Pending Orders
```
Admin Panel → 📦 إدارة الطلبات
           → ⏳ الطلبات المعلقة
           → [📱 محلي فقط] [🌐 API فقط]
           → Click order ID
```

### Manage Local Pending Order
```
View Order Details
  ↓
Check: "⏳ معلق | 📱 طلب محلي"
  ↓
Choose Action:
  - 🔄 Retry via API
  - ✅ Mark as done
  - ❌ Refund & reject
```

### View API Order
```
View Order Details
  ↓
Check: "⏳ معلق | 🌐 طلب عبر API"
  ↓
No controls available (read-only)
  ↓
Click back button
```

### Search Orders
```
Admin Panel → 🔍 بحث عن طلب
           → Enter order ID or user ID
           → Results show source label
           → Click order ID to view
```

### Filter by Status
```
Admin Panel → 📦 إدارة الطلبات
           → Choose status:
             - ⏳ الطلبات المعلقة
             - ✅ الطلبات المكتملة
             - ❌ الطلبات المرفوضة
           → [📱 محلي فقط] [🌐 API فقط]
```

---

## Safety Rules

### ✅ Allowed Actions
- View any order (local or API)
- Retry local pending orders via API
- Mark local pending orders as done
- Refund local pending orders
- Bulk approve local pending orders
- Bulk reject local pending orders
- Filter orders by source and status
- Search orders by ID or user ID

### ❌ Forbidden Actions
- Modify API orders (any status)
- Modify completed orders
- Modify rejected orders
- Refund API orders
- Retry API orders
- Bulk operations on API orders

---

## Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| ❌ لا يمكن إعادة محاولة طلبات API | Can't retry API orders | Only retry local orders |
| ❌ يمكن فقط إعادة محاولة الطلبات المعلقة | Can only retry pending | Order must be pending |
| ❌ لا يمكن تعديل طلبات API | Can't modify API orders | API orders are read-only |
| ❌ يمكن فقط تعديل الطلبات المعلقة | Can only modify pending | Order must be pending |
| ❌ لا يمكن استرجاع طلبات API | Can't refund API orders | API orders are read-only |
| ❌ يمكن فقط استرجاع الطلبات المعلقة | Can only refund pending | Order must be pending |

---

## Database Functions

### Get Orders by Source
```python
# All orders
orders = database.get_all_orders_by_source()

# Local orders only
local = database.get_all_orders_by_source("LOCAL")

# API orders only
api = database.get_all_orders_by_source("API")
```

### Get Orders by Status and Source
```python
# Pending local orders
pending_local = database.get_orders_by_status_and_source("pending", "LOCAL")

# Completed API orders
completed_api = database.get_orders_by_status_and_source("completed", "API")

# All pending orders
all_pending = database.get_orders_by_status_and_source("pending")
```

---

## UI Display Examples

### Pending Orders List
```
⏳ الطلبات المعلقة (5)
━━━━━━━━━━━━━━━━━━━━━━

⏳ معلق | 📱 طلب محلي
📦 PUBG UC
🔢 رقم: 12345
👤 المستخدم: 987654321
💰 المبلغ: 150$ (3x 50$)
📅 التاريخ: 2024-01-27 03:45 PM
─────────────────────

⏳ معلق | 🌐 طلب عبر API
📦 Fortnite V-Bucks
🔢 رقم: 54321
👤 المستخدم: 987654321
💰 المبلغ: 100$
─────────────────────

[#12345] [#54321]
[📱 محلي فقط] [🌐 API فقط]
[✅ قبول الكل] [❌ رفض الكل]
[🔙 رجوع]
```

### Order Details - Local Pending
```
📦 تفاصيل الطلب #12345
━━━━━━━━━━━━━━━━━━━━━━
⏳ معلق | 📱 طلب محلي
━━━━━━━━━━━━━━━━━━━━━━
👤 العميل: 987654321
📦 المنتج: PUBG UC
💰 السعر: 50$ × 3 = 150$
━━━━━━━━━━━━━━━━━━━━━━
📅 التاريخ: 2024-01-27 03:45 PM

[🔄 إعادة المحاولة (API)]
[✅ تم التنفيذ يدوياً]
[❌ إلغاء وإرجاع الرصيد]
[🔙 رجوع]
```

### Order Details - API Order
```
📦 تفاصيل الطلب #54321
━━━━━━━━━━━━━━━━━━━━━━
⏳ معلق | 🌐 طلب عبر API
━━━━━━━━━━━━━━━━━━━━━━
👤 العميل: 987654321
📦 المنتج: Fortnite V-Bucks
💰 السعر: 100$
━━━━━━━━━━━━━━━━━━━━━━
📅 التاريخ: 2024-01-27 02:30 PM

[🔙 رجوع]
```

### Search Results
```
🔍 نتائج البحث عن: 12345
━━━━━━━━━━━━━━━━━━━━━━

✅ تم العثور على 2 نتيجة:

1. ⏳ معلق | 📱 طلب محلي | PUBG UC
   🔢 12345 | 👤 987654321

2. ✅ مكتمل | 🌐 طلب عبر API | Fortnite V-Bucks
   🔢 54321 | 👤 987654321

[#12345] [#54321]
[🔙 رجوع]
```

---

## Filtering Options

### By Status
- ⏳ الطلبات المعلقة (Pending)
- ✅ الطلبات المكتملة (Completed)
- ❌ الطلبات المرفوضة (Rejected)

### By Source (within each status)
- 📱 محلي فقط (Local only)
- 🌐 API فقط (API only)
- All (default)

---

## Bulk Operations

### Bulk Approve
```
Affects: Local pending orders ONLY
Action: Mark as completed
Notification: Sent to users
Confirmation: Required
```

### Bulk Reject
```
Affects: Local pending orders ONLY
Action: Mark as rejected + refund
Notification: Sent to users with refund details
Confirmation: Required
```

---

## Constants

```python
ORDER_SOURCE_LOCAL = "LOCAL"
ORDER_SOURCE_API = "API"
```

---

## Troubleshooting

### Admin can't see controls
- Check order source (should be LOCAL)
- Check order status (should be pending)
- Refresh page

### Admin sees wrong label
- Check database migration ran
- Verify order_source field exists
- Run verify_improvements.py

### Bulk operations not working
- Check orders are local pending
- Check admin permissions
- Check database connection

### Search not finding orders
- Check order ID or user ID is correct
- Check order exists in database
- Try searching by different field

---

## Performance Tips

- Listings show last 20 orders (configurable)
- Search limited to 10 results (configurable)
- Filtering done in memory (fast)
- No N+1 queries
- Async operations for responsiveness

---

## Verification

Run anytime to verify implementation:
```bash
python verify_improvements.py
```

Expected output:
```
✅ PASS: Database Schema
✅ PASS: Order Source Constants
✅ PASS: Helper Functions
✅ PASS: Database Functions
✅ PASS: Imports

Total: 5/5 tests passed
```

---

## Key Files

- **handlers/admin/orders.py** - Admin order handlers
- **services/database.py** - Database functions
- **ADMIN_ORDER_IMPROVEMENTS.md** - Full documentation
- **MIGRATION_GUIDE.md** - Migration instructions
- **verify_improvements.py** - Verification script

---

## Support

For detailed information, see:
- **ADMIN_ORDER_IMPROVEMENTS.md** - Comprehensive guide
- **MIGRATION_GUIDE.md** - Database migration
- **IMPLEMENTATION_COMPLETE.md** - Implementation summary

---

**Last Updated:** 2024
**Version:** 1.0
**Status:** ✅ Complete and Verified
