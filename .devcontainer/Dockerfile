FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Install MariaDB client and other dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        mariadb-client \
        default-libmysqlclient-dev \
        build-essential \
        pkg-config \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install Python packages for MariaDB and development tools
RUN pip install --no-cache-dir \
    mysqlclient \
    PyMySQL \
    sqlalchemy \
    alembic \
    python-dotenv \
    pip \
    setuptools \
    wheel

# Create workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

USER vscode
