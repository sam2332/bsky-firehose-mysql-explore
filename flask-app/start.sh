#!/bin/bash

# Bluesky Posts Explorer - Start Script

echo "🚀 Starting Bluesky Posts Explorer..."

# Change to flask-app directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Start the Flask application
echo "🌐 Starting Flask application..."
echo "📱 Access the web interface at: http://localhost:5000"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

python app.py
