import sqlite3
import json
from datetime import datetime

def view_posts(limit=10):
    """View recent posts from the database"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT author_did, author_handle, text, created_at, language, post_uri, saved_at 
        FROM posts 
        ORDER BY saved_at DESC 
        LIMIT ?
    ''', (limit,))
    
    posts = cursor.fetchall()
    conn.close()
    
    print(f"=== Last {len(posts)} posts ===\n")
    
    for i, (author_did, author_handle, text, created_at, language, post_uri, saved_at) in enumerate(posts, 1):
        handle_display = f"@{author_handle}" if author_handle else author_did
        print(f"{i}. Author: {handle_display}")
        print(f"   Text: {text}")
        print(f"   Created: {created_at}")
        print(f"   Language: {language}")
        print(f"   URI: {post_uri}")
        print(f"   Saved: {saved_at}")
        print("-" * 80)

def get_stats():
    """Get database statistics"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM posts')
    total_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT author_did) FROM posts')
    unique_authors = cursor.fetchone()[0]
    
    cursor.execute('SELECT language, COUNT(*) FROM posts GROUP BY language ORDER BY COUNT(*) DESC LIMIT 10')
    language_stats = cursor.fetchall()
    
    conn.close()
    
    print(f"=== Database Statistics ===")
    print(f"Total posts: {total_posts}")
    print(f"Unique authors: {unique_authors}")
    print(f"\nTop languages:")
    for lang, count in language_stats:
        print(f"  {lang or 'Unknown'}: {count}")

def search_posts(search_term, limit=10):
    """Search posts by text content"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT author_did, author_handle, text, created_at, language 
        FROM posts 
        WHERE text LIKE ? 
        ORDER BY saved_at DESC 
        LIMIT ?
    ''', (f'%{search_term}%', limit))
    
    posts = cursor.fetchall()
    conn.close()
    
    print(f"=== Posts containing '{search_term}' ===\n")
    
    for i, (author_did, author_handle, text, created_at, language) in enumerate(posts, 1):
        handle_display = f"@{author_handle}" if author_handle else author_did
        print(f"{i}. Author: {handle_display}")
        print(f"   Text: {text}")
        print(f"   Created: {created_at}")
        print(f"   Language: {language}")
        print("-" * 80)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "stats":
            get_stats()
        elif command == "search" and len(sys.argv) > 2:
            search_term = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            search_posts(search_term, limit)
        elif command == "view":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_posts(limit)
        else:
            print("Usage: python query_posts.py [stats|view [limit]|search <term> [limit]]")
    else:
        view_posts()
