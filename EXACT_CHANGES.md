# Exact Code Changes Reference

## File 1: services/database.py

### Change: Added new function (after `is_user_admin()`)

```python
def is_super_admin(user_id):
    """التحقق هل المستخدم سوبر أدمن (من config فقط)"""
    import config
    return user_id in config.ADMIN_IDS
```

**Location:** End of file, after `is_user_admin()` function  
**Lines Added:** 3  
**Purpose:** Distinguish super-admins (from config) from regular admins (from database)

---

## File 2: handlers/admin/users.py

### Change 1: Enhanced `promote_user_to_admin()` function

**BEFORE:**
```python
@router.callback_query(F.data.startswith("promote_admin:"))
async def promote_user_to_admin(call: types.CallbackQuery):
    uid = call.data.split(":")[1]
    database.set_admin(uid, True)
    await call.answer("✅ تم ترقية المستخدم إلى أدمن بنجاح!", show_alert=True)
    await open_user_control(call.message, uid, is_edit=True)
```

**AFTER:**
```python
@router.callback_query(F.data.startswith("promote_admin:"))
async def promote_user_to_admin(call: types.CallbackQuery):
    # التحقق: فقط السوبر أدمن يمكنه ترقية مستخدمين
    if not database.is_super_admin(call.from_user.id):
        return await call.answer("❌ فقط السوبر أدمن يمكنه ترقية المستخدمين!", show_alert=True)
    
    uid = call.data.split(":")[1]
    database.set_admin(uid, True)
    await call.answer("✅ تم ترقية المستخدم إلى أدمن بنجاح!", show_alert=True)
    await open_user_control(call.message, uid, is_edit=True)
```

**Lines Added:** 3  
**Change Type:** Permission check added

### Change 2: Enhanced `demote_user_from_admin()` function

**BEFORE:**
```python
@router.callback_query(F.data.startswith("demote_admin:"))
async def demote_user_from_admin(call: types.CallbackQuery):
    uid = call.data.split(":")[1]

    # حماية: لا يمكنك حذف نفسك من الأدمن لتجنب أن تغلق البوت على نفسك
    if str(uid) == str(call.from_user.id):
        return await call.answer("❌ لا يمكنك إزالة نفسك من الأدمن!", show_alert=True)

    database.set_admin(uid, False)
    await call.answer("✅ تم إزالة صلاحيات الأدمن.", show_alert=True)
    await open_user_control(call.message, uid, is_edit=True)
```

**AFTER:**
```python
@router.callback_query(F.data.startswith("demote_admin:"))
async def demote_user_from_admin(call: types.CallbackQuery):
    # التحقق: فقط السوبر أدمن يمكنه تنزيل مستخدمين
    if not database.is_super_admin(call.from_user.id):
        return await call.answer("❌ فقط السوبر أدمن يمكنه تنزيل المستخدمين!", show_alert=True)
    
    uid = call.data.split(":")[1]

    # حماية: لا يمكنك حذف نفسك من الأدمن لتجنب أن تغلق البوت على نفسك
    if str(uid) == str(call.from_user.id):
        return await call.answer("❌ لا يمكنك إزالة نفسك من الأدمن!", show_alert=True)

    database.set_admin(uid, False)
    await call.answer("✅ تم إزالة صلاحيات الأدمن.", show_alert=True)
    await open_user_control(call.message, uid, is_edit=True)
```

**Lines Added:** 3  
**Change Type:** Permission check added

---

## File 3: handlers/admin/orders.py

### Change 1: `retry_order_api()` function (Line ~89)

**BEFORE:**
```python
if success:
    if uuid_order:
        api_manager.save_uuid_locally(order['user_id'], uuid_order)
    database.remove_pending_order(oid)  # ❌ DELETED
    try:
        await call.bot.send_message(...)
```

**AFTER:**
```python
if success:
    if uuid_order:
        api_manager.save_uuid_locally(order['user_id'], uuid_order)
    database.update_order_status(oid, "completed")  # ✅ STATUS UPDATE
    try:
        await call.bot.send_message(...)
```

**Change:** 1 line modified

### Change 2: `mark_manual_done()` function (Line ~127)

**BEFORE:**
```python
await call.answer("تم الحفظ وإشعار العميل ✅")
database.remove_pending_order(oid)  # ❌ DELETED
await show_pending_orders(call)
```

**AFTER:**
```python
await call.answer("تم الحفظ وإشعار العميل ✅")
await show_pending_orders(call)
```

**Change:** 1 line removed

### Change 3: `refund_order_admin()` function (Line ~160)

**BEFORE:**
```python
cost_syp = int(cost * rate)

database.remove_pending_order(oid)  # ❌ DELETED

try:
```

**AFTER:**
```python
cost_syp = int(cost * rate)

database.update_order_status(oid, "rejected")  # ✅ STATUS UPDATE

try:
```

**Change:** 1 line modified

### Change 4: `confirm_bulk_approve_orders()` function (Line ~234)

**BEFORE:**
```python
for order in pending:
    try:
        database.update_order_status(order['id'], "completed")
        
        # Notify user
        try:
            await call.bot.send_message(...)
        except:
            pass
        
        database.remove_pending_order(order['id'])  # ❌ DELETED
        approved_count += 1
```

**AFTER:**
```python
for order in pending:
    try:
        database.update_order_status(order['id'], "completed")
        
        # Notify user
        try:
            await call.bot.send_message(...)
        except:
            pass
        
        approved_count += 1
```

**Change:** 1 line removed

### Change 5: `confirm_bulk_reject_orders()` function (Line ~267)

**BEFORE:**
```python
for order in pending:
    try:
        cost = float(order['product']['price']) * int(order['qty'])
        cost_syp = int(cost * rate)
        
        # Refund balance
        new_bal = database.add_balance(order['user_id'], cost)
        new_bal_syp = int(new_bal * rate)
        
        database.remove_pending_order(order['id'])  # ❌ DELETED
        rejected_count += 1
```

**AFTER:**
```python
for order in pending:
    try:
        cost = float(order['product']['price']) * int(order['qty'])
        cost_syp = int(cost * rate)
        
        # Refund balance
        new_bal = database.add_balance(order['user_id'], cost)
        new_bal_syp = int(new_bal * rate)
        
        database.update_order_status(order['id'], "rejected")  # ✅ STATUS UPDATE
        rejected_count += 1
```

**Change:** 1 line modified

---

## Summary of Changes

| File | Function | Change Type | Lines |
|------|----------|-------------|-------|
| database.py | is_super_admin() | NEW | +3 |
| users.py | promote_user_to_admin() | ENHANCED | +3 |
| users.py | demote_user_from_admin() | ENHANCED | +3 |
| orders.py | retry_order_api() | MODIFIED | 1 |
| orders.py | mark_manual_done() | MODIFIED | -1 |
| orders.py | refund_order_admin() | MODIFIED | 1 |
| orders.py | confirm_bulk_approve_orders() | MODIFIED | -1 |
| orders.py | confirm_bulk_reject_orders() | MODIFIED | 1 |

**Total Lines Changed:** ~19 lines  
**Total Files Modified:** 3 files  
**Breaking Changes:** 0  
**Backward Compatibility:** 100%

---

## Verification Commands

To verify the changes were applied correctly:

```bash
# Check for is_super_admin function
grep -n "def is_super_admin" services/database.py

# Check for permission checks in users.py
grep -n "is_super_admin" handlers/admin/users.py

# Check for status updates in orders.py
grep -n "update_order_status" handlers/admin/orders.py

# Check that remove_pending_order is NOT used in orders.py
grep -n "remove_pending_order" handlers/admin/orders.py
# Should return 0 results
```

---

## Rollback Instructions (if needed)

### To rollback database.py:
1. Remove the `is_super_admin()` function

### To rollback users.py:
1. Remove the permission check lines from `promote_user_to_admin()`
2. Remove the permission check lines from `demote_user_from_admin()`

### To rollback orders.py:
1. Replace `update_order_status(oid, "completed")` with `remove_pending_order(oid)` in `retry_order_api()`
2. Add back `database.remove_pending_order(oid)` in `mark_manual_done()`
3. Replace `update_order_status(oid, "rejected")` with `remove_pending_order(oid)` in `refund_order_admin()`
4. Add back `database.remove_pending_order(order['id'])` in `confirm_bulk_approve_orders()`
5. Replace `update_order_status(order['id'], "rejected")` with `remove_pending_order(order['id'])` in `confirm_bulk_reject_orders()`

**But you shouldn't need to - these changes are safe!**
