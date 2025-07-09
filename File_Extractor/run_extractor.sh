#!/bin/bash
# Launcher script for Bluesky File Extractor

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Bluesky File Extractor${NC}"
echo -e "${BLUE}=========================${NC}"

# Check if dependencies are installed
if ! python3 -c "import atproto, mysql.connector" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
fi

# Check database connectivity
echo -e "${YELLOW}🔍 Checking database connectivity...${NC}"
if ! python3 -c "
import mysql.connector
try:
    conn = mysql.connector.connect(
        host='mariadb',
        database='bsky_db',
        user='bsky_user',
        password='bsky_password',
        port=3306
    )
    conn.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"; then
    echo -e "${RED}❌ Cannot connect to database${NC}"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data

# Run the file extractor
echo -e "${GREEN}🎯 Starting file extraction...${NC}"
echo -e "${YELLOW}📁 Files will be saved to: $(pwd)/data/${NC}"
echo -e "${YELLOW}📊 Use Ctrl+C to stop${NC}"
echo

python3 file_extractor.py
