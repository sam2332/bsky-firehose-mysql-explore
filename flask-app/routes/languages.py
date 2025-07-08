from flask import jsonify
from libs.database import get_shared_database_class
def register_routes(app):
    
    @app.route('/api/languages')
    def get_languages():
        """Get available languages for filtering"""
        with get_shared_database_class() as db:
            try:
                languages = db.fetch_all('''
                    SELECT language, COUNT(*) as count 
                    FROM posts 
                    WHERE language IS NOT NULL 
                    GROUP BY language 
                    ORDER BY count DESC
                ''')
                
                languages = [{'code': lang['language'], 'count': lang['count'], 'name': lang['language'].upper() if lang['language'] else 'Unknown'} 
                            for lang in languages]
                
                return jsonify({'languages': languages})
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500