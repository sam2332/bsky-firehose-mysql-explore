# Gunicorn configuration file for Bluesky Posts Explorer
# Similar to Unicorn's multi-worker setup

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Recommended formula
worker_class = "gthread"  # Multi-threaded workers for better concurrency
threads = 2  # Number of threads per worker
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Performance tuning
preload_app = True  # Load application before forking workers
daemon = False  # Don't daemonize for Docker/systemd compatibility
enable_stdio_inheritance = True  # Better logging in containers

# Security
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'bluesky-posts-explorer'

# Worker management
worker_tmp_dir = '/dev/shm'  # Use memory for worker temp files if available
worker_class = 'gthread'  # Multi-threaded workers

# SSL (if needed)
# keyfile = None
# certfile = None

# Graceful restart
graceful_timeout = 30
reload = False  # Set to True for development

# Environment variables
raw_env = []

# Hooks
def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Bluesky Posts Explorer server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("worker received SIGABRT signal")
