from flask import Flask, render_template, request, jsonify
import mysql.connector
from datetime import datetime
from collections import Counter
import re
import pytz

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


@app.route('/api/political-sentiment')
def political_sentiment():
    """Analyze political sentiment in posts - optimized version"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Much faster approach: Use a few key phrases and combine them
        # Instead of checking every phrase individually
        
        # Key right-wing indicators (most common/distinctive)
        right_key_phrases = [
            "maga", "trump", "america first", "second amendment", "gun rights",
            "border security", "traditional values", "deep state"
        ]
        
        # Key left-wing indicators (most common/distinctive) 
        left_key_phrases = [
            "social justice", "climate change", "black lives matter", "lgbtq",
            "medicare for all", "wealth inequality", "defund police", "reproductive rights"
        ]
        
        # Single query for right-wing posts using key phrases only
        right_conditions = " OR ".join([f"LOWER(text) LIKE %s" for _ in right_key_phrases])
        right_params = [f"%{phrase.lower()}%" for phrase in right_key_phrases]
        
        cursor.execute(f"""
            SELECT COUNT(DISTINCT id) as count, COUNT(DISTINCT author_did) as unique_authors
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND ({right_conditions})
        """, right_params)
        right_stats = cursor.fetchone()
        
        # Single query for left-wing posts using key phrases only
        left_conditions = " OR ".join([f"LOWER(text) LIKE %s" for _ in left_key_phrases])
        left_params = [f"%{phrase.lower()}%" for phrase in left_key_phrases]
        
        cursor.execute(f"""
            SELECT COUNT(DISTINCT id) as count, COUNT(DISTINCT author_did) as unique_authors
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND ({left_conditions})
        """, left_params)
        left_stats = cursor.fetchone()
        
        # Simplified timeline - just get daily political activity
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as posts_count
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND (
                LOWER(text) LIKE '%trump%' OR LOWER(text) LIKE '%biden%' OR 
                LOWER(text) LIKE '%climate%' OR LOWER(text) LIKE '%politics%' OR
                LOWER(text) LIKE '%election%' OR LOWER(text) LIKE '%vote%'
            )
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        timeline = [{'date': row[0].isoformat(), 'count': row[1]} 
                   for row in cursor.fetchall()]
        
        # Quick phrase detection for trending topics (limit to recent posts)
        cursor.execute("""
            SELECT text
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND (
                LOWER(text) LIKE '%trump%' OR LOWER(text) LIKE '%biden%' OR 
                LOWER(text) LIKE '%climate%' OR LOWER(text) LIKE '%abortion%' OR
                LOWER(text) LIKE '%gun%' OR LOWER(text) LIKE '%immigration%'
            )
            LIMIT 500
        """)
        
        recent_posts = cursor.fetchall()
        phrase_counts = {}
        
        # Count key phrases in recent political posts
        check_phrases = [
            "trump", "biden", "climate change", "abortion", "gun rights", 
            "immigration", "healthcare", "economy", "democracy", "election"
        ]
        
        for phrase in check_phrases:
            count = 0
            for (text,) in recent_posts:
                if phrase.lower() in text.lower():
                    count += 1
            if count > 0:
                phrase_counts[phrase] = count
        
        # Convert to list and sort
        trending_phrases = [{'phrase': phrase, 'count': count} 
                          for phrase, count in phrase_counts.items()]
        trending_phrases.sort(key=lambda x: x['count'], reverse=True)
        
        conn.close()
        
        return jsonify({
            'right_wing': {
                'posts': right_stats[0] or 0,
                'unique_authors': right_stats[1] or 0
            },
            'left_wing': {
                'posts': left_stats[0] or 0, 
                'unique_authors': left_stats[1] or 0
            },
            'timeline': timeline,
            'trending_phrases': trending_phrases[:8]
        })
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"Political sentiment error: {e}")  # Debug logging
        return jsonify({'error': str(e)}), 500


@app.route('/api/trending-topics')
def trending_topics():
    """Get trending topics and keywords"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        time_period = request.args.get('period', '24h')
        
        # Convert period to MySQL interval
        if time_period == '1h':
            interval = 'INTERVAL 1 HOUR'
        elif time_period == '6h':
            interval = 'INTERVAL 6 HOUR' 
        elif time_period == '24h':
            interval = 'INTERVAL 24 HOUR'
        elif time_period == '7d':
            interval = 'INTERVAL 7 DAY'
        else:
            interval = 'INTERVAL 24 HOUR'
        
        cursor = conn.cursor()
        
        # Get recent posts for keyword analysis
        cursor.execute(f"""
            SELECT text 
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), {interval})
            AND text IS NOT NULL
            LIMIT 5000
        """)
        
        posts_text = cursor.fetchall()
        
        # Analyze keywords
        word_freq = Counter()
        for (text,) in posts_text:
            words = re.findall(r'\b\w+\b', text.lower())
            word_freq.update(word for word in words 
                           if word not in STOP_WORDS and len(word) > 3)
        
        # Get most frequent hashtags/mentions
        cursor.execute(f"""
            SELECT text
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), {interval})
            AND (text LIKE '%#%' OR text LIKE '%@%')
            LIMIT 2000
        """)
        
        hashtag_posts = cursor.fetchall()
        hashtags = Counter()
        mentions = Counter()
        
        for (text,) in hashtag_posts:
            # Extract hashtags
            hashtag_matches = re.findall(r'#(\w+)', text)
            hashtags.update(hashtag_matches)
            
            # Extract mentions
            mention_matches = re.findall(r'@(\w+)', text)
            mentions.update(mention_matches)
        
        conn.close()
        
        return jsonify({
            'period': time_period,
            'trending_keywords': [{'word': word, 'count': count} 
                                for word, count in word_freq.most_common(20)],
            'trending_hashtags': [{'hashtag': tag, 'count': count} 
                                for tag, count in hashtags.most_common(10)],
            'trending_mentions': [{'mention': mention, 'count': count} 
                                for mention, count in mentions.most_common(10)]
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/user-behavior')
def user_behavior():
    """Analyze user posting behavior and patterns"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Top posters in last 24 hours
        cursor.execute("""
            SELECT 
                author_handle,
                author_did,
                COUNT(*) as post_count,
                MIN(created_at) as first_post,
                MAX(created_at) as last_post
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND author_handle IS NOT NULL
            GROUP BY author_handle, author_did
            HAVING post_count >= 5
            ORDER BY post_count DESC
            LIMIT 20
        """)
        
        top_posters = []
        for row in cursor.fetchall():
            handle, did, count, first, last = row
            time_diff = (last - first).total_seconds() / 3600 if last and first else 0
            
            # Convert UTC timestamps to Eastern Time
            first_et = utc_to_eastern(first) if first else None
            last_et = utc_to_eastern(last) if last else None
            
            top_posters.append({
                'handle': handle,
                'did': did,
                'post_count': count,
                'posts_per_hour': round(count / max(time_diff, 1), 2),
                'first_post': first_et.isoformat() if first_et else None,
                'last_post': last_et.isoformat() if last_et else None
            })
        
        # Posting patterns by hour
        cursor.execute("""
            SELECT 
                HOUR(created_at) as hour,
                COUNT(*) as post_count
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY HOUR(created_at)
            ORDER BY hour
        """)
        
        hourly_activity = [{'hour': row[0], 'count': row[1]} 
                          for row in cursor.fetchall()]
        
        # Language distribution for active users
        cursor.execute("""
            SELECT 
                language,
                COUNT(*) as count,
                COUNT(DISTINCT author_did) as unique_authors
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
            LIMIT 10
        """)
        
        language_activity = [{'language': row[0], 'posts': row[1], 'users': row[2]} 
                           for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'top_posters': top_posters,
            'hourly_activity': hourly_activity,
            'language_activity': language_activity
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/content-analysis')
def content_analysis():
    """Analyze content patterns and themes"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Average post length by language
        cursor.execute("""
            SELECT 
                language,
                AVG(CHAR_LENGTH(text)) as avg_length,
                COUNT(*) as post_count
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND text IS NOT NULL
            AND language IS NOT NULL
            GROUP BY language
            HAVING post_count >= 10
            ORDER BY avg_length DESC
        """)
        
        length_by_language = [{'language': row[0], 'avg_length': round(row[1], 1), 'posts': row[2]} 
                            for row in cursor.fetchall()]
        
        # Posts with links vs without
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN text LIKE '%http%' THEN 'With Links'
                    ELSE 'Text Only'
                END as post_type,
                COUNT(*) as count
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY post_type
        """)
        
        link_analysis = [{'type': row[0], 'count': row[1]} 
                        for row in cursor.fetchall()]
        
        # Sentiment indicators (simple keyword-based)
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN text REGEXP '😀|😊|😍|🎉|❤️|💕|😁|😃|😄|happy|love|great|amazing|awesome|wonderful' THEN 'Positive'
                    WHEN text REGEXP '😢|😭|😡|😤|💔|😞|😔|sad|angry|hate|terrible|awful|horrible|bad' THEN 'Negative'
                    ELSE 'Neutral'
                END as sentiment,
                COUNT(*) as count
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND text IS NOT NULL
            GROUP BY sentiment
        """)
        
        sentiment_analysis = [{'sentiment': row[0], 'count': row[1]} 
                            for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'length_by_language': length_by_language,
            'link_analysis': link_analysis,
            'sentiment_analysis': sentiment_analysis
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/network-analysis')
def network_analysis():
    """Analyze user interaction networks and patterns"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Most mentioned users
        cursor.execute("""
            SELECT text 
            FROM posts 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND text LIKE '%@%'
            LIMIT 1000
        """)
        
        mention_posts = cursor.fetchall()
        mentions = Counter()
        
        for (text,) in mention_posts:
            mention_matches = re.findall(r'@(\w+)', text)
            mentions.update(mention_matches)
        
        # Authors who post most frequently together (same timeframes)
        cursor.execute("""
            SELECT 
                p1.author_handle as user1,
                p2.author_handle as user2,
                COUNT(*) as concurrent_posts
            FROM posts p1
            JOIN posts p2 ON p1.author_handle != p2.author_handle
                AND ABS(TIMESTAMPDIFF(MINUTE, p1.created_at, p2.created_at)) <= 5
            WHERE p1.created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND p1.author_handle IS NOT NULL
            AND p2.author_handle IS NOT NULL
            GROUP BY p1.author_handle, p2.author_handle
            HAVING concurrent_posts >= 3
            ORDER BY concurrent_posts DESC
            LIMIT 20
        """)
        
        concurrent_posters = [{'user1': row[0], 'user2': row[1], 'count': row[2]} 
                            for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'most_mentioned': [{'user': user, 'mentions': count} 
                             for user, count in mentions.most_common(15)],
            'concurrent_posters': concurrent_posters
        })
        
    except Exception as e:
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
