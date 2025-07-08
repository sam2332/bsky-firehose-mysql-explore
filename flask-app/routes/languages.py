from flask import jsonify
from libs.database import get_db_connection
def register_routes(app):
    
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