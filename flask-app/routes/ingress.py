from flask import jsonify, render_template
from libs.database import get_db_connection
from datetime import datetime
from utils import format_post_text, format_datetime
import time
from flask_socketio import emit


def register_socket_routes(socketio):
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
    return background_ingress_monitor

def register_routes(app):
    
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