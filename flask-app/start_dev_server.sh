#!/bin/bash
# Development startup script for Bluesky Posts Explorer
# Single-threaded development server with auto-reload

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Bluesky Posts Explorer Development Server...${NC}"

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo -e "${RED}Error: app.py not found. Please run this script from the flask-app directory.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
    cd ..
    python3 -m venv venv
    cd flask-app
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source ../venv/bin/activate

# Install/update dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r ../requirements.txt

# Set environment variables for development
export FLASK_ENV=development
export FLASK_DEBUG=1
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."

# Start the development server with auto-reload
echo -e "${GREEN}Starting development server with auto-reload...${NC}"
echo -e "${YELLOW}Server will be available at: http://0.0.0.0:5000${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"

# Use Gunicorn in development mode with reload
gunicorn --config gunicorn.conf.py --reload --workers 1 --threads 1 app:app
