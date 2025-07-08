#!/usr/bin/env python3
"""
Aggressive backlog processor to resolve unresolved DIDs
This can be run separately to catch up on the backlog
"""
import sqlite3
import threading
import queue
import time
from atproto import IdResolver

def resolve_handle_from_did_sync(did):
    """Synchronous DID resolution"""
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
        print(f"Failed to resolve handle for {did}: {e}")
        return None

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

def update_posts_for_did(did, handle):
    """Update all posts for a DID with the resolved handle"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE posts SET author_handle = ? WHERE author_did = ?', (handle, did))
    updated_count = cursor.rowcount
    conn.commit()
    conn.close()
    return updated_count

def get_unresolved_dids(limit=100):
    """Get unresolved DIDs from database"""
    conn = sqlite3.connect('bsky_posts.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.author_did, COUNT(*) as post_count
        FROM posts p
        LEFT JOIN did_cache dc ON p.author_did = dc.did
        WHERE p.author_handle IS NULL 
        AND (dc.did IS NULL OR (dc.handle IS NULL AND dc.failed_attempts < 3))
        GROUP BY p.author_did
        ORDER BY post_count DESC
        LIMIT ?
    ''', (limit,))
    
    result = cursor.fetchall()
    conn.close()
    return result

def backlog_worker(work_queue, results_queue):
    """Worker thread for processing backlog"""
    worker_id = threading.current_thread().ident
    
    while True:
        try:
            did = work_queue.get(timeout=1)
            if did is None:  # Shutdown signal
                break
                
            print(f"Worker {worker_id} resolving {did}")
            handle = resolve_handle_from_did_sync(did)
            results_queue.put((did, handle))
            work_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Worker {worker_id} error: {e}")
            work_queue.task_done()

def main():
    print("Aggressive Backlog Processor")
    print("=" * 40)
    
    # Get initial statistics
    unresolved_dids = get_unresolved_dids(1000)  # Get top 1000 unresolved DIDs
    print(f"Found {len(unresolved_dids)} unresolved DIDs to process")
    
    if not unresolved_dids:
        print("No unresolved DIDs found!")
        return
    
    # Create queues
    work_queue = queue.Queue()
    results_queue = queue.Queue()
    
    # Start worker threads
    num_workers = 15  # More aggressive processing
    workers = []
    for i in range(num_workers):
        worker = threading.Thread(target=backlog_worker, args=(work_queue, results_queue), daemon=True)
        worker.start()
        workers.append(worker)
    
    print(f"Started {num_workers} worker threads")
    
    # Queue work
    for did, post_count in unresolved_dids:
        work_queue.put(did)
    
    print(f"Queued {len(unresolved_dids)} DIDs for processing")
    
    # Process results as they come in
    processed = 0
    successful = 0
    failed = 0
    
    while processed < len(unresolved_dids):
        try:
            did, handle = results_queue.get(timeout=30)
            processed += 1
            
            if handle:
                # Cache the successful resolution
                cache_handle(did, handle)
                # Update all posts for this DID
                updated_count = update_posts_for_did(did, handle)
                successful += 1
                print(f"✓ Resolved {did} -> @{handle} (updated {updated_count} posts) [{processed}/{len(unresolved_dids)}]")
            else:
                # Mark as failed
                mark_resolution_failed(did)
                failed += 1
                print(f"✗ Failed to resolve {did} [{processed}/{len(unresolved_dids)}]")
                
        except queue.Empty:
            print("Timeout waiting for results, continuing...")
            break
    
    # Shutdown workers
    for _ in workers:
        work_queue.put(None)
    for worker in workers:
        worker.join(timeout=5)
    
    print(f"\nCompleted! Processed: {processed}, Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    main()
