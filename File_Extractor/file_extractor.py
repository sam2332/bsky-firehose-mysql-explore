import json
import mysql.connector
import threading
import queue
import time
import os
import hashlib
import configparser
from datetime import datetime
from pathlib import Path
from atproto_client.models import get_or_create
from atproto import CAR, models, IdResolver
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message

def lprint(string, *args, **kwargs):
    """Prints a message with a timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {string}", *args, **kwargs)

# Load configuration
def load_config():
    """Load configuration from config.ini file"""
    config = configparser.ConfigParser()
    config_file = Path(__file__).parent / "config.ini"
    
    # Default configuration
    defaults = {
        'DB_HOST': 'mariadb',
        'DB_NAME': 'bsky_db',
        'DB_USER': 'bsky_user',
        'DB_PASSWORD': 'bsky_password',
        'DB_PORT': '3306',
        'STATS_INTERVAL': '30',
        'RESOLUTION_WORKERS': '1'
    }
    
    if config_file.exists():
        config.read(config_file)
        # Get values from config file or use defaults
        for key, default_value in defaults.items():
            if 'DEFAULT' in config and key in config['DEFAULT']:
                defaults[key] = config['DEFAULT'][key]
    
    return defaults

CONFIG = load_config()

# Database configuration
MYSQL_CONFIG = {
    'host': CONFIG['DB_HOST'],
    'database': CONFIG['DB_NAME'],
    'user': CONFIG['DB_USER'],
    'password': CONFIG['DB_PASSWORD'],
    'port': int(CONFIG['DB_PORT']),
    'autocommit': True
}

# Base directory for extracted files
BASE_DIR = Path(__file__).parent / "data"

class JSONExtra(json.JSONEncoder):
    """Handle CID objects in JSON serialization"""
    def default(self, obj):
        try:
            result = json.JSONEncoder.default(self, obj)
            return result
        except:
            return repr(obj)

def init_database():
    """Initialize database connection"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Create table for tracking extracted files
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extracted_files (
                id INT AUTO_INCREMENT PRIMARY KEY,
                author_did VARCHAR(255) NOT NULL,
                author_handle VARCHAR(255),
                post_uri VARCHAR(512) NOT NULL,
                file_path VARCHAR(512) NOT NULL,
                file_type VARCHAR(50),
                file_size INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_author_did (author_did),
                INDEX idx_author_handle (author_handle),
                INDEX idx_post_uri (post_uri)
            )
        ''')
        
        conn.commit()
        conn.close()
        lprint("✅ Database initialized successfully")
    except mysql.connector.Error as e:
        lprint(f"❌ Failed to initialize database: {e}")
        raise

def get_cached_handle(did):
    """Get handle from cache if available"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT handle FROM did_cache WHERE did = %s AND handle IS NOT NULL', (did,))
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

def resolve_handle_from_did_sync(did):
    """Synchronous DID resolution"""
    try:
        resolver = IdResolver()
        did_doc = resolver.did.resolve(did)
        
        handle = None
        if did_doc and hasattr(did_doc, 'also_known_as') and did_doc.also_known_as:
            for aka in did_doc.also_known_as:
                if aka.startswith('at://'):
                    handle = aka[5:]  # Remove 'at://' prefix
                    break
        
        if not handle and did_doc and hasattr(did_doc, 'service') and did_doc.service:
            for service in did_doc.service:
                if hasattr(service, 'service_endpoint') and isinstance(service.service_endpoint, str):
                    if service.service_endpoint.startswith('https://'):
                        endpoint = service.service_endpoint
                        if '.bsky.social' in endpoint:
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

def determine_file_type_and_extension(data, mime_type=None):
    """Determine file type and extension from binary data"""
    if not data:
        return 'unknown', '.bin'
    
    # Check magic bytes for common file types
    if data.startswith(b'\xFF\xD8\xFF'):
        return 'image/jpeg', '.jpg'
    elif data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png', '.png'
    elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return 'image/gif', '.gif'
    elif data.startswith(b'RIFF') and b'WEBP' in data[:12]:
        return 'image/webp', '.webp'
    elif data.startswith(b'%PDF'):
        return 'application/pdf', '.pdf'
    elif data.startswith(b'PK\x03\x04'):
        return 'application/zip', '.zip'
    elif data.startswith(b'\x00\x00\x00\x20ftypmp4'):
        return 'video/mp4', '.mp4'
    elif data.startswith(b'\x1a\x45\xdf\xa3'):
        return 'video/webm', '.webm'
    elif data.startswith(b'OggS'):
        return 'audio/ogg', '.ogg'
    elif data.startswith(b'ID3') or data.startswith(b'\xFF\xFB'):
        return 'audio/mpeg', '.mp3'
    elif data.startswith(b'fLaC'):
        return 'audio/flac', '.flac'
    elif data.startswith(b'RIFF') and b'AVI ' in data[:12]:
        return 'video/avi', '.avi'
    elif data.startswith(b'\x00\x00\x00\x1cftyp'):
        return 'video/quicktime', '.mov'
    
    # Fallback to mime_type if provided
    if mime_type:
        extension_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/webm': '.webm',
            'audio/mpeg': '.mp3',
            'audio/ogg': '.ogg',
            'application/pdf': '.pdf',
            'text/plain': '.txt',
            'application/json': '.json'
        }
        return mime_type, extension_map.get(mime_type, '.bin')
    
    return 'application/octet-stream', '.bin'

def save_extracted_file(author_did, author_handle, post_uri, file_data, file_type, created_at):
    """Save extracted file to organized directory structure"""
    try:
        # Parse post URI to get post ID
        post_id = post_uri.split('/')[-1] if '/' in post_uri else 'unknown'
        
        # Parse created_at for month folder
        try:
            if created_at.endswith('Z'):
                created_at = created_at[:-1] + '+00:00'
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            month_folder = dt.strftime('%Y-%m')
        except:
            month_folder = datetime.now().strftime('%Y-%m')
        
        # Determine file type and extension
        file_mime, extension = determine_file_type_and_extension(file_data, file_type)
        
        # Create safe filename from handle
        safe_handle = author_handle if author_handle else author_did.replace(':', '_')
        safe_handle = ''.join(c for c in safe_handle if c.isalnum() or c in '._-')
        
        # Create directory structure
        user_dir = BASE_DIR / safe_handle / month_folder
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with hash to avoid collisions
        file_hash = hashlib.md5(file_data).hexdigest()[:8]
        filename = f"{post_id}_{file_hash}{extension}"
        file_path = user_dir / filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Record in database
        try:
            conn = mysql.connector.connect(**MYSQL_CONFIG)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO extracted_files (author_did, author_handle, post_uri, file_path, file_type, file_size)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (author_did, author_handle, post_uri, str(file_path), file_mime, len(file_data)))
            conn.commit()
            conn.close()
        except mysql.connector.Error as e:
            lprint(f"Error recording extracted file in database: {e}")
        
        lprint(f"📁 Saved file: {file_path} ({len(file_data)} bytes, {file_mime})")
        return str(file_path)
        
    except Exception as e:
        lprint(f"Error saving extracted file: {e}")
        return None

# Global queues for thread communication
resolution_queue = queue.Queue()
handle_cache = {}

def did_resolution_worker():
    """Background worker thread for DID resolution"""
    worker_id = threading.current_thread().ident
    lprint(f"DID resolution worker {worker_id} started")
    
    while True:
        try:
            did = resolution_queue.get(timeout=1)
            
            if did is None:  # Shutdown signal
                lprint(f"Worker {worker_id} shutting down")
                break
            
            # Check cache first
            cached_handle = get_cached_handle(did)
            if cached_handle:
                handle_cache[did] = cached_handle
                resolution_queue.task_done()
                continue
            
            # Try to resolve from network
            handle = resolve_handle_from_did_sync(did)
            
            if handle:
                cache_handle(did, handle)
                handle_cache[did] = handle
                #lprint(f"Worker {worker_id} resolved: {did} -> @{handle}")
            #else:
                #lprint(f"Worker {worker_id} failed to resolve: {did}")
            
            resolution_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            #lprint(f"Error in DID resolution worker {worker_id}: {e}")
            resolution_queue.task_done()

def extract_embedded_files(embed_data):
    """Extract files from embed data"""
    files = []
    
    if not embed_data:
        return files
    
    # Handle different embed types
    # Check for images (app.bsky.embed.images)
    if hasattr(embed_data, 'images') and embed_data.images:
        for img in embed_data.images:
            if hasattr(img, 'image'):
                # img.image is a BlobRef
                image_ref = img.image
                files.append({
                    'type': 'image',
                    'ref': image_ref,
                    'mime_type': getattr(image_ref, 'mime_type', 'image/jpeg'),
                    'size': getattr(image_ref, 'size', 0),
                    'alt': getattr(img, 'alt', ''),
                    'aspect_ratio': getattr(img, 'aspect_ratio', None)
                })
    
    # Check for external links with images (app.bsky.embed.external)
    if hasattr(embed_data, 'external') and embed_data.external:
        external = embed_data.external
        if hasattr(external, 'thumb') and external.thumb:
            files.append({
                'type': 'external_thumb',
                'ref': external.thumb,
                'mime_type': getattr(external.thumb, 'mime_type', 'image/jpeg'),
                'size': getattr(external.thumb, 'size', 0)
            })
    
    # Check for record with media (app.bsky.embed.record_with_media)
    if hasattr(embed_data, 'media') and embed_data.media:
        media = embed_data.media
        # Recursively extract from media
        media_files = extract_embedded_files(media)
        files.extend(media_files)
    
    # Check for video (app.bsky.embed.video)
    if hasattr(embed_data, 'video') and embed_data.video:
        video = embed_data.video
        files.append({
            'type': 'video',
            'ref': video,
            'mime_type': getattr(video, 'mime_type', 'video/mp4'),
            'size': getattr(video, 'size', 0)
        })
    
    return files

# Initialize the database
init_database()

# Start background worker thread for DID resolution
num_workers = int(CONFIG.get('RESOLUTION_WORKERS', 1))
workers = []
for i in range(num_workers):
    worker = threading.Thread(target=did_resolution_worker, daemon=True)
    worker.start()
    workers.append(worker)

lprint(f"Started {num_workers} DID resolution worker thread(s)")

# Statistics tracking
files_extracted = 0
posts_processed = 0
last_stats_time = time.time()
stats_interval = int(CONFIG.get('STATS_INTERVAL', 30))

client = FirehoseSubscribeReposClient()

def on_message_handler(message):
    global files_extracted, posts_processed, last_stats_time
    
    # Print periodic statistics
    current_time = time.time()
    if current_time - last_stats_time > stats_interval:
        lprint(f"Stats: {posts_processed} posts processed, {files_extracted} files extracted")
        last_stats_time = current_time
    
    commit = parse_subscribe_repos_message(message)
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return
    
    car = CAR.from_bytes(commit.blocks)
    author_did = commit.repo
    
    for op in commit.ops:
        if op.action in ["create"] and op.cid:
            raw = car.blocks.get(op.cid)
            cooked = get_or_create(raw, strict=False)
            
            try:
                if cooked and hasattr(cooked, 'py_type') and cooked.py_type == "app.bsky.feed.post":
                    posts_processed += 1
                    
                    # Extract post data
                    created_at = getattr(cooked, 'created_at', datetime.now().isoformat())
                    post_uri = f"at://{author_did}/{op.path}"
                    
                    # Get or queue handle resolution
                    author_handle = handle_cache.get(author_did)
                    if not author_handle:
                        author_handle = get_cached_handle(author_did)
                        if author_handle:
                            handle_cache[author_did] = author_handle
                        else:
                            resolution_queue.put(author_did)
                    
                    # Check for embedded files
                    embed = getattr(cooked, 'embed', None)
                    if embed:
                        files = extract_embedded_files(embed)
                        
                        for file_info in files:
                            # Extract file data from CAR blocks
                            file_ref = file_info['ref']
                            file_cid = None
                            
                            # Try to get CID from BlobRef
                            if hasattr(file_ref, 'link'):
                                file_cid = file_ref.link
                            elif hasattr(file_ref, 'cid'):
                                file_cid = file_ref.cid
                            elif hasattr(file_ref, '$link'):
                                file_cid = file_ref['$link']
                            
                            if file_cid:
                                file_data = car.blocks.get(file_cid)
                                
                                if file_data:
                                    saved_path = save_extracted_file(
                                        author_did,
                                        author_handle,
                                        post_uri,
                                        file_data,
                                        file_info['mime_type'],
                                        created_at
                                    )
                                    
                                    if saved_path:
                                        files_extracted += 1
                                        handle_display = author_handle or "resolving..."
                                        lprint(f"📎 Extracted {file_info['type']} from @{handle_display}: {file_info['mime_type']} ({file_info['size']} bytes)")
                                #else:
                                #    lprint(f"⚠️  Could not find file data for CID: {file_cid}")
                            else:
                                lprint(f"⚠️  Could not extract CID from file reference: {type(file_ref)}")
                    
            except Exception as e:
                lprint(f"Error processing message: {e}")

try:
    lprint("🚀 Starting Bluesky file extractor...")
    client.start(on_message_handler)
finally:
    # Shutdown worker threads
    lprint("Shutting down worker threads...")
    for _ in workers:
        resolution_queue.put(None)  # Shutdown signal
    for worker in workers:
        worker.join(timeout=5)
    lprint("File extractor stopped")
