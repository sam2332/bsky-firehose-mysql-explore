# Tasks for Cache Heavy Function Outputs in Database

## Relevant Files

- `migrations/` - Alembic migration scripts for schema changes (will create new files).
- `migrations/env.py` - Alembic environment configuration; needs target_metadata setup.
- `alembic.ini` - Alembic configuration file; needs database URL setup.
- `setup_database.py` - Database setup script; may need updates for new columns.
- `flask-app/libs/database.py` - Database abstraction layer; will add caching logic.
- `flask-app/routes/analytics.py` - Contains heavy political phrase detection and analytics to cache.
- `flask-app/utils.py` - Contains heavy political phrase detection functions to cache.
- `test_db_connection.py` - Update tests for new caching functionality.
- `test_cache_functions.py` - New test file for cache-specific tests.
- `requirements.txt` - Add any new dependencies if needed.

## Heavy Functions Catalog (Task 1.1 Complete)

Based on analysis of the codebase, the following computationally expensive functions have been identified for caching:

### 1. Word Frequency Analysis
- **File:** `word_frequency_analysis.py`
- **Functions:** 
  - `generate_word_frequency()` - Processes all words from posts and counts frequency
  - `clean_text()` - Text preprocessing with regex operations and stop word filtering
- **Computation:** Text cleaning, tokenization, stop word filtering, frequency counting
- **Output:** Counter object with word frequencies (top N words)

### 2. Political Phrase Detection & Sentiment Analysis
- **Files:** `flask-app/routes/analytics.py`, `flask-app/utils.py`
- **Functions:**
  - `detect_political_phrases()` - Scans text for political keywords
  - `get_political_sentiment()` - Analyzes posts for political sentiment
- **Computation:** Text pattern matching against large keyword lists, sentiment scoring
- **Output:** Dict with right_wing/left_wing phrase counts and sentiment scores

### 3. Word Cloud Generation
- **Files:** `custom_word_cloud.py`, `word_cloud_generator.py`
- **Functions:**
  - `create_custom_word_cloud()` - Generates word cloud images
  - `get_posts_text()` - Fetches and processes post text for word clouds
  - `clean_text()` - Text preprocessing for word clouds
- **Computation:** Text processing, word frequency calculation, image generation
- **Output:** Word cloud data structure and image paths

### 4. Trending Topics Analysis
- **File:** `flask-app/routes/analytics.py`
- **Functions:**
  - `get_trending_topics()` - Analyzes hashtags and word trends
- **Computation:** Regex pattern matching for hashtags, word frequency analysis
- **Output:** Lists of trending hashtags and words with counts

### 5. Network Analysis
- **File:** `flask-app/routes/analytics.py`
- **Functions:**
  - `get_network_analysis()` - Analyzes user mention patterns and concurrent activity
- **Computation:** Regex matching for @mentions, temporal analysis of posting patterns
- **Output:** Most mentioned users and concurrent posting data

### 6. Content Analysis (Sentiment)
- **File:** `flask-app/routes/analytics.py`
- **Functions:**
  - `get_content_analysis()` - Analyzes post sentiment, links, and language patterns
- **Computation:** Regex pattern matching for sentiment keywords and links
- **Output:** Sentiment analysis results, link analysis, language statistics

## Cache Column Specifications (Task 1.2 Complete)

Based on the production analytics functions, the following cache columns will be added to the `posts` table:

### 1. cached_political_phrases (TEXT)
- **Purpose:** Store results of `detect_political_phrases()` function
- **Source Function:** `flask-app/routes/analytics.py` and `flask-app/utils.py`
- **Data Type:** TEXT (JSON serialized)
- **Expected Content:** 
  ```json
  {
    "right_wing": ["maga", "america first"],
    "left_wing": ["climate change", "social justice"],
    "total_score": 1,
    "processed_at": "2025-07-09T10:30:00Z"
  }
  ```

### 2. cached_sentiment_score (TEXT)
- **Purpose:** Store results of content sentiment analysis
- **Source Function:** `get_content_analysis()` in `flask-app/routes/analytics.py`
- **Data Type:** TEXT (JSON serialized)
- **Expected Content:**
  ```json
  {
    "sentiment": "positive",
    "confidence": 0.75,
    "keywords_matched": ["good", "great", "amazing"],
    "processed_at": "2025-07-09T10:30:00Z"
  }
  ```

### 3. cached_trending_topics (TEXT)
- **Purpose:** Store trending topic analysis results for the post
- **Source Function:** `get_trending_topics()` in `flask-app/routes/analytics.py`
- **Data Type:** TEXT (JSON serialized)
- **Expected Content:**
  ```json
  {
    "hashtags": ["#politics", "#news"],
    "mentions": ["@user1", "@user2"],
    "trending_words": ["election", "vote", "democracy"],
    "processed_at": "2025-07-09T10:30:00Z"
  }
  ```

### 4. cached_network_metrics (TEXT)
- **Purpose:** Store network analysis metrics for the post
- **Source Function:** `get_network_analysis()` in `flask-app/routes/analytics.py`
- **Data Type:** TEXT (JSON serialized)
- **Expected Content:**
  ```json
  {
    "mentions_count": 3,
    "mentioned_users": ["user1", "user2", "user3"],
    "reply_to": "at://did:plc:abc123/app.bsky.feed.post/xyz789",
    "network_reach": 150,
    "processed_at": "2025-07-09T10:30:00Z"
  }
  ```

### Cache Design Principles:
- **Write-Once Policy:** Cache values are never updated once written
- **JSON Format:** All cache columns use JSON serialization for flexibility
- **Timestamp Tracking:** Each cache entry includes `processed_at` timestamp
- **NULL Default:** Uncached posts will have NULL values in cache columns
- **Indexing:** No indexes on cache columns to avoid write performance impact

### Notes

- Unit tests should be placed alongside the code files they are testing.
- Use `pytest` to run tests: `pytest test_cache_functions.py` for cache tests.
- Use Alembic for schema migrations: `alembic revision --autogenerate -m "Add cache columns"`.
- Cache uses TEXT BLOB columns for flexibility in storing analysis outputs.
- One-time write policy: cache values are never updated once written.

## Tasks

- [ ] 1.0 Identify and Document Heavy Function Outputs to Cache
  - [x] 1.1 Catalog all computationally expensive functions: word_frequency analysis, political_phrase_detection, sentiment_analysis, word_cloud_generation, trending_topics_analysis, network_analysis
  - [x] 1.2 Define cache column specifications: cached_political_phrases (TEXT), cached_sentiment_score (TEXT), cached_trending_topics (TEXT), cached_network_metrics (TEXT)
  - [ ] 1.3 Document expected TEXT BLOB format for each cached output (JSON serialized strings)
- [ ] 2.0 Set Up SQLAlchemy Models and Alembic Configuration
  - [ ] 2.1 Create SQLAlchemy models file with Post model including cache columns
  - [ ] 2.2 Configure Alembic env.py to use the new models metadata
  - [ ] 2.3 Update alembic.ini with proper database connection string
  - [ ] 2.4 Test Alembic configuration with dry-run migration
- [ ] 3.0 Create Database Schema Migration
  - [ ] 3.1 Generate Alembic migration script for adding cache columns to posts table
  - [ ] 3.2 Review generated migration script for correctness
  - [ ] 3.3 Apply migration to database and verify schema changes
  - [ ] 3.4 Add rollback testing for the migration
- [ ] 4.0 Implement Cache Access Layer in Database Module
  - [ ] 4.1 Add cache_get() method to DatabaseClass for retrieving cached values
  - [ ] 4.2 Add cache_set() method to DatabaseClass for storing cached values (write-once policy)
  - [ ] 4.3 Add cache_exists() method to DatabaseClass for checking cache availability
  - [ ] 4.4 Implement JSON serialization/deserialization for TEXT BLOB storage
  - [ ] 4.5 Add logging for cache hits/misses for performance monitoring
- [ ] 5.0 Refactor Heavy Functions to Use Caching
  - [ ] 5.1 Update word_frequency_analysis.py functions to check cache before computation
  - [ ] 5.2 Update political phrase detection in analytics.py and utils.py to use cache
  - [ ] 5.3 Update sentiment analysis functions to use cache
  - [ ] 5.4 Update word cloud generation functions to use cache
  - [ ] 5.5 Update trending topics analysis to use cache
  - [ ] 5.6 Update network analysis functions to use cache
  - [ ] 5.7 Ensure all cached functions follow write-once policy (never update existing cache)
- [ ] 6.0 Add Comprehensive Unit Tests
  - [ ] 6.1 Create test_cache_functions.py with cache layer tests (hit, miss, write-once)
  - [ ] 6.2 Add tests for each heavy function's caching logic
  - [ ] 6.3 Add tests for JSON serialization/deserialization of cache data
  - [ ] 6.4 Add tests for cache column existence and data types
  - [ ] 6.5 Add integration tests for end-to-end caching workflow
  - [ ] 6.6 Add performance tests to verify caching improves speed
- [ ] 7.0 Update Documentation and Code Quality
  - [ ] 7.1 Add docstrings to all new cache-related functions
  - [ ] 7.2 Update existing function docstrings to mention caching behavior
  - [ ] 7.3 Add inline comments explaining cache logic and write-once policy
  - [ ] 7.4 Ensure all code follows PEP 8 formatting standards
  - [ ] 7.5 Update setup_database.py comments to reflect new cache columns
