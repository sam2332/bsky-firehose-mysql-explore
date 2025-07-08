from libs.database import get_db_connection
from flask import  jsonify, render_template
def register_routes(app):
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