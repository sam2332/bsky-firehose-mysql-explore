from flask import request, jsonify, render_template
from utils import  format_post_text, format_datetime, detect_political_phrases
from libs.database import get_db_connection
def register_routes(app):
    """Register routes for post-related API endpoints."""
  
    @app.route('/')
    def index():
        """Main dashboard page"""
        return render_template('index.html')

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