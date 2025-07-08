from flask import Flask, request, jsonify, render_template
from libs.database import get_shared_database_class
def register_routes(app):

    @app.route('/api/authors')
    def get_authors():
        """Get authors for autocomplete"""
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify({'authors': []})
        
        with get_shared_database_class() as db:
            try:
                authors = db.fetch_all('''
                    SELECT DISTINCT author_handle, author_did, COUNT(*) as post_count
                    FROM posts 
                    WHERE (author_handle LIKE %s OR author_did LIKE %s)
                    AND author_handle IS NOT NULL
                    GROUP BY author_handle, author_did
                    ORDER BY post_count DESC
                    LIMIT 10
                ''', (f"%{query}%", f"%{query}%"))
                
                authors = [{'handle': author['author_handle'], 'did': author['author_did'], 'post_count': author['post_count']} 
                        for author in authors]
                
                return jsonify({'authors': authors})
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
