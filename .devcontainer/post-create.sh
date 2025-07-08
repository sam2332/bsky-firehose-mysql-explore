#!/bin/bash

# Post-create script for dev container setup
echo "🚀 Setting up Python development environment..."

# Create persistent database directory
echo "📁 Creating persistent database directory..."
mkdir -p /workspace/db
chmod 755 /workspace/db
echo "✅ Database directory created at /workspace/db"

# Install project dependencies
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python requirements..."
    pip install -r requirements.txt
else
    echo "📦 Installing common dependencies..."
    pip install \
        atproto \
        atproto-client \
        atproto-firehose \
        mysqlclient \
        PyMySQL \
        sqlalchemy \
        alembic \
        python-dotenv \
        jupyter \
        pandas \
        requests
fi

# Wait for MariaDB to be ready
echo "⏳ Waiting for MariaDB to be ready..."
until mysqladmin ping -h mariadb -u bsky_user -pbsky_password --silent; do
    echo "Waiting for MariaDB..."
    sleep 2
done

echo "✅ MariaDB is ready!"

# Set up database migration tools
echo "🗄️ Setting up database..."
if [ ! -f "alembic.ini" ]; then
    echo "Initializing Alembic..."
    alembic init migrations
    
    # Update alembic.ini with our database URL
    sed -i 's|sqlalchemy.url = .*|sqlalchemy.url = mysql://bsky_user:bsky_password@mariadb:3306/bsky_db|' alembic.ini
fi

# Run database setup
echo "🔧 Running database setup..."
python setup_database.py

echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Run the SQLite to MariaDB migration: python migrate_to_mysql.py"
echo "  2. Access phpMyAdmin at http://localhost:8080"
echo "  3. Start developing! 🚀"
