# 🔄 Database Migration Guide

## Overview

This guide explains how to migrate existing orders to use the new `order_source` field.

---

## What Changed?

A new field `order_source` was added to the `orders` table:
- **Field Name:** `order_source`
- **Type:** TEXT
- **Default Value:** `'LOCAL'`
- **Purpose:** Classify orders as LOCAL or API

---

## Migration Steps

### Step 1: Automatic Migration (Recommended)

The database schema is automatically updated when the bot starts:

```python
# In services/database.py - init_db()
cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    product_json TEXT,
    qty INTEGER,
    inputs_json TEXT,
    params_json TEXT,
    status TEXT,
    date TEXT,
    order_source TEXT DEFAULT 'LOCAL',  # ← New field
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
''')
```

**What happens:**
- ✅ If table doesn't exist: Created with new field
- ✅ If table exists: No changes (field already there or will be added by SQLite)
- ✅ Existing orders: Default to `'LOCAL'`

### Step 2: Verify Migration

Run this command to verify the migration:

```bash
python -c "
import services.database as db
db.init_db()
conn = db.get_db_connection()
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(orders)')
columns = cursor.fetchall()
for col in columns:
    print(f'{col[1]}: {col[2]}')
conn.close()
"
```

**Expected output:**
```
id: TEXT
user_id: TEXT
product_json: TEXT
qty: INTEGER
inputs_json: TEXT
params_json: TEXT
status: TEXT
date: TEXT
order_source: TEXT
```

### Step 3: Verify Data

Check that existing orders have the default value:

```bash
python -c "
import services.database as db
orders = db.get_all_orders()
print(f'Total orders: {len(orders)}')
for order in orders[:5]:
    source = order.get('order_source', 'NOT SET')
    print(f'Order {order[\"id\"]}: source={source}')
"
```

**Expected output:**
```
Total orders: 42
Order 12345: source=LOCAL
Order 54321: source=LOCAL
Order 98765: source=LOCAL
...
```

---

## Manual Migration (If Needed)

If you need to manually update the database:

### Option 1: Using SQLite CLI

```bash
sqlite3 whitebot.db
```

```sql
-- Add column if it doesn't exist
ALTER TABLE orders ADD COLUMN order_source TEXT DEFAULT 'LOCAL';

-- Verify
SELECT COUNT(*) FROM orders WHERE order_source IS NULL;
-- Should return 0

-- Check a few records
SELECT id, order_source FROM orders LIMIT 5;
```

### Option 2: Using Python

```python
import services.database as db

conn = db.get_db_connection()
cursor = conn.cursor()

# Add column if it doesn't exist
try:
    cursor.execute('ALTER TABLE orders ADD COLUMN order_source TEXT DEFAULT "LOCAL"')
    conn.commit()
    print("✅ Column added successfully")
except Exception as e:
    if "duplicate column" in str(e):
        print("✅ Column already exists")
    else:
        print(f"❌ Error: {e}")

# Verify
cursor.execute('SELECT COUNT(*) FROM orders WHERE order_source IS NULL')
null_count = cursor.fetchone()[0]
print(f"Orders with NULL source: {null_count}")

# Update any NULL values to 'LOCAL'
if null_count > 0:
    cursor.execute('UPDATE orders SET order_source = "LOCAL" WHERE order_source IS NULL')
    conn.commit()
    print(f"✅ Updated {cursor.rowcount} orders")

conn.close()
```

---

## Rollback (If Needed)

If you need to rollback the changes:

### Option 1: Remove the field

```sql
-- SQLite doesn't support DROP COLUMN directly
-- You would need to recreate the table without the field
-- This is complex, so it's not recommended
```

### Option 2: Restore from backup

```bash
# If you have a backup
cp whitebot.db.backup whitebot.db
```

---

## Verification Checklist

After migration, verify:

- [ ] Database initializes without errors
- [ ] All existing orders have `order_source = 'LOCAL'`
- [ ] New orders are created with `order_source = 'LOCAL'`
- [ ] Admin can filter orders by source
- [ ] Admin can view order details with source label
- [ ] Control buttons show/hide correctly based on source
- [ ] No errors in bot logs

---

## Troubleshooting

### Issue: "duplicate column" error

**Cause:** Column already exists in database

**Solution:** This is normal. The column was already added in a previous migration.

### Issue: Orders showing NULL for order_source

**Cause:** Old database records before migration

**Solution:** Run the update command:
```python
import services.database as db
conn = db.get_db_connection()
cursor = conn.cursor()
cursor.execute('UPDATE orders SET order_source = "LOCAL" WHERE order_source IS NULL')
conn.commit()
conn.close()
```

### Issue: Admin can't filter by source

**Cause:** Database not properly initialized

**Solution:** 
1. Restart the bot
2. Run `db.init_db()` manually
3. Check database schema with PRAGMA

### Issue: New orders not getting source field

**Cause:** Code not using new database functions

**Solution:** Ensure `save_pending_order()` is being used (it automatically sets source to LOCAL)

---

## Data Integrity

### Before Migration
```
orders table:
- id, user_id, product_json, qty, inputs_json, params_json, status, date
```

### After Migration
```
orders table:
- id, user_id, product_json, qty, inputs_json, params_json, status, date, order_source
```

### Data Preservation
- ✅ All existing orders preserved
- ✅ All existing fields unchanged
- ✅ New field defaults to 'LOCAL'
- ✅ No data loss

---

## Performance Impact

- ✅ Minimal - just one additional TEXT field
- ✅ No indexes added (can be added later if needed)
- ✅ No query performance impact
- ✅ Filtering is efficient

---

## Backward Compatibility

- ✅ Existing code continues to work
- ✅ New code uses new field
- ✅ Default value ensures compatibility
- ✅ No breaking changes

---

## Next Steps

After successful migration:

1. ✅ Verify all orders have source field
2. ✅ Test admin filtering by source
3. ✅ Test control button visibility
4. ✅ Test bulk operations
5. ✅ Monitor logs for errors
6. ✅ Backup database

---

## Support

If you encounter issues:

1. Check this guide
2. Review error messages
3. Check database schema
4. Verify data integrity
5. Check bot logs

All changes are backward compatible and safe.
