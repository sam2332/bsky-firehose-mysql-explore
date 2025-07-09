#!/usr/bin/env python3
"""
Test script to verify background monitoring improvements
"""

import sys
import os
import time
import threading
sys.path.append('/workspaces/bsky/flask-app')

from libs.database import get_shared_database_class

def test_repeated_database_operations():
    """Test repeated database operations similar to background monitoring"""
    print("🔄 Testing repeated database operations...")
    
    try:
        for i in range(5):  # Test 5 iterations
            print(f"  Iteration {i+1}/5...")
            
            # Use fresh database instance for each iteration (like our fixed background monitoring)
            with get_shared_database_class() as db:
                # Simulate multiple queries like in analytics monitoring
                result1 = db.fetch_one("SELECT COUNT(*) as count FROM posts LIMIT 1")
                result2 = db.fetch_all("SELECT 1 as test UNION SELECT 2 as test")
                result3 = db.fetch_one("SELECT 'hello' as message")
                
                print(f"    Results: {result1['count'] if result1 else 0} posts, {len(result2)} test results, message: {result3['message'] if result3 else 'None'}")
            
            # Small delay between iterations
            time.sleep(0.5)
        
        print("✅ Repeated database operations test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Repeated database operations test failed: {e}")
        return False

def test_parallel_database_access():
    """Test parallel database access from multiple threads"""
    print("🔄 Testing parallel database access...")
    
    results = []
    errors = []
    
    def worker_thread(thread_id):
        try:
            with get_shared_database_class() as db:
                result = db.fetch_one("SELECT %s as thread_id, COUNT(*) as count FROM posts", (thread_id,))
                results.append(f"Thread {thread_id}: {result['count'] if result else 0} posts")
        except Exception as e:
            errors.append(f"Thread {thread_id} error: {e}")
    
    # Start multiple threads
    threads = []
    for i in range(3):
        thread = threading.Thread(target=worker_thread, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    if errors:
        print(f"❌ Parallel database access test failed with errors: {errors}")
        return False
    else:
        print(f"✅ Parallel database access test passed! Results: {results}")
        return True

if __name__ == "__main__":
    print("Testing database connection improvements for background monitoring...")
    
    # Run tests
    tests = [
        test_repeated_database_operations,
        test_parallel_database_access,
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
        print("🎉 All tests passed! Background monitoring should now work without unread result errors.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed!")
        sys.exit(1)
