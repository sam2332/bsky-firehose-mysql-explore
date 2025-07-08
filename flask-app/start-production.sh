#!/bin/bash

# Production start script for Bluesky Posts Explorer
# Multi-worker setup similar to Unicorn

set -e

echo "🚀 Starting Bluesky Posts Explorer (Production Mode)"

# Change to the directory containing this script
cd "$(dirname "$0")"

# Source environment variables if .env file exists
if [ -f ".env" ]; then
    echo "📄 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default environment variables if not set
export FLASK_ENV=${FLASK_ENV:-production}
export FLASK_DEBUG=${FLASK_DEBUG:-0}
export MYSQL_HOST=${MYSQL_HOST:-mariadb}
export MYSQL_DATABASE=${MYSQL_DATABASE:-bsky_db}
export MYSQL_USER=${MYSQL_USER:-bsky_user}
export MYSQL_PASSWORD=${MYSQL_PASSWORD:-bsky_password}
export MYSQL_PORT=${MYSQL_PORT:-3306}

# Function to handle shutdown
cleanup() {
    echo "🛑 Shutting down Bluesky Posts Explorer..."
    if [ ! -z "$GUNICORN_PID" ]; then
        kill -TERM $GUNICORN_PID 2>/dev/null || true
        wait $GUNICORN_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi


# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt



# Calculate the number of workers
WORKERS=${WORKERS:-$(($(nproc) * 2 + 1))}
echo "🔧 Starting with $WORKERS worker processes"

# Start Gunicorn with the configuration file
echo "🌐 Starting Gunicorn server..."
echo "📱 Access the web interface at: http://localhost:5000"
echo "⏹️  Press Ctrl+C to stop the server"
echo "📊 Worker processes: $WORKERS"
echo "🔧 Configuration: gunicorn.conf.py"
echo ""

# Start Gunicorn and get its PID
gunicorn --config gunicorn.conf.py app:app &
GUNICORN_PID=$!

# Wait for Gunicorn to start
sleep 2

# Check if Gunicorn is running
if kill -0 $GUNICORN_PID 2>/dev/null; then
    echo "✅ Gunicorn started successfully (PID: $GUNICORN_PID)"
    echo "🔍 Monitoring worker processes..."
    
    # Monitor the process
    wait $GUNICORN_PID
else
    echo "❌ Failed to start Gunicorn"
    exit 1
fi
