#!/usr/bin/env python3
"""
Monitor script to check DID resolution status
"""
import mysql.connector
import time
from datetime import datetime

# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306
}

def get_resolution_stats():
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    # Count posts with and without handles
    cursor.execute('SELECT COUNT(*) FROM posts WHERE author_handle IS NOT NULL')
    resolved_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM posts WHERE author_handle IS NULL')
    unresolved_count = cursor.fetchone()[0]
    
    # Count cached DIDs
    cursor.execute('SELECT COUNT(*) FROM did_cache WHERE handle IS NOT NULL')
    cached_success = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM did_cache WHERE handle IS NULL')
    cached_failures = cursor.fetchone()[0]
    
    # Get some recent unresolved posts
    cursor.execute('''
        SELECT author_did, COUNT(*) as post_count 
        FROM posts 
        WHERE author_handle IS NULL 
        GROUP BY author_did 
        ORDER BY post_count DESC 
        LIMIT 10
    ''')
    top_unresolved = cursor.fetchall()
    
    conn.close()
    
    return {
        'resolved_posts': resolved_count,
        'unresolved_posts': unresolved_count,
        'cached_successes': cached_success,
        'cached_failures': cached_failures,
        'top_unresolved': top_unresolved
    }

def main():
    print("DID Resolution Monitor")
    print("=" * 50)
    
    while True:
        try:
            stats = get_resolution_stats()
            total_posts = stats['resolved_posts'] + stats['unresolved_posts']
            resolution_rate = (stats['resolved_posts'] / total_posts * 100) if total_posts > 0 else 0
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Resolution Status:")
            print(f"  Total posts: {total_posts}")
            print(f"  Resolved: {stats['resolved_posts']} ({resolution_rate:.1f}%)")
            print(f"  Unresolved: {stats['unresolved_posts']}")
            print(f"  Cached successes: {stats['cached_successes']}")
            print(f"  Cached failures: {stats['cached_failures']}")
            
            if stats['top_unresolved']:
                print("\n  Top unresolved DIDs:")
                for did, count in stats['top_unresolved'][:5]:
                    print(f"    {did[:20]}... ({count} posts)")
            
            time.sleep(10)  # Update every 10 seconds
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
