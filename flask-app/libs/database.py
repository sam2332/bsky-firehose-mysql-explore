import mysql.connector
import time
import logging
import threading
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306,
    'charset': 'utf8mb4',
    'autocommit': True,
    'connect_timeout': 10,
    'connection_timeout': 10,
    'buffered': True,
    'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'
}

# Global connection pool
_connection_pool = {}
_pool_lock = threading.Lock()


class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors"""
    pass


class DatabaseOperationError(Exception):
    """Custom exception for database operation errors"""
    pass


class DatabaseClass:
    """
    Database abstraction layer with retry logic and reconnection capabilities.
    Provides robust MySQL operations with exponential backoff for failed operations.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, reuse_connection: bool = True):
        """
        Initialize database connection with retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay in seconds between retries
            reuse_connection: Whether to reuse existing connections from pool
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.reuse_connection = reuse_connection
        self.connection: Optional[mysql.connector.MySQLConnection] = None
        self.connection_id = None
        self._should_close_on_exit = True
        
        if reuse_connection:
            self._get_pooled_connection()
        else:
            self._connect()

    def _get_pooled_connection(self) -> None:
        """Get a connection from the pool or create a new one"""
        thread_id = threading.get_ident()
        
        with _pool_lock:
            if thread_id in _connection_pool:
                pooled_conn = _connection_pool[thread_id]
                if pooled_conn and self._test_connection(pooled_conn):
                    self.connection = pooled_conn
                    self.connection_id = thread_id
                    self._should_close_on_exit = False
                    logger.debug(f"Reusing existing connection for thread {thread_id}")
                    return
                else:
                    # Connection is invalid, remove from pool
                    if thread_id in _connection_pool:
                        del _connection_pool[thread_id]
            
            # Create new connection and add to pool
            self._connect()
            if self.connection:
                _connection_pool[thread_id] = self.connection
                self.connection_id = thread_id
                self._should_close_on_exit = False
                logger.info(f"Created new pooled connection for thread {thread_id}")

    def _test_connection(self, conn) -> bool:
        """Test if a connection is still valid"""
        try:
            conn.ping(reconnect=False, attempts=1)
            # Also ensure no unread results are left
            try:
                conn.consume_results()
            except:
                pass
            return True
        except Exception:
            return False

    def _connect(self) -> None:
        """Establish database connection with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if self.connection:
                    try:
                        self.connection.close()
                    except Exception:
                        pass
                
                self.connection = mysql.connector.connect(**MYSQL_CONFIG)
                logger.info("Database connection established successfully")
                return
                
            except mysql.connector.Error as e:
                last_exception = e
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"Retrying connection in {delay} seconds...")
                    time.sleep(delay)
        
        raise DatabaseConnectionError(f"Failed to establish database connection after {self.max_retries + 1} attempts: {last_exception}")

    def _is_connection_alive(self) -> bool:
        """Check if the current connection is alive and working"""
        if not self.connection:
            return False
        
        try:
            # Use ping() to check if connection is alive
            self.connection.ping(reconnect=False, attempts=1)
            return True
        except mysql.connector.Error:
            return False

    def _ensure_connection(self) -> None:
        """Ensure we have a valid database connection"""
        if not self._is_connection_alive():
            logger.info("Connection lost, attempting to reconnect...")
            self._connect()
        else:
            # Clear any unread results from previous operations
            try:
                if self.connection:
                    self.connection.consume_results()
            except:
                pass

    def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute database operation with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self._ensure_connection()
                self._clear_unread_results()
                return operation(*args, **kwargs)
                
            except mysql.connector.Error as e:
                last_exception = e
                logger.warning(f"Database operation attempt {attempt + 1} failed: {e}")
                
                # Check if it's a connection-related error
                if e.errno in [2006, 2013, 2055, 2003]:  # Connection lost, lost connection to server, etc.
                    logger.info("Connection error detected, forcing reconnection")
                    self.connection = None
                elif "Unread result found" in str(e):
                    logger.info("Unread result found, clearing and retrying")
                    self._clear_unread_results()
                
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"Retrying operation in {delay} seconds...")
                    time.sleep(delay)
                else:
                    break
        
        raise DatabaseOperationError(f"Database operation failed after {self.max_retries + 1} attempts: {last_exception}")

    @contextmanager
    def get_cursor(self, dictionary: bool = True):
        """Context manager for database cursor with automatic cleanup"""
        cursor = None
        try:
            self._ensure_connection()
            cursor = self.connection.cursor(dictionary=dictionary, buffered=True)
            yield cursor
        except Exception as e:
            if cursor:
                # Consume any unread results before closing
                try:
                    while cursor.nextset():
                        pass
                except:
                    pass
                cursor.close()
            raise e
        finally:
            if cursor:
                # Consume any unread results before closing
                try:
                    while cursor.nextset():
                        pass
                except:
                    pass
                cursor.close()

    def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return all results.
        
        Args:
            query: SQL SELECT query
            params: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        def _execute():
            with self.get_cursor(dictionary=True) as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        
        return self._execute_with_retry(_execute)

    def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """
        Execute SELECT query and return first result.
        
        Args:
            query: SQL SELECT query
            params: Query parameters
            
        Returns:
            Dictionary representing the row or None
        """
        def _execute():
            with self.get_cursor(dictionary=True) as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchone()
        
        return self._execute_with_retry(_execute)

    def execute(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        Execute INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        def _execute():
            with self.get_cursor(dictionary=False) as cursor:
                cursor.execute(query, params or ())
                return cursor.rowcount
        
        return self._execute_with_retry(_execute)

    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """
        Execute multiple queries with different parameters.
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        def _execute():
            with self.get_cursor(dictionary=False) as cursor:
                cursor.executemany(query, params_list)
                return cursor.rowcount
        
        return self._execute_with_retry(_execute)

    def execute_transaction(self, operations: List[Tuple[str, Optional[Tuple]]]) -> bool:
        """
        Execute multiple operations in a transaction.
        
        Args:
            operations: List of (query, params) tuples
            
        Returns:
            True if transaction succeeded, False otherwise
        """
        def _execute():
            # Temporarily disable autocommit for transaction
            original_autocommit = self.connection.autocommit
            self.connection.autocommit = False
            
            try:
                with self.get_cursor(dictionary=False) as cursor:
                    for query, params in operations:
                        cursor.execute(query, params or ())
                    self.connection.commit()
                    return True
            except Exception as e:
                self.connection.rollback()
                raise e
            finally:
                self.connection.autocommit = original_autocommit
        
        return self._execute_with_retry(_execute)

    def get_last_insert_id(self) -> int:
        """Get the last inserted row ID"""
        def _execute():
            with self.get_cursor(dictionary=False) as cursor:
                return cursor.lastrowid
        
        return self._execute_with_retry(_execute)

    @property
    def cursor(self):
        """
        Backward compatibility property to get a cursor directly.
        Note: This doesn't include automatic retry logic. Use get_cursor() context manager for better error handling.
        """
        self._ensure_connection()
        return self.connection.cursor(buffered=True)
    
    def get_raw_connection(self):
        """
        Get the raw MySQL connection object for backward compatibility.
        Use with caution - this bypasses retry logic.
        """
        self._ensure_connection()
        return self.connection

    def close(self) -> None:
        """Close database connection or return to pool"""
        if self.connection and self._should_close_on_exit:
            try:
                self.connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")
            finally:
                self.connection = None
        elif self.connection and not self._should_close_on_exit:
            logger.debug(f"Connection returned to pool for thread {self.connection_id}")

    def _clear_unread_results(self) -> None:
        """Clear any unread results from the connection"""
        if self.connection:
            try:
                self.connection.consume_results()
            except Exception:
                # If consume_results fails, try to create and close a cursor
                try:
                    cursor = self.connection.cursor()
                    cursor.close()
                except Exception:
                    pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def get_database_class(reuse_connection: bool = True) -> DatabaseClass:
    """
    Get database class instance with retry logic and reconnection capabilities
    
    Args:
        reuse_connection: Whether to reuse connections from pool (default True)
    """
    return DatabaseClass(reuse_connection=reuse_connection)


def get_shared_database_class() -> DatabaseClass:
    """
    Get a shared database class instance that reuses connections.
    Recommended for background tasks and frequent operations.
    """
    return DatabaseClass(reuse_connection=True)


def get_db_connection():
    """
    Get a raw database connection for backward compatibility.
    Consider using get_database_class() for better error handling and retry logic.
    
    Returns:
        Raw MySQL connection object
    """
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        return None


def cleanup_connection_pool():
    """Clean up all pooled connections"""
    global _connection_pool
    with _pool_lock:
        for thread_id, conn in _connection_pool.items():
            try:
                if conn:
                    conn.close()
                    logger.info(f"Closed pooled connection for thread {thread_id}")
            except Exception as e:
                logger.warning(f"Error closing pooled connection for thread {thread_id}: {e}")
        _connection_pool.clear()
        logger.info("Connection pool cleaned up")
