-- Initialize the bsky database schema
USE bsky_db;

-- Posts table with MariaDB optimizations
CREATE TABLE IF NOT EXISTS posts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    author_did VARCHAR(255) NOT NULL,
    author_handle VARCHAR(255),
    text TEXT,
    created_at TIMESTAMP NULL,
    language VARCHAR(10),
    post_uri VARCHAR(500),
    raw_data LONGTEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_author_did (author_did),
    INDEX idx_author_handle (author_handle),
    INDEX idx_created_at (created_at),
    INDEX idx_saved_at (saved_at),
    INDEX idx_language (language),
    FULLTEXT INDEX idx_text_fulltext (text)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- DID cache table
CREATE TABLE IF NOT EXISTS did_cache (
    did VARCHAR(255) PRIMARY KEY,
    handle VARCHAR(255),
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    failed_attempts INT DEFAULT 0,
    
    INDEX idx_handle (handle),
    INDEX idx_resolved_at (resolved_at),
    INDEX idx_failed_attempts (failed_attempts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create user with proper permissions
CREATE USER IF NOT EXISTS 'bsky_user'@'%' IDENTIFIED BY 'bsky_password';
GRANT ALL PRIVILEGES ON bsky_db.* TO 'bsky_user'@'%';
FLUSH PRIVILEGES;
