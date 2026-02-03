#!/usr/bin/env python3
"""
Verification script for admin order management improvements.
Tests all critical functionality.
"""

import services.database as database
import sys

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def test_database_schema():
    """Test that database schema is correct."""
    print_header("Testing Database Schema")
    
    try:
        database.init_db()
        print_success("Database initialized")
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Check orders table structure
        cursor.execute("PRAGMA table_info(orders)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        required_fields = {
            'id': 'TEXT',
            'user_id': 'TEXT',
            'product_json': 'TEXT',
            'qty': 'INTEGER',
            'inputs_json': 'TEXT',
            'params_json': 'TEXT',
            'status': 'TEXT',
            'date': 'TEXT',
            'order_source': 'TEXT'
        }
        
        for field, field_type in required_fields.items():
            if field in columns:
                print_success(f"Field '{field}' exists with type {columns[field]}")
            else:
                print_error(f"Field '{field}' missing!")
                return False
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Database schema test failed: {e}")
        return False

def test_order_source_constants():
    """Test that order source constants are defined."""
    print_header("Testing Order Source Constants")
    
    try:
        from handlers.admin.orders import ORDER_SOURCE_LOCAL, ORDER_SOURCE_API
        
        if ORDER_SOURCE_LOCAL == "LOCAL":
            print_success(f"ORDER_SOURCE_LOCAL = '{ORDER_SOURCE_LOCAL}'")
        else:
            print_error(f"ORDER_SOURCE_LOCAL has wrong value: {ORDER_SOURCE_LOCAL}")
            return False
        
        if ORDER_SOURCE_API == "API":
            print_success(f"ORDER_SOURCE_API = '{ORDER_SOURCE_API}'")
        else:
            print_error(f"ORDER_SOURCE_API has wrong value: {ORDER_SOURCE_API}")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Order source constants test failed: {e}")
        return False

def test_helper_functions():
    """Test helper functions."""
    print_header("Testing Helper Functions")
    
    try:
        from handlers.admin.orders import (
            _get_order_source_label,
            _should_show_controls,
            _format_admin_order_status
        )
        
        # Test source labels
        local_label = _get_order_source_label("LOCAL")
        api_label = _get_order_source_label("API")
        
        if "طلب محلي" in local_label:
            print_success(f"Local label: {local_label}")
        else:
            print_error(f"Local label incorrect: {local_label}")
            return False
        
        if "API" in api_label:
            print_success(f"API label: {api_label}")
        else:
            print_error(f"API label incorrect: {api_label}")
            return False
        
        # Test control visibility
        local_pending = {"status": "pending", "order_source": "LOCAL"}
        local_completed = {"status": "completed", "order_source": "LOCAL"}
        api_order = {"status": "pending", "order_source": "API"}
        
        if _should_show_controls(local_pending, is_api=False):
            print_success("Controls shown for local pending order")
        else:
            print_error("Controls NOT shown for local pending order")
            return False
        
        if not _should_show_controls(local_completed, is_api=False):
            print_success("Controls hidden for local completed order")
        else:
            print_error("Controls shown for local completed order")
            return False
        
        if not _should_show_controls(api_order, is_api=True):
            print_success("Controls hidden for API order")
        else:
            print_error("Controls shown for API order")
            return False
        
        # Test status formatting
        status_label, status_code = _format_admin_order_status("pending")
        if status_code == "pending":
            print_success(f"Status formatting works: {status_label}")
        else:
            print_error(f"Status formatting failed: {status_code}")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Helper functions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_functions():
    """Test new database functions."""
    print_header("Testing Database Functions")
    
    try:
        # Test get_orders_by_status_and_source
        if hasattr(database, 'get_orders_by_status_and_source'):
            print_success("Function 'get_orders_by_status_and_source' exists")
        else:
            print_error("Function 'get_orders_by_status_and_source' missing")
            return False
        
        # Test get_all_orders_by_source
        if hasattr(database, 'get_all_orders_by_source'):
            print_success("Function 'get_all_orders_by_source' exists")
        else:
            print_error("Function 'get_all_orders_by_source' missing")
            return False
        
        # Test that functions work
        try:
            all_orders = database.get_all_orders_by_source()
            print_success(f"get_all_orders_by_source() returned {len(all_orders)} orders")
            
            local_orders = database.get_all_orders_by_source("LOCAL")
            print_success(f"get_all_orders_by_source('LOCAL') returned {len(local_orders)} orders")
            
            api_orders = database.get_all_orders_by_source("API")
            print_success(f"get_all_orders_by_source('API') returned {len(api_orders)} orders")
            
        except Exception as e:
            print_error(f"Database functions failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Database functions test failed: {e}")
        return False

def test_imports():
    """Test that all imports work."""
    print_header("Testing Imports")
    
    try:
        from handlers.admin import orders
        print_success("handlers.admin.orders imported")
        
        from services import database
        print_success("services.database imported")
        
        from aiogram import Router, types, F
        print_success("aiogram imported")
        
        return True
        
    except Exception as e:
        print_error(f"Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  ADMIN ORDER MANAGEMENT - VERIFICATION TESTS")
    print("="*60)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Order Source Constants", test_order_source_constants),
        ("Helper Functions", test_helper_functions),
        ("Database Functions", test_database_functions),
        ("Imports", test_imports),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! ✨")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
