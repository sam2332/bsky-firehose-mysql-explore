from libs.database import get_shared_database_class
from flask import  jsonify, render_template
def register_routes(app):
    @app.route('/api/stats')
    def get_stats():
        """Get database statistics"""
        with get_shared_database_class() as db:
            try:
                # Total posts
                result = db.fetch_one('SELECT COUNT(*) as count FROM posts')
                total_posts = result['count']
                
                # Unique authors
                result = db.fetch_one('SELECT COUNT(DISTINCT author_did) as count FROM posts')
                unique_authors = result['count']
                
                # Posts today
                result = db.fetch_one('''
                    SELECT COUNT(*) as count FROM posts 
                    WHERE DATE(saved_at) = CURDATE()
                ''')
                posts_today = result['count']
                
                # Posts this week
                result = db.fetch_one('''
                    SELECT COUNT(*) as count FROM posts 
                    WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ''')
                posts_week = result['count']
                
                # Top languages
                languages = db.fetch_all('''
                    SELECT language, COUNT(*) as count 
                    FROM posts 
                    WHERE language IS NOT NULL 
                    GROUP BY language 
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                
                # Format languages for response
                languages = [{'language': lang['language'] or 'Unknown', 'count': lang['count']} 
                            for lang in languages]
                
                # Recent activity (posts per hour for last 24 hours)
                activity = db.fetch_all('''
                    SELECT 
                        HOUR(saved_at) as hour,
                        COUNT(*) as count
                    FROM posts 
                    WHERE saved_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    GROUP BY HOUR(saved_at)
                    ORDER BY hour
                ''')
                
                return jsonify({
                    'total_posts': total_posts,
                    'unique_authors': unique_authors,
                    'posts_today': posts_today,
                    'posts_week': posts_week,
                    'languages': languages,
                    'activity': activity
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500