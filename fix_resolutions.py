#!/usr/bin/env python3
"""
Fix script to sync cached DID resolutions with posts and process backlog
"""
import sqlite3
import time
from datetime import datetime

def sync_cached_handles():
    """Update posts with handles that are already cached"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    # Update posts where we have cached handles but posts aren't updated
    cursor.execute('''
        UPDATE posts 
        SET author_handle = (
            SELECT handle 
            FROM did_cache 
            WHERE did_cache.did = posts.author_did
        ) 
        WHERE author_handle IS NULL 
        AND EXISTS (
            SELECT 1 
            FROM did_cache 
            WHERE did_cache.did = posts.author_did 
            AND did_cache.handle IS NOT NULL
        )
    ''')
    
    updated_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return updated_count

def get_stats():
    """Get current resolution statistics"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM posts')
    total_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM posts WHERE author_handle IS NOT NULL')
    resolved_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM posts WHERE author_handle IS NULL')
    unresolved_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM did_cache WHERE handle IS NOT NULL')
    cached_successes = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM did_cache WHERE handle IS NULL')
    cached_failures = cursor.fetchone()[0]
    
    # Count posts that could be resolved from cache but aren't
    cursor.execute('''
        SELECT COUNT(*) 
        FROM posts p 
        JOIN did_cache dc ON p.author_did = dc.did 
        WHERE p.author_handle IS NULL AND dc.handle IS NOT NULL
    ''')
    sync_needed = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_posts': total_posts,
        'resolved_posts': resolved_posts,
        'unresolved_posts': unresolved_posts,
        'cached_successes': cached_successes,
        'cached_failures': cached_failures,
        'sync_needed': sync_needed,
        'resolution_rate': (resolved_posts / total_posts * 100) if total_posts > 0 else 0
    }

def get_unresolved_dids(limit=20):
    """Get DIDs that need resolution, prioritized by post count"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.author_did, COUNT(*) as post_count
        FROM posts p
        LEFT JOIN did_cache dc ON p.author_did = dc.did
        WHERE p.author_handle IS NULL 
        AND (dc.did IS NULL OR (dc.handle IS NULL AND dc.failed_attempts < 3))
        GROUP BY p.author_did
        ORDER BY post_count DESC
        LIMIT ?
    ''', (limit,))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def main():
    print("DID Resolution Fix Script")
    print("=" * 50)
    
    while True:
        try:
            # Sync cached handles first
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Syncing cached handles...")
            updated = sync_cached_handles()
            if updated > 0:
                print(f"✅ Updated {updated} posts with cached handles")
            
            # Get current stats
            stats = get_stats()
            print(f"\n📊 Current Status:")
            print(f"   Total posts: {stats['total_posts']:,}")
            print(f"   Resolved: {stats['resolved_posts']:,} ({stats['resolution_rate']:.1f}%)")
            print(f"   Unresolved: {stats['unresolved_posts']:,}")
            print(f"   Cached successes: {stats['cached_successes']:,}")
            print(f"   Cached failures: {stats['cached_failures']:,}")
            print(f"   Sync needed: {stats['sync_needed']:,}")
            
            # Show top unresolved DIDs
            unresolved = get_unresolved_dids(5)
            if unresolved:
                print(f"\n🔍 Top unresolved DIDs:")
                for did, count in unresolved:
                    print(f"   {did[:30]}... ({count} posts)")
            
            time.sleep(30)  # Update every 30 seconds
            
        except KeyboardInterrupt:
            print("\n👋 Fix script stopped.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
