import json
import sqlite3
import threading
import queue
from datetime import datetime
from atproto_client.models import get_or_create
from atproto import CAR, models, IdResolver
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message

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

# Initialize SQLite database
def init_database():
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    # Posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_did TEXT,
            author_handle TEXT,
            text TEXT,
            created_at TEXT,
            language TEXT,
            post_uri TEXT,
            raw_data TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # DID to handle cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS did_cache (
            did TEXT PRIMARY KEY,
            handle TEXT,
            resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            failed_attempts INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def get_cached_handle(did):
    """Get handle from cache if available"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    cursor.execute('SELECT handle FROM did_cache WHERE did = ?', (did,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def cache_handle(did, handle):
    """Cache the DID to handle mapping"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO did_cache (did, handle, resolved_at, failed_attempts)
        VALUES (?, ?, CURRENT_TIMESTAMP, 0)
    ''', (did, handle))
    conn.commit()
    conn.close()

def mark_resolution_failed(did):
    """Mark that resolution failed for this DID"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO did_cache (did, handle, resolved_at, failed_attempts)
        VALUES (?, NULL, CURRENT_TIMESTAMP, 
                COALESCE((SELECT failed_attempts FROM did_cache WHERE did = ?), 0) + 1)
    ''', (did, did))
    conn.commit()
    conn.close()

def should_retry_resolution(did):
    """Check if we should retry resolution for a failed DID"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT failed_attempts, resolved_at 
        FROM did_cache 
        WHERE did = ? AND handle IS NULL
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
    from datetime import datetime, timedelta
    last_attempt = datetime.fromisoformat(resolved_at)
    return datetime.now() - last_attempt > timedelta(hours=1)

# Global queues for thread communication
resolution_queue = queue.Queue()  # DIDs to resolve
update_queue = queue.Queue()      # Updates to apply to database

def update_post_handle(post_id, handle):
    """Update a post's handle in the database"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE posts SET author_handle = ? WHERE id = ?', (handle, post_id))
    conn.commit()
    conn.close()

def save_post_to_db(author_did, author_handle, text, created_at, language, post_uri, raw_data):
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO posts (author_did, author_handle, text, created_at, language, post_uri, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (author_did, author_handle, text, created_at, language, post_uri, raw_data))
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id

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
        
        return handle
        
    except Exception as e:
        print(f"Failed to resolve handle for {did}: {e}")
        return None

def did_resolution_worker():
    """Background worker thread for DID resolution"""
    while True:
        try:
            # Get work from queue (blocks until item available)
            did, post_ids = resolution_queue.get(timeout=1)
            
            if did is None:  # Shutdown signal
                break
                
            # Check cache first
            cached_handle = get_cached_handle(did)
            if cached_handle is not None:
                # Update all posts with this DID
                for post_id in post_ids:
                    update_queue.put(('update_post', post_id, cached_handle))
                resolution_queue.task_done()
                continue
            
            # Check if we should retry failed resolutions
            if not should_retry_resolution(did):
                resolution_queue.task_done()
                continue
            
            # Try to resolve from network
            handle = resolve_handle_from_did_sync(did)
            
            # Queue database updates
            if handle:
                update_queue.put(('cache_success', did, handle))
                for post_id in post_ids:
                    update_queue.put(('update_post', post_id, handle))
                print(f"Resolved and cached: {did} -> @{handle}")
            else:
                update_queue.put(('cache_failure', did))
                print(f"Failed to resolve handle for {did}")
            
            resolution_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in DID resolution worker: {e}")
            resolution_queue.task_done()

def process_database_updates():
    """Process queued database updates on main thread"""
    try:
        while True:
            update_type, *args = update_queue.get_nowait()
            
            if update_type == 'update_post':
                post_id, handle = args
                update_post_handle(post_id, handle)
            elif update_type == 'cache_success':
                did, handle = args
                cache_handle(did, handle)
            elif update_type == 'cache_failure':
                did = args[0]
                mark_resolution_failed(did)
                
            update_queue.task_done()
            
    except queue.Empty:
        pass  # No more updates to process

# Initialize the database
init_database()

# Start background worker threads
num_workers = 2  # Number of DID resolution worker threads
workers = []
for i in range(num_workers):
    worker = threading.Thread(target=did_resolution_worker, daemon=True)
    worker.start()
    workers.append(worker)

print(f"Started {num_workers} DID resolution worker threads")

# Track DIDs being resolved to batch requests
pending_resolutions = {}  # did -> list of post_ids

client = FirehoseSubscribeReposClient()

# all of this undocumented horseshit is based on cargo-culting the bollocks out of
# https://github.com/MarshalX/atproto/blob/main/examples/firehose/sub_repos.py
# and
# https://github.com/MarshalX/bluesky-feed-generator/blob/main/server/data_stream.py

def on_message_handler(message):
    # Process any pending database updates first
    process_database_updates()
    
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
                
                # If no cached handle, queue for background resolution
                if cached_handle is None:
                    if author_did in pending_resolutions:
                        pending_resolutions[author_did].append(post_id)
                    else:
                        pending_resolutions[author_did] = [post_id]
                        # Queue DID for resolution
                        resolution_queue.put((author_did, pending_resolutions[author_did].copy()))
                        pending_resolutions[author_did] = []  # Reset for next batch
                
                handle_display = cached_handle or "resolving..."
                print(f"Saved post from @{handle_display}: {text[:50]}{'...' if len(text) > 50 else ''}")

try:
    client.start(on_message_handler)
finally:
    # Shutdown worker threads
    print("Shutting down worker threads...")
    for _ in workers:
        resolution_queue.put((None, None))  # Shutdown signal
    for worker in workers:
        worker.join(timeout=5)