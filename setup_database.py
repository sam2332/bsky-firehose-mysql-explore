#!/usr/bin/env python3
"""
Database setup script for MariaDB
This script initializes the database with the correct schema and sets up initial configuration.
"""

import os
import mysql.connector
from mysql.connector import Error
import sqlite3
import json
from datetime import datetime

# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306
}

def wait_for_mysql():
    """Wait for MySQL to be available"""
    import time
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            connection = mysql.connector.connect(
                host=MYSQL_CONFIG['host'],
                user=MYSQL_CONFIG['user'],
                password=MYSQL_CONFIG['password'],
                port=MYSQL_CONFIG['port']
            )
            if connection.is_connected():
                print("✅ Successfully connected to MariaDB")
                connection.close()
                return True
        except Error as e:
            print(f"⏳ Waiting for MariaDB... (attempt {retry_count + 1}/{max_retries})")
            time.sleep(2)
            retry_count += 1
    
    raise Exception("❌ Could not connect to MariaDB after maximum retries")

def create_database_schema():
    """Create the database schema based on the existing SQLite structure"""
    
    # First, let's examine the SQLite database to understand the schema
    sqlite_path = '/workspace/bsky_posts.db'
    
    if not os.path.exists(sqlite_path):
        print("⚠️ No SQLite database found. Creating fresh schema...")
        create_fresh_schema()
        return
    
    print("📊 Analyzing existing SQLite database...")
    
    try:
        # Connect to SQLite to get schema
        sqlite_conn = sqlite3.connect(sqlite_path)
        cursor = sqlite_conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables in SQLite database")
        
        # Connect to MySQL
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor()
        
        # Create tables based on SQLite schema
        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            print(f"🔄 Processing table: {table_name}")
            
            # Get SQLite table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Convert SQLite schema to MySQL
            mysql_columns = []
            for col in columns:
                col_name = col[1]
                col_type = col[2].upper()
                is_nullable = not col[3]  # SQLite: 0 = nullable, 1 = not null
                is_pk = col[5]  # Primary key flag
                
                # Convert SQLite types to MySQL types
                if 'INTEGER' in col_type:
                    if is_pk:
                        mysql_type = 'INT AUTO_INCREMENT PRIMARY KEY'
                    else:
                        mysql_type = 'INT'
                elif 'TEXT' in col_type or 'VARCHAR' in col_type:
                    mysql_type = 'TEXT'
                elif 'REAL' in col_type or 'FLOAT' in col_type:
                    mysql_type = 'FLOAT'
                elif 'DATETIME' in col_type:
                    mysql_type = 'DATETIME'
                else:
                    mysql_type = 'TEXT'  # Default fallback
                
                null_constraint = '' if is_nullable and not is_pk else ' NOT NULL'
                mysql_columns.append(f"`{col_name}` {mysql_type}{null_constraint}")
            
            # Create table
            create_table_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(mysql_columns)})"
            print(f"Creating table: {create_table_sql}")
            mysql_cursor.execute(create_table_sql)
        
        mysql_conn.commit()
        print("✅ Database schema created successfully")
        
        # Close connections
        sqlite_conn.close()
        mysql_conn.close()
        
    except Error as e:
        print(f"❌ Error creating database schema: {e}")
        raise

def create_fresh_schema():
    """Create a fresh database schema for Bluesky posts"""
    
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = connection.cursor()
        
        # Create posts table (common structure for Bluesky monitoring)
        create_posts_table = """
        CREATE TABLE IF NOT EXISTS posts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uri VARCHAR(500) NOT NULL UNIQUE,
            cid VARCHAR(200),
            author_did VARCHAR(200),
            author_handle VARCHAR(100),
            text TEXT,
            created_at DATETIME,
            indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reply_count INT DEFAULT 0,
            repost_count INT DEFAULT 0,
            like_count INT DEFAULT 0,
            has_media BOOLEAN DEFAULT FALSE,
            media_count INT DEFAULT 0,
            language VARCHAR(10),
            labels JSON,
            INDEX idx_author_did (author_did),
            INDEX idx_created_at (created_at),
            INDEX idx_indexed_at (indexed_at)
        );
        """
        
        # Create authors table for better normalization
        create_authors_table = """
        CREATE TABLE IF NOT EXISTS authors (
            did VARCHAR(200) PRIMARY KEY,
            handle VARCHAR(100),
            display_name VARCHAR(200),
            description TEXT,
            avatar_url VARCHAR(500),
            follower_count INT DEFAULT 0,
            following_count INT DEFAULT 0,
            posts_count INT DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_handle (handle)
        );
        """
        
        # Create monitoring_stats table for tracking
        create_stats_table = """
        CREATE TABLE IF NOT EXISTS monitoring_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stat_date DATE UNIQUE,
            posts_processed INT DEFAULT 0,
            new_authors INT DEFAULT 0,
            total_posts INT DEFAULT 0,
            total_authors INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor.execute(create_posts_table)
        cursor.execute(create_authors_table)
        cursor.execute(create_stats_table)
        
        connection.commit()
        print("✅ Fresh database schema created successfully")
        
        connection.close()
        
    except Error as e:
        print(f"❌ Error creating fresh schema: {e}")
        raise

def main():
    print("🗄️ Setting up MariaDB database...")
    
    try:
        # Wait for MySQL to be ready
        wait_for_mysql()
        
        # Create database schema
        create_database_schema()
        
        print("🎉 Database setup completed successfully!")
        print("\n📋 Next steps:")
        print("  1. Run migration if you have existing SQLite data: python migrate_to_mysql.py")
        print("  2. Access phpMyAdmin at http://localhost:8080")
        print("  3. Start your Bluesky monitoring scripts!")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
