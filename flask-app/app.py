from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import mysql.connector
from datetime import datetime
from collections import Counter
import re
import pytz
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")

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

# Political keyword phrases for analysis (more contextual than single words)
RIGHT_WING_KEYWORDS = [
    # Trump & MAGA movement
    "make america great again", "maga", "trump 2024", "america first", 
    "drain the swamp", "deep state conspiracy", "stop the steal", "fake news media",
    "mainstream media lies", "liberal media bias", "election was stolen",
    
    # Conservative values & religion
    "traditional family values", "christian values", "religious freedom", "moral decay",
    "defend the constitution", "founding fathers intended", "constitutional rights",
    "god and country", "prayer in schools", "christian nation",
    
    # Gun rights
    "second amendment rights", "shall not be infringed", "gun grabbers", 
    "defend 2a", "right to bear arms", "good guy with gun", "constitutional carry",
    "gun control doesn't work", "criminals don't follow laws",
    
    # Immigration & border
    "secure the border", "illegal aliens", "build the wall", "mass deportation",
    "border crisis", "invasion at border", "merit based immigration",
    "chain migration", "sanctuary cities dangerous", "america first immigration",
    
    # Economic conservatism
    "free market capitalism", "small government", "lower taxes", "government overreach",
    "fiscal responsibility", "balanced budget", "job creators", "reduce regulations",
    "socialist policies", "government handouts", "welfare state",
    
    # Anti-left sentiments
    "woke ideology", "cancel culture", "virtue signaling", "identity politics",
    "cultural marxism", "critical race theory", "grooming children", "parental rights",
    "gender ideology", "biological reality", "protect our children", "indoctrination",
    
    # Law enforcement & military
    "back the blue", "blue lives matter", "law and order", "defund police insane",
    "support our troops", "strong military", "peace through strength",
    "thin blue line", "law enforcement heroes",
    
    # Nationalism & sovereignty
    "america first", "national sovereignty", "globalist agenda", "new world order",
    "drain the swamp", "deep state", "patriotic americans", "real americans",
    "silent majority", "forgotten americans", "common sense conservative"
]

LEFT_WING_KEYWORDS = [
    # Social justice & civil rights
    "social justice", "racial justice", "systemic racism", "black lives matter",
    "police brutality", "criminal justice reform", "prison abolition", 
    "defund the police", "restorative justice", "racial equity",
    
    # LGBTQ+ rights
    "lgbtq rights", "transgender rights", "marriage equality", "gender affirming care",
    "conversion therapy ban", "pride month", "love is love", "trans rights human rights",
    "protect trans kids", "drag queen story hour",
    
    # Women's rights & reproductive freedom
    "reproductive rights", "bodily autonomy", "abortion access", "planned parenthood",
    "my body my choice", "reproductive freedom", "women's rights", "gender equality",
    "pay gap", "glass ceiling", "reproductive justice",
    
    # Climate & environment
    "climate change real", "climate crisis", "green new deal", "renewable energy",
    "fossil fuel industry", "environmental justice", "carbon emissions", 
    "climate action now", "save the planet", "sustainable future",
    
    # Economic justice
    "wealth inequality", "income inequality", "tax the rich", "billionaire class",
    "living wage", "minimum wage increase", "workers rights", "union strong",
    "medicare for all", "universal healthcare", "student debt forgiveness",
    "affordable housing", "rent control", "universal basic income",
    
    # Progressive politics
    "democratic socialism", "progressive agenda", "fight for justice",
    "power to the people", "grassroots movement", "political revolution",
    "anti capitalism", "corporate greed", "wall street corruption",
    
    # Immigration & refugee rights
    "immigration reform", "pathway to citizenship", "dreamers deserve", 
    "refugee rights", "family separation", "kids in cages", "sanctuary cities",
    "no human is illegal", "border patrol abuse",
    
    # Anti-establishment
    "eat the rich", "abolish ice", "abolish prisons", "defund military",
    "corporate accountability", "big pharma greed", "healthcare human right",
    "housing human right", "food justice", "water is life",
    
    # International & peace
    "anti war", "military industrial complex", "stop bombing", "peace not war",
    "human rights violations", "international law", "war crimes", 
    "indigenous rights", "land back", "decolonize", "global solidarity",
    
    # Modern progressive terms
    "intersectional feminism", "check your privilege", "systemic oppression",
    "mutual aid", "community care", "harm reduction", "prison industrial complex",
    "disability justice", "neurodiversity", "accessibility matters"
]

STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
    'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
    'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our',
    'their', 'mine', 'yours', 'hers', 'ours', 'theirs', 'what', 'which', 'who',
    'whom', 'whose', 'where', 'when', 'why', 'how', 'all', 'any', 'both', 'each',
    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
    'own', 'same', 'so', 'than', 'too', 'very', 'can', 'just', 'now', 'get', 'like'
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

def utc_to_eastern(dt):
    """Convert UTC datetime to Eastern Time"""
    if not dt:
        return None
    
    # Define timezones
    utc = pytz.timezone('UTC')
    eastern = pytz.timezone('US/Eastern')
    
    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = utc.localize(dt)
    
    # Convert to Eastern Time
    return dt.astimezone(eastern)

def format_datetime(dt) -> str:
    """Format datetime for display in Michigan timezone (Eastern Time)"""
    if not dt:
        return "Unknown"
    
    # Define Michigan timezone (Eastern Time)
    eastern = pytz.timezone('US/Eastern')
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except Exception:
            return dt
    
    # Convert to Michigan timezone if datetime has timezone info
    if dt.tzinfo:
        # Convert to Eastern time
        dt_eastern = dt.astimezone(eastern)
    else:
        # Assume UTC if no timezone info and convert to Eastern
        utc = pytz.UTC
        dt_utc = utc.localize(dt)
        dt_eastern = dt_utc.astimezone(eastern)
    
    # Calculate time difference using Eastern time
    now_eastern = datetime.now(eastern)
    diff = now_eastern - dt_eastern
    
    # Handle negative differences (future dates)
    if diff.total_seconds() < 0:
        return dt_eastern.strftime('%Y-%m-%d %I:%M %p ET')
    
    # Get total seconds for accurate calculations
    total_seconds = diff.total_seconds()
    
    if diff.days > 7:
        return dt_eastern.strftime('%Y-%m-%d %I:%M %p ET')
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif total_seconds > 3600:
        hours = int(total_seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif total_seconds > 60:
        minutes = int(total_seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return f"{round(total_seconds)} seconds ago"

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
        
        # Check if political analysis is requested (optional for performance)
        include_political = request.args.get('include_political', 'true').lower() == 'true'
        
        # Format posts for display
        posts = []
        for post_data in posts_data:
            post_id, author_did, author_handle, text, created_at, language, post_uri, saved_at = post_data
            
            # Only do political analysis if requested (saves processing time)
            political_analysis = None
            political_leaning = 'neutral'
            political_phrases = {'right_wing': [], 'left_wing': [], 'score': 0}
            
            if include_political:
                political_analysis = detect_political_phrases(text)
                
                # Determine political leaning
                if political_analysis['total_score'] > 0:
                    political_leaning = 'right_wing'
                elif political_analysis['total_score'] < 0:
                    political_leaning = 'left_wing'
                
                political_phrases = {
                    'right_wing': political_analysis['right_wing'][:3],  # Show max 3 phrases
                    'left_wing': political_analysis['left_wing'][:3],
                    'score': political_analysis['total_score']
                }
            
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
                'saved_at_display': format_datetime(saved_at),
                'political_leaning': political_leaning,
                'political_phrases': political_phrases
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

@app.route('/analytics')
def analytics():
    """Analytics dashboard page"""
    return render_template('analytics.html')

@app.route('/ingress')
def ingress():
    """Real-time data ingress monitoring page"""
    return render_template('ingress.html')

@app.route('/api/ingress-stats')
def ingress_stats():
    """Get real-time ingress statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Posts in the last minute
        cursor.execute('''
            SELECT COUNT(*) FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 1 MINUTE)
        ''')
        posts_last_minute = cursor.fetchone()[0]
        
        # Posts in the last 5 minutes
        cursor.execute('''
            SELECT COUNT(*) FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        ''')
        posts_last_5min = cursor.fetchone()[0]
        
        # Posts in the last hour
        cursor.execute('''
            SELECT COUNT(*) FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
        ''')
        posts_last_hour = cursor.fetchone()[0]
        
        # Posts today
        cursor.execute('''
            SELECT COUNT(*) FROM posts 
            WHERE DATE(saved_at) = CURDATE()
        ''')
        posts_today = cursor.fetchone()[0]
        
        # Current ingress rate (posts per minute) - use actual last minute count
        ingress_rate = posts_last_minute
        
        # 5-minute average for comparison
        ingress_rate_5min_avg = posts_last_5min / 5.0 if posts_last_5min else 0
        
        # Languages in last 5 minutes
        cursor.execute('''
            SELECT language, COUNT(*) as count 
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            AND language IS NOT NULL 
            GROUP BY language 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        recent_languages = [{'language': lang or 'Unknown', 'count': count} 
                          for lang, count in cursor.fetchall()]
        
        # Top authors in last 5 minutes
        cursor.execute('''
            SELECT author_handle, COUNT(*) as count 
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            AND author_handle IS NOT NULL 
            GROUP BY author_handle 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        top_recent_authors = [{'handle': author, 'post_count': count, 'display_name': ''} 
                            for author, count in cursor.fetchall()]
        
        # Active authors today
        cursor.execute('''
            SELECT COUNT(DISTINCT author_did) FROM posts 
            WHERE DATE(saved_at) = CURDATE()
        ''')
        active_authors_today = cursor.fetchone()[0]
        
        # New authors today (authors who posted for the first time today)
        cursor.execute('''
            SELECT COUNT(DISTINCT p1.author_did) 
            FROM posts p1
            WHERE DATE(p1.saved_at) = CURDATE()
            AND NOT EXISTS (
                SELECT 1 FROM posts p2 
                WHERE p2.author_did = p1.author_did 
                AND DATE(p2.saved_at) < CURDATE()
            )
        ''')
        new_authors_today = cursor.fetchone()[0]
        
        # Most recent posts (last 10)
        cursor.execute('''
            SELECT author_handle, text, saved_at, language
            FROM posts 
            ORDER BY saved_at DESC 
            LIMIT 10
        ''')
        recent_posts = []
        for author, text, saved_at, language in cursor.fetchall():
            recent_posts.append({
                'author': author or 'Unknown',
                'text': format_post_text(text, 100),
                'saved_at': format_datetime(saved_at),
                'language': language or 'Unknown'
            })
        
        conn.close()
        
        return jsonify({
            'posts_per_minute': posts_last_minute,  # Actual posts in last minute
            'posts_per_minute_5min_avg': round(ingress_rate_5min_avg, 2),  # 5-minute average
            'posts_last_minute': posts_last_minute,
            'posts_last_5min': posts_last_5min,
            'posts_last_hour': posts_last_hour,
            'total_today': posts_today,
            'last_hour': posts_last_hour,
            'ingress_rate': posts_last_minute,  # Match posts_per_minute for consistency
            'recent_languages': recent_languages,
            'top_recent_authors': top_recent_authors,
            'recent_posts': recent_posts,
            'timestamp': datetime.now().isoformat(),
            # Author metrics for JavaScript
            'new_authors_today': new_authors_today,
            'active_authors_now': active_authors_today,
            'top_active': top_recent_authors,
            # Additional fields the JS expects
            'posts_per_minute_change': 0,  # Would need historical data to calculate
            'total_today_change': 0,
            'last_hour_change': 0,
            'errors_per_minute': 0,
            'errors_per_minute_change': 0,
            'db_write_rate': posts_last_minute,  # Use actual posts per minute
            'db_queue_size': 0,
            'db_usage_percent': 45  # Mock value
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ingress-timeline')
def ingress_timeline():
    """Get timeline data for ingress charts"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Posts per minute for the last hour
        cursor.execute('''
            SELECT 
                DATE_FORMAT(saved_at, '%Y-%m-%d %H:%i:00') as minute,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            GROUP BY DATE_FORMAT(saved_at, '%Y-%m-%d %H:%i:00')
            ORDER BY minute
        ''')
        
        minute_data = []
        for minute_str, count in cursor.fetchall():
            minute_data.append({
                'time': minute_str,
                'count': count
            })
        
        # Posts per 5-minute interval for the last 4 hours
        cursor.execute('''
            SELECT 
                DATE_FORMAT(saved_at, '%Y-%m-%d %H:%i:00') as time_slot,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 4 HOUR)
            GROUP BY FLOOR(UNIX_TIMESTAMP(saved_at) / 300)
            ORDER BY time_slot
        ''')
        
        interval_data = []
        for time_slot, count in cursor.fetchall():
            interval_data.append({
                'time': time_slot,
                'count': count
            })
        
        # Language distribution over last hour
        cursor.execute('''
            SELECT 
                language,
                DATE_FORMAT(saved_at, '%Y-%m-%d %H:%i:00') as minute,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            AND language IS NOT NULL
            GROUP BY language, DATE_FORMAT(saved_at, '%Y-%m-%d %H:%i:00')
            ORDER BY minute, count DESC
        ''')
        
        language_timeline = {}
        for language, minute, count in cursor.fetchall():
            if language not in language_timeline:
                language_timeline[language] = []
            language_timeline[language].append({
                'time': minute,
                'count': count
            })
        
        conn.close()
        
        return jsonify({
            'minute_data': minute_data,
            'interval_data': interval_data,
            'language_timeline': language_timeline
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

def detect_political_phrases(text):
    """Detect political phrases in text and return matches - optimized version"""
    if not text:
        return {'right_wing': [], 'left_wing': [], 'total_score': 0}
    
    text_lower = text.lower()
    detected = {'right_wing': [], 'left_wing': [], 'total_score': 0}
    
    # Use only key phrases for faster detection
    key_right_phrases = [
        "maga", "trump", "america first", "gun rights", "border security",
        "traditional values", "deep state", "fake news"
    ]
    
    key_left_phrases = [
        "social justice", "climate change", "black lives matter", "lgbtq",
        "medicare for all", "wealth inequality", "defund police"
    ]
    
    # Check for right-wing phrases (faster lookup)
    for phrase in key_right_phrases:
        if phrase in text_lower:
            detected['right_wing'].append(phrase)
            detected['total_score'] += 1
    
    # Check for left-wing phrases (faster lookup)
    for phrase in key_left_phrases:
        if phrase in text_lower:
            detected['left_wing'].append(phrase)
            detected['total_score'] -= 1  # Negative score for left-wing
    
    return detected

# Socket.IO event handlers for real-time ingress monitoring
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected to ingress monitoring')
    emit('status', {'message': 'Connected to real-time ingress monitoring'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected from ingress monitoring')

@socketio.on('start_monitoring')
def handle_start_monitoring():
    """Start real-time monitoring for this client"""
    print('Starting real-time monitoring for client')
    emit('monitoring_started', {'status': 'success'})

@socketio.on('stop_monitoring')
def handle_stop_monitoring():
    """Stop real-time monitoring for this client"""
    print('Stopping real-time monitoring for client')
    emit('monitoring_stopped', {'status': 'success'})

# Background task for broadcasting real-time data
def background_ingress_monitor():
    """Background task to broadcast ingress data to all connected clients"""
    while True:
        try:
            # Get fresh ingress data
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                
                # Get current metrics
                cursor.execute('SELECT COUNT(*) FROM posts WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 1 MINUTE)')
                posts_last_minute = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM posts WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)')
                posts_last_5min = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM posts WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)')
                posts_last_hour = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM posts WHERE DATE(saved_at) = CURDATE()')
                posts_today = cursor.fetchone()[0]
                
                ingress_rate = posts_last_minute
                
                # 5-minute average for comparison
                ingress_rate_5min_avg = posts_last_5min / 5.0 if posts_last_5min else 0
                
                # Get recent languages
                cursor.execute('''
                    SELECT language, COUNT(*) as count 
                    FROM posts 
                    WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                    AND language IS NOT NULL 
                    GROUP BY language 
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                recent_languages = [{'language': lang or 'Unknown', 'count': count} 
                                  for lang, count in cursor.fetchall()]
                
                # Get active authors
                cursor.execute('''
                    SELECT author_handle, COUNT(*) as count 
                    FROM posts 
                    WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                    AND author_handle IS NOT NULL 
                    GROUP BY author_handle 
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                top_active_authors = [{'handle': author, 'post_count': count, 'display_name': ''} 
                                    for author, count in cursor.fetchall()]
                
                # Get most recent posts
                cursor.execute('''
                    SELECT author_handle, text, saved_at, language
                    FROM posts 
                    ORDER BY saved_at DESC 
                    LIMIT 5
                ''')
                recent_posts = []
                for author, text, saved_at, language in cursor.fetchall():
                    recent_posts.append({
                        'author': author or 'Unknown',
                        'text': format_post_text(text, 100),
                        'saved_at': format_datetime(saved_at),
                        'language': language or 'Unknown'
                    })
                
                conn.close()
                
                # Broadcast data to all connected clients
                socketio.emit('ingress_update', {
                    'posts_per_minute': posts_last_minute,  # Actual posts in last minute
                    'posts_per_minute_5min_avg': round(ingress_rate_5min_avg, 2),  # 5-minute average
                    'posts_last_minute': posts_last_minute,
                    'posts_last_5min': posts_last_5min,
                    'posts_last_hour': posts_last_hour,
                    'total_today': posts_today,
                    'last_hour': posts_last_hour,
                    'languages': recent_languages,
                    'top_active': top_active_authors,
                    'recent_posts': recent_posts,
                    'timestamp': datetime.now().isoformat(),
                    'db_write_rate': posts_last_minute,  # Use actual posts per minute
                    'db_queue_size': 0,
                    'db_usage_percent': 45
                })
                
        except Exception as e:
            print(f"Error in background monitor: {e}")
            socketio.emit('error', {'message': str(e)})
        
        # Wait 3 seconds before next update
        time.sleep(3)

# Start background monitoring thread
monitor_thread = threading.Thread(target=background_ingress_monitor, daemon=True)
monitor_thread.start()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
