from flask import render_template, jsonify, request
from libs.database import get_shared_database_class
from datetime import datetime, timedelta
from flask_socketio import emit
import time
import re
import json
from decimal import Decimal
import pytz


def decimal_converter(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def convert_to_eastern(utc_datetime):
    """Convert UTC datetime to Eastern timezone"""
    if utc_datetime is None:
        return None
    
    try:
        # Import zoneinfo for timezone handling (Python 3.9+)
        from zoneinfo import ZoneInfo
        eastern_tz = ZoneInfo("America/Detroit")
    except ImportError:
        # Fallback for older Python versions
        import pytz
        eastern_tz = pytz.timezone('US/Eastern')
    
    # If it's a naive datetime, assume it's UTC
    if utc_datetime.tzinfo is None:
        try:
            from zoneinfo import ZoneInfo
            utc_tz = ZoneInfo("UTC")
            utc_datetime = utc_datetime.replace(tzinfo=utc_tz)
        except ImportError:
            import pytz
            utc_tz = pytz.UTC
            utc_datetime = utc_tz.localize(utc_datetime)
    
    # Convert to Eastern time
    eastern_datetime = utc_datetime.astimezone(eastern_tz)
    return eastern_datetime


def safe_jsonify(data):
    """Safely jsonify data containing Decimal objects"""
    return json.loads(json.dumps(data, default=decimal_converter))


def detect_political_phrases(text):
    """Detect political phrases in text and return matches - optimized version"""
    if not text:
        return {'right_wing': [], 'left_wing': [], 'total_score': 0}
    
    text_lower = text.lower()
    detected = {'right_wing': [], 'left_wing': [], 'total_score': 0}
    
    # Use only key phrases for faster detection
    from utils import RIGHT_WING_KEYWORDS, LEFT_WING_KEYWORDS    
    # Check for right-wing phrases (faster lookup)
    for phrase in RIGHT_WING_KEYWORDS:
        if phrase in text_lower:
            detected['right_wing'].append(phrase)
            detected['total_score'] += 1
    
    # Check for left-wing phrases (faster lookup)
    for phrase in LEFT_WING_KEYWORDS:
        if phrase in text_lower:
            detected['left_wing'].append(phrase)
            detected['total_score'] -= 1  # Negative score for left-wing
    
    return detected


def register_socket_routes(socketio):
    """Register Socket.IO routes for analytics"""
    
    @socketio.on('connect_analytics')
    def handle_analytics_connect():
        """Handle client connection to analytics"""
        print('Client connected to analytics monitoring')
        emit('analytics_status', {'message': 'Connected to real-time analytics'})

    @socketio.on('disconnect_analytics')
    def handle_analytics_disconnect():
        """Handle client disconnection from analytics"""
        print('Client disconnected from analytics monitoring')

    @socketio.on('start_analytics_monitoring')
    def handle_start_analytics_monitoring():
        """Start real-time analytics monitoring for this client"""
        print('Starting real-time analytics monitoring for client')
        emit('analytics_monitoring_started', {'status': 'success'})

    @socketio.on('stop_analytics_monitoring')
    def handle_stop_analytics_monitoring():
        """Stop real-time analytics monitoring for this client"""
        print('Stopping real-time analytics monitoring for client')
        emit('analytics_monitoring_stopped', {'status': 'success'})

    # Background task for broadcasting real-time analytics data
    def background_analytics_monitor():
        """Background task to broadcast analytics data to all connected clients"""
        while True:
            try:
                # Use a fresh database instance for each iteration to avoid unread results
                with get_shared_database_class() as db:
                    # Get all analytics data and emit it
                    analytics_data = get_all_analytics_data(db)
                    
                    # Broadcast data to all connected clients
                    socketio.emit('analytics_update', safe_jsonify(analytics_data))
                
            except Exception as e:
                print(f"Error in analytics background monitor: {e}")
                socketio.emit('analytics_error', {'message': str(e)})
            
            # Wait 10 seconds before next update (analytics don't need to be as frequent as ingress)
            time.sleep(10)
    
    return background_analytics_monitor


def get_all_analytics_data(db):
    """Get comprehensive analytics data"""
    
    # Political sentiment analysis
    political_data = get_political_sentiment(db)
    
    # Trending topics
    trending_data = get_trending_topics(db, '24h')
    
    # User behavior
    user_behavior = get_user_behavior(db)
    
    # Content analysis
    content_analysis = get_content_analysis(db)
    
    # Network analysis
    network_analysis = get_network_analysis(db)
    
    return {
        'political_sentiment': political_data,
        'trending_topics': trending_data,
        'user_behavior': user_behavior,
        'content_analysis': content_analysis,
        'network_analysis': network_analysis,
        'timestamp': datetime.now().isoformat()
    }


def get_political_sentiment(db):
    """Get political sentiment analysis data"""
    try:
        # Get posts from last 24 hours for analysis
        recent_posts = db.fetch_all('''
            SELECT text, saved_at 
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            AND text IS NOT NULL
            ORDER BY saved_at DESC
        ''')
        
        political_stats = {
            'right_wing_count': 0,
            'left_wing_count': 0,
            'political_phrases': [],
            'timeline_data': []
        }
        
        for row in recent_posts:
            political_phrases = detect_political_phrases(row['text'])
            
            if political_phrases['right_wing']:
                political_stats['right_wing_count'] += 1
                political_stats['political_phrases'].extend(political_phrases['right_wing'])
            
            if political_phrases['left_wing']:
                political_stats['left_wing_count'] += 1
                political_stats['political_phrases'].extend(political_phrases['left_wing'])
        
        # Get timeline data (political posts by hour)
        timeline_results = db.fetch_all('''
            SELECT 
                DATE_FORMAT(saved_at, '%Y-%m-%d %H:00:00') as hour,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND (text LIKE '%trump%' OR text LIKE '%biden%' OR text LIKE '%politics%' 
                 OR text LIKE '%election%' OR text LIKE '%democrat%' OR text LIKE '%republican%')
            GROUP BY DATE_FORMAT(saved_at, '%Y-%m-%d %H:00:00')
            ORDER BY hour
        ''')
        
        political_stats['timeline_data'] = [
            {'date': row['hour'], 'count': row['count']} 
            for row in timeline_results
        ]
        
        return political_stats
        
    except Exception as e:
        print(f"Error in political sentiment analysis: {e}")
        return {'right_wing_count': 0, 'left_wing_count': 0, 'political_phrases': [], 'timeline_data': []}


def get_trending_topics(db, period):
    """Get trending topics for specified period"""
    try:
        hours_map = {'1h': 1, '6h': 6, '24h': 24}
        hours = hours_map.get(period, 24)
        
        # Get trending hashtags
        hashtag_results = db.fetch_all('''
            SELECT text, COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND text REGEXP '#[a-zA-Z0-9_]+'
            GROUP BY text
            ORDER BY count DESC
            LIMIT 50
        ''', (hours,))
        
        # Extract hashtags from text
        hashtags = {}
        for row in hashtag_results:
            tags = re.findall(r'#\w+', row['text'].lower())
            for tag in tags:
                hashtags[tag] = hashtags.get(tag, 0) + 1
        
        trending_hashtags = sorted(hashtags.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Get trending phrases (simple word analysis)
        text_results = db.fetch_all('''
            SELECT text
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND text IS NOT NULL
            LIMIT 1000
        ''', (hours,))
        
        word_counts = {}
        for row in text_results:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', row['text'].lower())
            for word in words:
                if word not in ['that', 'this', 'with', 'from', 'they', 'have', 'been', 'will', 'were', 'what', 'when', 'where']:
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        trending_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            'hashtags': [{'tag': tag, 'count': count} for tag, count in trending_hashtags],
            'words': [{'word': word, 'count': count} for word, count in trending_words]
        }
        
    except Exception as e:
        print(f"Error getting trending topics: {e}")
        return {'hashtags': [], 'words': []}


def get_user_behavior(db):
    """Get user behavior analysis"""
    try:
        # High-volume posters in last 24 hours
        top_posters_data = db.fetch_all('''
            SELECT 
                author_handle,
                author_did,
                COUNT(*) as post_count,
                MIN(saved_at) as first_post,
                MAX(saved_at) as last_post,
                ROUND(COUNT(*) / 24.0, 1) as posts_per_hour
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND author_handle IS NOT NULL
            GROUP BY author_handle, author_did
            HAVING post_count >= 5
            ORDER BY post_count DESC
            LIMIT 20
        ''')
        
        top_posters = []
        for poster in top_posters_data:
            # Convert timestamps to Eastern time
            first_eastern = convert_to_eastern(poster['first_post'])
            last_eastern = convert_to_eastern(poster['last_post'])
            
            top_posters.append({
                'handle': poster['author_handle'],
                'did': poster['author_did'],
                'post_count': poster['post_count'],
                'first_post': first_eastern.isoformat() if first_eastern else None,
                'last_post': last_eastern.isoformat() if last_eastern else None,
                'posts_per_hour': poster['posts_per_hour']
            })
        
        # Hourly activity
        hourly_data = db.fetch_all('''
            SELECT 
                HOUR(saved_at) as hour,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY HOUR(saved_at)
            ORDER BY hour
        ''')
        
        return {
            'top_posters': top_posters,
            'hourly_activity': hourly_data
        }
        
    except Exception as e:
        print(f"Error getting user behavior: {e}")
        return {'top_posters': [], 'hourly_activity': []}


def get_content_analysis(db):
    """Get content analysis data"""
    try:
        # Posts with/without links
        link_data = db.fetch_all('''
            SELECT 
                CASE WHEN text REGEXP 'https?://' THEN 'With Links' ELSE 'Without Links' END as type,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY CASE WHEN text REGEXP 'https?://' THEN 'With Links' ELSE 'Without Links' END
        ''')
        
        # Sentiment analysis (simple)
        sentiment_data = db.fetch_all('''
            SELECT 
                CASE 
                    WHEN text REGEXP '(good|great|amazing|love|happy|awesome|excellent)' THEN 'Positive'
                    WHEN text REGEXP '(bad|terrible|hate|angry|sad|awful|horrible)' THEN 'Negative'
                    ELSE 'Neutral'
                END as sentiment,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY sentiment
        ''')
        
        # Average post length by language
        language_length = db.fetch_all('''
            SELECT 
                language,
                ROUND(AVG(LENGTH(text)), 1) as avg_length,
                COUNT(*) as count
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND language IS NOT NULL
            GROUP BY language
            HAVING count >= 10
            ORDER BY count DESC
            LIMIT 10
        ''')
        
        return {
            'link_analysis': link_data,
            'sentiment_analysis': sentiment_data,
            'language_length': language_length
        }
        
    except Exception as e:
        print(f"Error getting content analysis: {e}")
        return {'link_analysis': [], 'sentiment_analysis': [], 'language_length': []}


def get_network_analysis(db):
    """Get network analysis data"""
    try:
        # Most mentioned users (simple @mention counting)
        posts_with_mentions = db.fetch_all('''
            SELECT text
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND text REGEXP '@[a-zA-Z0-9._-]+'
            LIMIT 1000
        ''')
        
        mentions = {}
        for post in posts_with_mentions:
            found_mentions = re.findall(r'@([a-zA-Z0-9._-]+)', post['text'])
            for mention in found_mentions:
                mentions[mention] = mentions.get(mention, 0) + 1
        
        top_mentioned = sorted(mentions.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Users posting at the same time (concurrent activity)
        concurrent_activity = db.fetch_all('''
            SELECT 
                DATE_FORMAT(saved_at, '%Y-%m-%d %H:%i:00') as minute,
                COUNT(DISTINCT author_handle) as unique_authors,
                COUNT(*) as total_posts
            FROM posts 
            WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
            AND author_handle IS NOT NULL
            GROUP BY DATE_FORMAT(saved_at, '%Y-%m-%d %H:%i:00')
            HAVING unique_authors > 1
            ORDER BY unique_authors DESC
            LIMIT 20
        ''')
        
        return {
            'most_mentioned': [{'handle': handle, 'count': count} for handle, count in top_mentioned],
            'concurrent_activity': concurrent_activity
        }
        
    except Exception as e:
        print(f"Error getting network analysis: {e}")
        return {'most_mentioned': [], 'concurrent_activity': []}


def register_routes(app):
    
    @app.route('/analytics')
    def analytics():
        """Analytics dashboard page"""
        return render_template('analytics.html')

    @app.route('/api/analytics/political-sentiment')
    def api_political_sentiment():
        """Get political sentiment analysis"""
        with get_shared_database_class() as db:
            try:
                data = get_political_sentiment(db)
                return jsonify(safe_jsonify(data))
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    @app.route('/api/analytics/trending-topics')
    def api_trending_topics():
        """Get trending topics"""
        period = request.args.get('period', '24h')
        with get_shared_database_class() as db:
            try:
                data = get_trending_topics(db, period)
                return jsonify(safe_jsonify(data))
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    @app.route('/api/analytics/user-behavior')
    def api_user_behavior():
        """Get user behavior analysis"""
        with get_shared_database_class() as db:
            try:
                data = get_user_behavior(db)
                return jsonify(safe_jsonify(data))
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    @app.route('/api/analytics/content-analysis')
    def api_content_analysis():
        """Get content analysis"""
        with get_shared_database_class() as db:
            try:
                data = get_content_analysis(db)
                return jsonify(safe_jsonify(data))
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    @app.route('/api/analytics/network-analysis')
    def api_network_analysis():
        """Get network analysis"""
        with get_shared_database_class() as db:
            try:
                data = get_network_analysis(db)
                return jsonify(safe_jsonify(data))
            except Exception as e:
                return jsonify({'error': str(e)}), 500
