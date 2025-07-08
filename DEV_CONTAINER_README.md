# Bluesky Monitor - Dev Container Setup

This project now includes a complete Docker dev container setup with MariaDB persistence.

## 🚀 Quick Start

1. **Open in Dev Container**:
   - Open this folder in VS Code
   - When prompted, click "Reopen in Container" or use `Ctrl+Shift+P` -> "Dev Containers: Reopen in Container"

2. **Wait for Setup**:
   - The container will automatically set up Python, MariaDB, and all dependencies
   - Database files are persisted in the `./db/` folder (ignored by git)

3. **Access Services**:
   - **phpMyAdmin**: http://localhost:8080 (User: `bsky_user`, Password: `bsky_password`)
   - **MariaDB**: `localhost:3306` (from host) or `mariadb:3306` (from container)

## 📊 Database Migration

If you have existing SQLite data (`bsky_posts.db`), run the migration:

```bash
python migrate_to_mysql.py
```

This will:
- Analyze your SQLite schema
- Create corresponding MySQL tables
- Transfer all data with progress tracking
- Verify data integrity

## 🔧 Database Management

### Connection Details
- **Host**: `mariadb` (from container) or `localhost` (from host)
- **Port**: `3306`
- **Database**: `bsky_db`
- **Username**: `bsky_user`
- **Password**: `bsky_password`
- **Root Password**: `rootpassword`

### Using SQLTools (VS Code Extension)
The dev container includes SQLTools with MySQL driver pre-configured. You can:
1. Open the SQLTools panel in VS Code
2. Connect to "MariaDB Local" 
3. Browse tables and run queries directly in VS Code

### Manual Database Setup
If you need to reset or manually set up the database:

```bash
python setup_database.py
```

## 📁 File Persistence

- **Database files**: Stored in `./db/` folder on your host machine
- **Python packages**: Installed in container, reinstalled on rebuild
- **Source code**: Mounted from your local workspace

This means you can safely rebuild the container without losing your database data.

## 🛠️ Development Workflow

1. **Start the container**: Database starts automatically
2. **Code changes**: Edit files normally, changes are reflected immediately
3. **Database queries**: Use phpMyAdmin or SQLTools in VS Code
4. **Container rebuild**: Database data persists in `./db/` folder

## 📦 Included Extensions

- Python support (with pylint, black, isort)
- SQLTools with MySQL driver
- JSON support
- Python debugger

## 🗄️ Schema Overview

The migration creates tables based on your existing SQLite structure. For new setups, it creates:

- **posts**: Main posts table with engagement metrics
- **authors**: Author information and stats
- **monitoring_stats**: Daily monitoring statistics

## 🚨 Troubleshooting

### Container won't start
- Check Docker is running
- Ensure no other services are using ports 3306 or 8080

### Database connection issues
- Wait for the "MariaDB is ready!" message in the terminal
- Check if the `db/` folder has proper permissions

### Migration problems
- Ensure SQLite database (`bsky_posts.db`) exists
- Check MariaDB logs: `docker compose logs mariadb`

### Permission issues with db folder
```bash
# From the container terminal:
sudo chown -R vscode:vscode /workspace/db
chmod 755 /workspace/db
```
