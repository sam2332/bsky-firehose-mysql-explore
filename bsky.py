import json
import mysql.connector
import threading
import queue
import time
from datetime import datetime
from atproto_client.models import get_or_create
from atproto import CAR, models, IdResolver
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message
def lprint(string, *args, **kwargs):
    """Prints a message with a timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    #print(f"[{timestamp}] {string}", *args, **kwargs)
# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306,
    'autocommit': True
}

class JSONExtra(json.JSONEncoder):
    """raw objects sometimes contain CID() objects, which
    seem to be references to something elsewhere in bluesky.
    So, we 'serialise' these as a string representation,
    which is a hack but whatevAAAAR"""
    def default(self, obj):
        try:
            result = json.JSONEncoder.default(self, obj)
            return result
        except:
            return repr(obj)

# Initialize MySQL database
def init_database():
    """Initialize database connection - tables already exist in MySQL"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Test connection by checking if tables exist
        cursor.execute("SHOW TABLES LIKE 'posts'")
        posts_exists = cursor.fetchone()
        
        cursor.execute("SHOW TABLES LIKE 'did_cache'")
        cache_exists = cursor.fetchone()
        
        if posts_exists and cache_exists:
            lprint("✅ Connected to MySQL database successfully")
        else:
            lprint("⚠️ Warning: Expected tables not found in database")
        
        conn.close()
    except mysql.connector.Error as e:
        lprint(f"❌ Failed to connect to MySQL database: {e}")
        raise

def get_cached_handle(did):
    """Get handle from cache if available"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT handle FROM did_cache WHERE did = %s', (did,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except mysql.connector.Error as e:
        lprint(f"Error getting cached handle for {did}: {e}")
        return None

def cache_handle(did, handle):
    """Cache the DID to handle mapping"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO did_cache (did, handle, resolved_at, failed_attempts)
            VALUES (%s, %s, NOW(), 0)
            ON DUPLICATE KEY UPDATE 
            handle = VALUES(handle), 
            resolved_at = VALUES(resolved_at), 
            failed_attempts = 0
        ''', (did, handle))
        conn.commit()
        conn.close()
    except mysql.connector.Error as e:
        lprint(f"Error caching handle for {did}: {e}")

def mark_resolution_failed(did):
    """Mark that resolution failed for this DID"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Get current failed attempts or 0 if not exists
        cursor.execute('SELECT failed_attempts FROM did_cache WHERE did = %s', (did,))
        result = cursor.fetchone()
        current_attempts = result[0] if result else 0
        
        cursor.execute('''
            INSERT INTO did_cache (did, handle, resolved_at, failed_attempts)
            VALUES (%s, NULL, NOW(), %s)
            ON DUPLICATE KEY UPDATE 
            handle = NULL,
            resolved_at = NOW(), 
            failed_attempts = %s
        ''', (did, current_attempts + 1, current_attempts + 1))
        conn.commit()
        conn.close()
    except mysql.connector.Error as e:
        lprint(f"Error marking resolution failed for {did}: {e}")

def should_retry_resolution(did):
    """Check if we should retry resolution for a failed DID"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT failed_attempts, resolved_at 
            FROM did_cache 
            WHERE did = %s AND handle IS NULL
        ''', (did,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return True  # Never tried before
        
        failed_attempts, resolved_at = result
        # Don't retry if failed more than 3 times
        if failed_attempts >= 3:
            return False
        
        # Retry after 1 hour for failed attempts
        from datetime import timedelta
        return datetime.now() - resolved_at > timedelta(hours=1)
    except mysql.connector.Error as e:
        lprint(f"Error checking retry status for {did}: {e}")
        return True  # Default to retry on error

# Global queues for thread communication
resolution_queue = queue.Queue()  # DIDs to resolve
update_queue = queue.Queue()      # Updates to apply to database

def update_multiple_posts_handle(post_ids, handle):
    """Update multiple posts' handles in a single transaction"""
    if not post_ids:
        return
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Use IN clause for better performance
        placeholders = ','.join(['%s' for _ in post_ids])
        cursor.execute(f'''
            UPDATE posts 
            SET author_handle = %s 
            WHERE id IN ({placeholders})
        ''', [handle] + post_ids)
        
        conn.commit()
        conn.close()
        
        lprint(f"Updated {len(post_ids)} posts with handle @{handle}")
    except mysql.connector.Error as e:
        lprint(f"Error updating multiple posts: {e}")

def update_post_handle(post_id, handle):
    """Update a single post's handle in the database"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute('UPDATE posts SET author_handle = %s WHERE id = %s', (handle, post_id))
        conn.commit()
        conn.close()
    except mysql.connector.Error as e:
        lprint(f"Error updating post handle: {e}")

def save_post_to_db(author_did, author_handle, text, created_at, language, post_uri, raw_data):
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Convert ISO datetime to MySQL format
        if created_at:
            try:
                from datetime import datetime
                # Parse the ISO datetime and convert to MySQL format
                if created_at.endswith('Z'):
                    created_at = created_at[:-1] + '+00:00'
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                created_at = None
        
        cursor.execute('''
            INSERT INTO posts (author_did, author_handle, text, created_at, language, post_uri, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (author_did, author_handle, text, created_at, language, post_uri, raw_data))
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return post_id
    except mysql.connector.Error as e:
        lprint(f"Error saving post to database: {e}")
        return None

def resolve_handle_from_did_sync(did):
    """Synchronous DID resolution for background thread"""
    try:
        resolver = IdResolver()
        did_doc = resolver.did.resolve(did)
        
        # Extract handle from the DID document
        handle = None
        if did_doc and hasattr(did_doc, 'also_known_as') and did_doc.also_known_as:
            for aka in did_doc.also_known_as:
                if aka.startswith('at://'):
                    handle = aka[5:]  # Remove 'at://' prefix
                    break
        
        # If no handle found in also_known_as, try service endpoints
        if not handle and did_doc and hasattr(did_doc, 'service') and did_doc.service:
            for service in did_doc.service:
                if hasattr(service, 'service_endpoint') and isinstance(service.service_endpoint, str):
                    if service.service_endpoint.startswith('https://'):
                        # Extract handle from service endpoint (common pattern)
                        endpoint = service.service_endpoint
                        if '.bsky.social' in endpoint:
                            # Try to extract handle from the endpoint
                            parts = endpoint.split('/')
                            if len(parts) > 2:
                                potential_handle = parts[2].split('.')[0]
                                if potential_handle and not potential_handle.startswith('did:'):
                                    handle = potential_handle + '.bsky.social'
                                    break
        
        return handle
        
    except Exception as e:
        lprint(f"Failed to resolve handle for {did}: {e}")
        return None

def did_resolution_worker():
    """Background worker thread for DID resolution"""
    worker_id = threading.current_thread().ident
    lprint(f"DID resolution worker {worker_id} started")
    
    while True:
        try:
            # Get work from queue (blocks until item available)
            did, post_ids = resolution_queue.get(timeout=1)
            
            if did is None:  # Shutdown signal
                lprint(f"Worker {worker_id} shutting down")
                break
                
            lprint(f"Worker {worker_id} processing DID: {did} for {len(post_ids)} posts")
            
            # Check cache first
            cached_handle = get_cached_handle(did)
            if cached_handle is not None:
                lprint(f"Worker {worker_id} found cached handle: {did} -> @{cached_handle}")
                # Batch update all posts with this DID
                update_queue.put(('update_posts_batch', post_ids, cached_handle))
                resolution_queue.task_done()
                continue
            
            # Check if we should retry failed resolutions
            if not should_retry_resolution(did):
                lprint(f"Worker {worker_id} skipping retry for {did} (too many failures)")
                resolution_queue.task_done()
                continue
            
            # Try to resolve from network
            lprint(f"Worker {worker_id} attempting network resolution for {did}")
            handle = resolve_handle_from_did_sync(did)
            
            # Queue database updates
            if handle:
                update_queue.put(('cache_success', did, handle))
                # Batch update all posts for this DID
                update_queue.put(('update_posts_batch', post_ids, handle))
                lprint(f"Worker {worker_id} resolved and cached: {did} -> @{handle} (updating {len(post_ids)} posts)")
            else:
                update_queue.put(('cache_failure', did))
                lprint(f"Worker {worker_id} failed to resolve handle for {did}")
            
            resolution_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            lprint(f"Error in DID resolution worker {worker_id}: {e}")
            resolution_queue.task_done()

def process_database_updates():
    """Process queued database updates on main thread"""
    updates_processed = 0
    try:
        while True:
            update_type, *args = update_queue.get_nowait()
            
            if update_type == 'update_post':
                post_id, handle = args
                update_post_handle(post_id, handle)
            elif update_type == 'update_posts_batch':
                post_ids, handle = args
                update_multiple_posts_handle(post_ids, handle)
            elif update_type == 'cache_success':
                did, handle = args
                cache_handle(did, handle)
            elif update_type == 'cache_failure':
                did = args[0]
                mark_resolution_failed(did)
                
            update_queue.task_done()
            updates_processed += 1
            
    except queue.Empty:
        if updates_processed > 0:
            lprint(f"Processed {updates_processed} database updates")
        pass  # No more updates to process

def process_backlog():
    """Background thread to process unresolved posts from the database"""
    
    while True:
        try:
            time.sleep(60)  # Check every minute
            
            # Get unresolved DIDs from database, grouped by frequency
            conn = mysql.connector.connect(**MYSQL_CONFIG)
            cursor = conn.cursor()
            
            # Get top unresolved DIDs that we haven't tried recently
            cursor.execute('''
                SELECT p.author_did, GROUP_CONCAT(p.id) as post_ids, COUNT(*) as post_count
                FROM posts p
                LEFT JOIN did_cache dc ON p.author_did = dc.did
                WHERE p.author_handle IS NULL 
                AND (dc.did IS NULL OR (dc.handle IS NULL AND dc.failed_attempts < 3))
                GROUP BY p.author_did
                ORDER BY post_count DESC
                LIMIT 20
            ''')
            
            backlog_items = cursor.fetchall()
            conn.close()
            
            # Queue the most frequent unresolved DIDs for processing
            for did, post_ids_str, _ in backlog_items:
                post_ids = [int(pid) for pid in post_ids_str.split(',')]
                resolution_queue.put((did, post_ids))
                lprint(f"Backlog processor: Queued {did} with {len(post_ids)} posts")
                
                # Don't overwhelm the queue
                if resolution_queue.qsize() > 50:
                    break
                    
        except mysql.connector.Error as e:
            lprint(f"Database error in backlog processor: {e}")
        except Exception as e:
            lprint(f"Error in backlog processor: {e}")

# Initialize the database
init_database()

# Start background worker threads
num_workers = 10  # Increased further for high volume
workers = []
for i in range(num_workers):
    worker = threading.Thread(target=did_resolution_worker, daemon=True)
    worker.start()
    workers.append(worker)

lprint(f"Started {num_workers} DID resolution worker threads")

# Start backlog processor thread
backlog_thread = threading.Thread(target=process_backlog, daemon=True)
backlog_thread.start()
lprint("Started backlog processor thread")

# Track DIDs being resolved to batch requests
pending_resolutions = {}  # did -> list of post_ids

# Statistics tracking
import time
last_stats_time = time.time()
posts_processed = 0
resolutions_queued = 0

client = FirehoseSubscribeReposClient()

# all of this undocumented horseshit is based on cargo-culting the bollocks out of
# https://github.com/MarshalX/atproto/blob/main/examples/firehose/sub_repos.py
# and
# https://github.com/MarshalX/bluesky-feed-generator/blob/main/server/data_stream.py

total_errors = 0  # Track total errors for debugging
def on_message_handler(message):
    global total_errors, posts_processed, resolutions_queued, last_stats_time
    
    # Process any pending database updates first
    process_database_updates()
    
    # Print periodic statistics and sync cached handles
    current_time = time.time()
    if current_time - last_stats_time > 30:  # Every 30 seconds
        queue_size = resolution_queue.qsize()
        update_queue_size = update_queue.qsize()
        
        # Sync cached handles to posts
        synced = sync_cached_handles_to_posts()
        
        lprint(f"Stats: {posts_processed} posts processed, {resolutions_queued} resolutions queued, "
              f"Resolution queue: {queue_size}, Update queue: {update_queue_size}")
        last_stats_time = current_time
    
    commit = parse_subscribe_repos_message(message)
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return
    car = CAR.from_bytes(commit.blocks)
    
    # Extract author DID from the commit
    author_did = commit.repo
    
    for op in commit.ops:
        if op.action in ["create"] and op.cid:
            raw = car.blocks.get(op.cid)
            cooked = get_or_create(raw, strict=False)
            try:
                if cooked.py_type == "app.bsky.feed.post":
                    # Extract post data
                    text = getattr(cooked, 'text', '')
                    created_at = getattr(cooked, 'created_at', '')
                    langs = getattr(cooked, 'langs', [])
                    language = langs[0] if langs else None
                    
                    # Construct post URI from the operation path
                    post_uri = f"at://{author_did}/{op.path}"
                    
                    # Check cache for handle
                    cached_handle = get_cached_handle(author_did)
                    
                    # Convert raw data to JSON string for storage
                    raw_json = json.dumps(raw, cls=JSONExtra)
                    
                    # Save to database (fast, no network calls)
                    post_id = save_post_to_db(author_did, cached_handle, text, created_at, language, post_uri, raw_json)
                    posts_processed += 1
                    
                    # If no cached handle, queue for background resolution
                    if cached_handle is None:
                        if author_did in pending_resolutions:
                            pending_resolutions[author_did].append(post_id)
                        else:
                            pending_resolutions[author_did] = [post_id]
                            # Queue DID for resolution with current post_id
                            resolution_queue.put((author_did, [post_id]))
                            resolutions_queued += 1
                    
                    handle_display = cached_handle or "resolving..."
                    lprint(f"Saved post from @{handle_display}: {text[:50]}{'...' if len(text) > 50 else ''}")
            except Exception as e:
                total_errors += 1
                error_filename = f'errors/{total_errors}.json'
                with open(error_filename, 'w') as f:
                    json.dump(raw, f, indent=2, cls=JSONExtra)
                lprint(f"Error processing message: {e}, saved to {error_filename}")

def sync_cached_handles_to_posts():
    """Sync cached handles to posts that haven't been updated yet"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE posts p
            JOIN did_cache dc ON p.author_did = dc.did
            SET p.author_handle = dc.handle
            WHERE p.author_handle IS NULL 
            AND dc.handle IS NOT NULL
        ''')
        
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if updated_count > 0:
            lprint(f"🔄 Synced {updated_count} posts with cached handles")
        
        return updated_count
    except mysql.connector.Error as e:
        lprint(f"Error syncing cached handles: {e}")
        return 0

try:
    client.start(on_message_handler)
finally:
    # Shutdown worker threads
    lprint("Shutting down worker threads...")
    for _ in workers:
        resolution_queue.put((None, None))  # Shutdown signal
    for worker in workers:
        worker.join(timeout=5)