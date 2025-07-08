import sqlite3
from datetime import datetime

def view_cache_stats():
    """View DID cache statistics"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    # Total cached DIDs
    cursor.execute('SELECT COUNT(*) FROM did_cache')
    total_cached = cursor.fetchone()[0]
    
    # Successfully resolved
    cursor.execute('SELECT COUNT(*) FROM did_cache WHERE handle IS NOT NULL')
    successful = cursor.fetchone()[0]
    
    # Failed resolutions
    cursor.execute('SELECT COUNT(*) FROM did_cache WHERE handle IS NULL')
    failed = cursor.fetchone()[0]
    
    # Recent resolutions (last 24 hours)
    cursor.execute('''
        SELECT COUNT(*) FROM did_cache 
        WHERE resolved_at > datetime('now', '-1 day')
    ''')
    recent = cursor.fetchone()[0]
    
    print(f"=== DID Cache Statistics ===")
    print(f"Total cached DIDs: {total_cached}")
    print(f"Successfully resolved: {successful}")
    print(f"Failed resolutions: {failed}")
    print(f"Resolved in last 24h: {recent}")
    
    conn.close()

def view_recent_resolutions(limit=20):
    """View recent DID resolutions"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT did, handle, resolved_at, failed_attempts
        FROM did_cache 
        ORDER BY resolved_at DESC 
        LIMIT ?
    ''', (limit,))
    
    results = cursor.fetchall()
    conn.close()
    
    print(f"=== Recent DID Resolutions ===")
    for did, handle, resolved_at, failed_attempts in results:
        status = f"@{handle}" if handle else f"FAILED ({failed_attempts} attempts)"
        print(f"{resolved_at}: {did} -> {status}")

def clear_failed_cache():
    """Clear failed resolution attempts to allow retries"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM did_cache WHERE handle IS NULL')
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"Cleared {deleted} failed resolution entries from cache")

def search_cache(search_term):
    """Search cache by handle or DID"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT did, handle, resolved_at, failed_attempts
        FROM did_cache 
        WHERE did LIKE ? OR handle LIKE ?
        ORDER BY resolved_at DESC
    ''', (f'%{search_term}%', f'%{search_term}%'))
    
    results = cursor.fetchall()
    conn.close()
    
    print(f"=== Cache entries matching '{search_term}' ===")
    for did, handle, resolved_at, failed_attempts in results:
        status = f"@{handle}" if handle else f"FAILED ({failed_attempts} attempts)"
        print(f"{resolved_at}: {did} -> {status}")

def rebuild_cache_from_posts():
    """Rebuild cache from existing posts data"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    # Get unique DIDs with handles from posts
    cursor.execute('''
        SELECT DISTINCT author_did, author_handle 
        FROM posts 
        WHERE author_handle IS NOT NULL
    ''')
    
    posts_data = cursor.fetchall()
    
    for did, handle in posts_data:
        cursor.execute('''
            INSERT OR IGNORE INTO did_cache (did, handle, resolved_at, failed_attempts)
            VALUES (?, ?, CURRENT_TIMESTAMP, 0)
        ''', (did, handle))
    
    conn.commit()
    conn.close()
    
    print(f"Rebuilt cache from {len(posts_data)} existing posts")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "stats":
            view_cache_stats()
        elif command == "recent":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            view_recent_resolutions(limit)
        elif command == "clear":
            clear_failed_cache()
        elif command == "search" and len(sys.argv) > 2:
            search_term = sys.argv[2]
            search_cache(search_term)
        elif command == "rebuild":
            rebuild_cache_from_posts()
        else:
            print("Usage: python cache_manager.py [stats|recent [limit]|clear|search <term>|rebuild]")
    else:
        view_cache_stats()
