from flask import Flask, render_template, request, jsonify
import mysql.connector
from datetime import datetime

app = Flask(__name__)

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

def format_post_text(text: str, max_length: int = 200) -> str:
    """Format post text for display"""
    if not text:
        return ""
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text

def format_datetime(dt) -> str:
    """Format datetime for display"""
    if not dt:
        return "Unknown"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except Exception:
            return dt
    
    # Calculate time difference
    now = datetime.utcnow()
    diff = now - dt.replace(tzinfo=None) if dt.tzinfo else now - dt
    
    if diff.days > 7:
        return dt.strftime('%Y-%m-%d %H:%M')
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Total posts
        cursor.execute('SELECT COUNT(*) FROM posts')
        total_posts = cursor.fetchone()[0]
        
        # Unique authors
        cursor.execute('SELECT COUNT(DISTINCT author_did) FROM posts')
        unique_authors = cursor.fetchone()[0]
        
        # Posts today
        cursor.execute('''
            SELECT COUNT(*) FROM posts 
            WHERE DATE(saved_at) = CURDATE()
        ''')
        posts_today = cursor.fetchone()[0]
        
        # Posts this week
        cursor.execute('''
            SELECT COUNT(*) FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ''')
        posts_week = cursor.fetchone()[0]
        
        # Top languages
        cursor.execute('''
            SELECT language, COUNT(*) as count 
            FROM posts 
            WHERE language IS NOT NULL 
            GROUP BY language 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        languages = [{'language': lang or 'Unknown', 'count': count} 
                    for lang, count in cursor.fetchall()]
        
        # Recent activity (posts per hour for last 24 hours)
        cursor.execute('''
            SELECT 
                HOUR(saved_at) as hour,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY HOUR(saved_at)
            ORDER BY hour
        ''')
        activity = [{'hour': hour, 'count': count} 
                   for hour, count in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'total_posts': total_posts,
            'unique_authors': unique_authors,
            'posts_today': posts_today,
            'posts_week': posts_week,
            'languages': languages,
            'activity': activity
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts')
def search_posts():
    """Search and filter posts"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get query parameters
        search_query = request.args.get('q', '').strip()
        language = request.args.get('language', '')
        author = request.args.get('author', '').strip()
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Max 100 per page
        sort_by = request.args.get('sort', 'saved_at')
        sort_order = request.args.get('order', 'desc')
        
        # Build WHERE clause
        where_conditions = []
        params = []
        
        # Text search
        if search_query:
            if len(search_query) > 2:
                # Use FULLTEXT search for longer queries
                where_conditions.append("MATCH(text) AGAINST(%s IN NATURAL LANGUAGE MODE)")
                params.append(search_query)
            else:
                # Use LIKE for shorter queries
                where_conditions.append("text LIKE %s")
                params.append(f"%{search_query}%")
        
        # Language filter
        if language:
            where_conditions.append("language = %s")
            params.append(language)
        
        # Author filter
        if author:
            where_conditions.append("(author_handle LIKE %s OR author_did LIKE %s)")
            params.extend([f"%{author}%", f"%{author}%"])
        
        # Date range filter
        if date_from:
            where_conditions.append("DATE(created_at) >= %s")
            params.append(date_from)
        
        if date_to:
            where_conditions.append("DATE(created_at) <= %s")
            params.append(date_to)
        
        # Build query
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Validate sort parameters
        valid_sort_fields = ['saved_at', 'created_at', 'author_handle', 'language']
        if sort_by not in valid_sort_fields:
            sort_by = 'saved_at'
        
        if sort_order.lower() not in ['asc', 'desc']:
            sort_order = 'desc'
        
        # Count total results
        count_query = f"SELECT COUNT(*) FROM posts {where_clause}"
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Calculate pagination
        offset = (page - 1) * per_page
        total_pages = (total_count + per_page - 1) // per_page
        
        # Get posts
        posts_query = f"""
            SELECT 
                id, author_did, author_handle, text, created_at, 
                language, post_uri, saved_at
            FROM posts 
            {where_clause}
            ORDER BY {sort_by} {sort_order.upper()}
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(posts_query, params + [per_page, offset])
        posts_data = cursor.fetchall()
        
        # Format posts for display
        posts = []
        for post_data in posts_data:
            post_id, author_did, author_handle, text, created_at, language, post_uri, saved_at = post_data
            
            posts.append({
                'id': post_id,
                'author_did': author_did,
                'author_handle': author_handle or 'Unknown',
                'author_display': f"@{author_handle}" if author_handle else author_did[:20] + "...",
                'text': format_post_text(text),
                'text_full': text,
                'created_at': created_at.isoformat() if created_at else None,
                'created_at_display': format_datetime(created_at),
                'language': language or 'Unknown',
                'post_uri': post_uri,
                'saved_at': saved_at.isoformat() if saved_at else None,
                'saved_at_display': format_datetime(saved_at)
            })
        
        conn.close()
        
        return jsonify({
            'posts': posts,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            },
            'query_info': {
                'search_query': search_query,
                'language': language,
                'author': author,
                'date_from': date_from,
                'date_to': date_to,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/languages')
def get_languages():
    """Get available languages for filtering"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT language, COUNT(*) as count 
            FROM posts 
            WHERE language IS NOT NULL 
            GROUP BY language 
            ORDER BY count DESC
        ''')
        
        languages = [{'code': lang, 'count': count, 'name': lang.upper() if lang else 'Unknown'} 
                    for lang, count in cursor.fetchall()]
        
        conn.close()
        return jsonify({'languages': languages})
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/authors')
def get_authors():
    """Get authors for autocomplete"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'authors': []})
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT author_handle, author_did, COUNT(*) as post_count
            FROM posts 
            WHERE (author_handle LIKE %s OR author_did LIKE %s)
            AND author_handle IS NOT NULL
            GROUP BY author_handle, author_did
            ORDER BY post_count DESC
            LIMIT 10
        ''', [f"%{query}%", f"%{query}%"])
        
        authors = [{'handle': handle, 'did': did, 'post_count': count} 
                  for handle, did, count in cursor.fetchall()]
        
        conn.close()
        return jsonify({'authors': authors})
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
