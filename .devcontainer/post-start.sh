#!/bin/bash

# Post-start script - runs every time the container starts
echo "🔄 Container started, checking services..."

# Check if MariaDB is running
if mysqladmin ping -h mariadb -u bsky_user -pbsky_password --silent; then
    echo "✅ MariaDB is running"
else
    echo "⚠️ MariaDB is not responding"
fi

echo "🌐 Services available:"
echo "  📊 phpMyAdmin: http://localhost:8080"
echo "  🗄️ MariaDB: localhost:3306"
