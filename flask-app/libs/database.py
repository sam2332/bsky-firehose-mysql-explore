
import mysql.connector
# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306,
    'charset': 'utf8mb4',
    'autocommit': True
}

def get_db_connection():
    """Get database connection with proper error handling"""
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return None