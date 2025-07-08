from flask import Flask, request, jsonify, render_template
from libs.database import get_db_connection
def register_routes(app):

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
