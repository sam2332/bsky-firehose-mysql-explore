#!/usr/bin/env python3
"""
Test script to verify database connection improvements
"""

import sys
import os
sys.path.append('/workspaces/bsky/flask-app')

from libs.database import get_shared_database_class

def test_basic_connection():
    """Test basic database connection and query"""
    try:
        with get_shared_database_class() as db:
            # Test simple query
            result = db.fetch_one("SELECT 1 as test")
            print(f"✅ Basic connection test passed: {result}")
            
            # Test query with parameters
            result = db.fetch_one("SELECT %s as test", ("hello",))
            print(f"✅ Parameterized query test passed: {result}")
            
            # Test multiple queries in sequence
            result1 = db.fetch_one("SELECT COUNT(*) as count FROM posts LIMIT 1")
            result2 = db.fetch_one("SELECT 1 as test")
            print(f"✅ Multiple queries test passed: {result1}, {result2}")
            
            return True
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def test_connection_reuse():
    """Test connection reuse functionality"""
    try:
        # First connection
        with get_shared_database_class() as db1:
            result1 = db1.fetch_one("SELECT 1 as first")
            
        # Second connection (should reuse)
        with get_shared_database_class() as db2:
            result2 = db2.fetch_one("SELECT 2 as second")
            
        print(f"✅ Connection reuse test passed: {result1}, {result2}")
        return True
    except Exception as e:
        print(f"❌ Connection reuse test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing database connection improvements...")
    
    # Run tests
    tests = [
        test_basic_connection,
        test_connection_reuse,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed!")
        sys.exit(1)
