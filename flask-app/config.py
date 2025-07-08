# Configuration for Flask app
import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Database configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'mariadb'
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or 'bsky_db'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'bsky_user'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'bsky_password'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
    
    # Application settings
    POSTS_PER_PAGE = 20
    MAX_SEARCH_RESULTS = 1000
