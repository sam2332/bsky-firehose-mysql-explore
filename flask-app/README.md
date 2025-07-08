# Bluesky Posts Explorer

A beautiful Flask web application for searching and filtering Bluesky posts stored in your database.

## Features

- **Real-time Statistics Dashboard** - View total posts, unique authors, and activity metrics
- **Advanced Search** - Full-text search with MySQL FULLTEXT indexing
- **Multiple Filters** - Filter by language, author, date range
- **Responsive Design** - Modern Bootstrap-based UI that works on all devices
- **Detailed Post Views** - Modal popups with complete post information
- **Pagination** - Efficient browsing through large datasets
- **Export Capabilities** - Links to view posts on Bluesky

## Installation

1. **Install dependencies:**
   ```bash
   cd flask-app
   pip install -r requirements.txt
   ```

2. **Set up environment variables (optional):**
   ```bash
   export MYSQL_HOST=mariadb
   export MYSQL_DATABASE=bsky_db
   export MYSQL_USER=bsky_user
   export MYSQL_PASSWORD=bsky_password
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the web interface:**
   Open your browser to `http://localhost:5000`

## Usage

### Search Features

- **Text Search**: Search within post content using natural language
- **Language Filter**: Filter posts by detected language
- **Author Filter**: Search for specific authors by handle or DID
- **Date Range**: Filter posts by creation or save date
- **Sorting**: Sort by date saved, date created, author, or language

### Dashboard

The main dashboard shows:
- Total posts in database
- Number of unique authors
- Posts saved today and this week
- Language distribution
- Recent activity patterns

### Post Details

Click on any post to view:
- Full post content
- Author information
- Technical details (DID, URI)
- Direct link to view on Bluesky

## Technical Details

### Database Schema

The application expects the following MySQL/MariaDB tables:

```sql
-- Posts table
CREATE TABLE posts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    author_did VARCHAR(255) NOT NULL,
    author_handle VARCHAR(255),
    text TEXT,
    created_at TIMESTAMP NULL,
    language VARCHAR(10),
    post_uri VARCHAR(500),
    raw_data LONGTEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Indexes for performance
    INDEX idx_author_did (author_did),
    INDEX idx_author_handle (author_handle),
    INDEX idx_created_at (created_at),
    INDEX idx_saved_at (saved_at),
    INDEX idx_language (language),
    FULLTEXT INDEX idx_text_fulltext (text)
);
```

### API Endpoints

- `GET /` - Main dashboard page
- `GET /api/stats` - Database statistics
- `GET /api/posts` - Search and filter posts
- `GET /api/languages` - Available languages
- `GET /api/authors` - Author autocomplete

### Performance Features

- **FULLTEXT Search**: Uses MySQL FULLTEXT indexing for fast text searches
- **Pagination**: Efficient pagination for large datasets
- **Caching**: Results caching for improved performance
- **Indexes**: Optimized database indexes for common queries

## Configuration

### Environment Variables

- `MYSQL_HOST` - Database host (default: mariadb)
- `MYSQL_DATABASE` - Database name (default: bsky_db)
- `MYSQL_USER` - Database user (default: bsky_user)
- `MYSQL_PASSWORD` - Database password (default: bsky_password)
- `MYSQL_PORT` - Database port (default: 3306)
- `SECRET_KEY` - Flask secret key for sessions

### Application Settings

Edit `config.py` to customize:
- Posts per page
- Maximum search results
- Other application settings

## Development

### Project Structure

```
flask-app/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html     # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css  # Custom styles
│   └── js/
│       └── app.js     # Frontend JavaScript
└── README.md          # This file
```

### Adding Features

The application is designed to be easily extensible:

1. **New Filters**: Add filter inputs to the form and update the API endpoint
2. **Export Options**: Add export buttons and new API endpoints
3. **Visualization**: Add charts and graphs using Chart.js or similar
4. **Real-time Updates**: Add WebSocket support for live updates

## Deployment

### Production Deployment

For production deployment, consider:

1. **Use Gunicorn**:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Environment Variables**: Set proper environment variables
3. **Reverse Proxy**: Use nginx or similar as a reverse proxy
4. **Database Optimization**: Ensure proper indexing and connection pooling
5. **Caching**: Add Redis or Memcached for better performance

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**: Check MySQL credentials and connectivity
2. **No Posts Found**: Verify data exists in the `posts` table
3. **Search Not Working**: Ensure FULLTEXT indexes are created
4. **Slow Performance**: Check database indexes and query optimization

### Debugging

Enable Flask debug mode:
```python
app.run(debug=True)
```

Check browser console for JavaScript errors and network requests.

## License

This project is part of the Bluesky monitoring system.
