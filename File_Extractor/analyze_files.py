#!/usr/bin/env python3
"""
Utility script to analyze and query extracted files
"""

import mysql.connector
import os
from pathlib import Path
from collections import defaultdict, Counter
import argparse

# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306,
    'autocommit': True
}

def get_extraction_stats():
    """Get statistics about extracted files"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Total files extracted
        cursor.execute("SELECT COUNT(*) FROM extracted_files")
        total_files = cursor.fetchone()[0]
        
        # Files by type
        cursor.execute("""
            SELECT file_type, COUNT(*) as count 
            FROM extracted_files 
            GROUP BY file_type 
            ORDER BY count DESC
        """)
        files_by_type = cursor.fetchall()
        
        # Files by user (top 10)
        cursor.execute("""
            SELECT author_handle, COUNT(*) as count 
            FROM extracted_files 
            WHERE author_handle IS NOT NULL
            GROUP BY author_handle 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_users = cursor.fetchall()
        
        # Files by month
        cursor.execute("""
            SELECT DATE_FORMAT(created_at, '%Y-%m') as month, COUNT(*) as count
            FROM extracted_files 
            GROUP BY month 
            ORDER BY month DESC
        """)
        files_by_month = cursor.fetchall()
        
        # Total file size
        cursor.execute("SELECT SUM(file_size) FROM extracted_files WHERE file_size IS NOT NULL")
        total_size = cursor.fetchone()[0] or 0
        
        conn.close()
        
        print(f"📊 File Extraction Statistics")
        print(f"=" * 50)
        print(f"Total files extracted: {total_files:,}")
        print(f"Total size: {total_size / (1024*1024*1024):.2f} GB")
        print()
        
        print("📁 Files by type:")
        for file_type, count in files_by_type[:10]:
            print(f"  {file_type}: {count:,}")
        print()
        
        print("👥 Top users by file count:")
        for handle, count in top_users:
            print(f"  @{handle}: {count:,} files")
        print()
        
        print("📅 Files by month:")
        for month, count in files_by_month[:6]:
            print(f"  {month}: {count:,}")
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")

def search_files(user_handle=None, file_type=None, limit=20):
    """Search for extracted files"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        query = "SELECT author_handle, file_type, file_path, file_size, created_at FROM extracted_files WHERE 1=1"
        params = []
        
        if user_handle:
            query += " AND author_handle LIKE %s"
            params.append(f"%{user_handle}%")
        
        if file_type:
            query += " AND file_type LIKE %s"
            params.append(f"%{file_type}%")
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        conn.close()
        
        print(f"🔍 Search Results ({len(results)} files)")
        print(f"=" * 80)
        
        for handle, ftype, fpath, fsize, created in results:
            size_str = f"{fsize / 1024:.1f} KB" if fsize else "Unknown"
            print(f"@{handle or 'unknown'} | {ftype} | {size_str} | {created}")
            print(f"  📁 {fpath}")
            print()
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")

def check_file_integrity():
    """Check if files on disk match database records"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT file_path, file_size FROM extracted_files")
        files = cursor.fetchall()
        
        conn.close()
        
        missing_files = []
        size_mismatches = []
        
        for file_path, expected_size in files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
            elif expected_size:
                actual_size = os.path.getsize(file_path)
                if actual_size != expected_size:
                    size_mismatches.append((file_path, expected_size, actual_size))
        
        print(f"🔍 File Integrity Check")
        print(f"=" * 50)
        print(f"Total files in database: {len(files):,}")
        print(f"Missing files: {len(missing_files):,}")
        print(f"Size mismatches: {len(size_mismatches):,}")
        
        if missing_files:
            print("\n❌ Missing files:")
            for file_path in missing_files[:10]:
                print(f"  {file_path}")
            if len(missing_files) > 10:
                print(f"  ... and {len(missing_files) - 10} more")
        
        if size_mismatches:
            print("\n⚠️  Size mismatches:")
            for file_path, expected, actual in size_mismatches[:5]:
                print(f"  {file_path}: expected {expected}, actual {actual}")
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")

def list_user_files(user_handle, limit=50):
    """List files for a specific user"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_type, file_path, file_size, created_at 
            FROM extracted_files 
            WHERE author_handle = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (user_handle, limit))
        
        files = cursor.fetchall()
        conn.close()
        
        if not files:
            print(f"No files found for @{user_handle}")
            return
        
        print(f"📁 Files for @{user_handle} ({len(files)} files)")
        print(f"=" * 60)
        
        type_counts = Counter()
        total_size = 0
        
        for file_type, file_path, file_size, created in files:
            type_counts[file_type] += 1
            if file_size:
                total_size += file_size
            
            size_str = f"{file_size / 1024:.1f} KB" if file_size else "Unknown"
            print(f"{file_type} | {size_str} | {created}")
            print(f"  📁 {file_path}")
            print()
        
        print(f"📊 Summary:")
        print(f"Total files: {len(files)}")
        print(f"Total size: {total_size / (1024*1024):.2f} MB")
        print(f"File types: {dict(type_counts)}")
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Analyze extracted Bluesky files')
    parser.add_argument('--stats', action='store_true', help='Show extraction statistics')
    parser.add_argument('--search', action='store_true', help='Search files')
    parser.add_argument('--user', help='Filter by user handle')
    parser.add_argument('--type', help='Filter by file type')
    parser.add_argument('--limit', type=int, default=20, help='Limit results')
    parser.add_argument('--integrity', action='store_true', help='Check file integrity')
    parser.add_argument('--list-user', help='List files for specific user')
    
    args = parser.parse_args()
    
    if args.stats:
        get_extraction_stats()
    elif args.search:
        search_files(args.user, args.type, args.limit)
    elif args.integrity:
        check_file_integrity()
    elif args.list_user:
        list_user_files(args.list_user, args.limit)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
