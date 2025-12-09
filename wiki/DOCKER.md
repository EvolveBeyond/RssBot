# Docker Deployment Guide

This guide covers comprehensive Docker deployment strategies for the RSS Bot platform, from development containers to production-ready orchestration.

## 🐳 Docker Overview

The RSS Bot platform provides flexible Docker deployment options:

1. **Development Setup** - Quick start with Docker Compose
2. **Production Deployment** - Optimized containers for production
3. **Kubernetes Integration** - Scalable container orchestration
4. **Custom Images** - Building specialized service containers

## 🏃 Quick Start with Docker

### Prerequisites
```bash
# Install Docker and Docker Compose
# Ubuntu/Debian
sudo apt update && sudo apt install docker.io docker-compose

# Arch Linux  
sudo pacman -S docker docker-compose

# macOS
brew install docker docker-compose

# Start Docker daemon
sudo systemctl start docker  # Linux
# Or start Docker Desktop on macOS/Windows
```

### Basic Development Setup
```bash
# Navigate to project root
cd /path/to/RssBot

# Copy environment configuration
cp .env.example .env
# Edit .env with your Telegram bot token

# Start infrastructure services
docker-compose -f infra/docker-compose.yml up -d postgres redis

# Verify services are running
docker-compose -f infra/docker-compose.yml ps
```

### Full Stack with Docker
```bash
# Start complete platform in Docker
docker-compose -f infra/docker-compose.yml up -d

# View logs
docker-compose -f infra/docker-compose.yml logs -f

# Stop all services
docker-compose -f infra/docker-compose.yml down
```

## 🏗️ Docker Architecture

### Service Container Strategy

#### Infrastructure Containers
- **PostgreSQL**: Official postgres:15-alpine image
- **Redis**: Official redis:7-alpine image  
- **Nginx**: Custom configuration for reverse proxy

#### Application Containers
- **Base Image**: Custom Python image with Rye
- **Service Images**: Built from base with service-specific code
- **Shared Volumes**: Code mounting for development

### Network Architecture
```
┌─────────────────────────────────────────┐
│              Docker Network             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ Nginx   │  │ Redis   │  │Postgres │  │
│  │ :80/:443│  │ :6379   │  │ :5432   │  │
│  └────┬────┘  └─────────┘  └─────────┘  │
│       │                                 │
│  ┌────┴──────────────────────────────┐  │
│  │        Application Services       │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │  │
│  │  │ DB  │ │User │ │ Bot │ │Ctrl │  │  │
│  │  │:8001│ │:8008│ │:8002│ │:8004│  │  │
│  │  └─────┘ └─────┘ └─────┘ └─────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## 📦 Container Images

### Base Service Image
```dockerfile
# infra/Dockerfile.service (already created)
FROM python:3.11-slim as base

# System dependencies
RUN apt-get update && apt-get install -y \
    curl gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir rye
RUN rye sync --no-dev

COPY . .
RUN chown -R app:app /app
USER app

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Optimized Production Image
Create `infra/Dockerfile.production`:
```dockerfile
# Multi-stage production build
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl gcc g++ libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

# Install Rye
RUN curl -sSf https://rye-up.com/get | RYE_INSTALL_OPTION="--yes" bash
ENV PATH="/root/.rye/shims:$PATH"

WORKDIR /app
COPY pyproject.toml requirements.lock ./
RUN rye sync --no-dev --production

# Production stage
FROM python:3.11-slim as production

# Runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

# Copy Python environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY services/ ./services/
COPY scripts/ ./scripts/
COPY contracts/ ./contracts/

# Set ownership
RUN chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Service-Specific Images

#### Database Service Image
```dockerfile
# infra/Dockerfile.db
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq-dev curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir rye && rye sync --no-dev

COPY services/db_svc/ ./
COPY contracts/db_service.json ./contracts/

EXPOSE 8001
CMD ["python", "main.py"]
```

#### Bot Service Image
```dockerfile
# infra/Dockerfile.bot
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir rye && rye sync --no-dev

COPY services/bot_svc/ ./
COPY contracts/bot_service.json ./contracts/

EXPOSE 8002
CMD ["python", "main.py"]
```

## 🚀 Docker Compose Configurations

### Development Compose (Enhanced)
Create `infra/docker-compose.dev.yml`:
```yaml
version: '3.8'

services:
  # Infrastructure
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: rssbot_dev
      POSTGRES_USER: rssbot
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
      - ./init-dev.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rssbot"]
      interval: 10s
      timeout: 5s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # Development proxy for service testing
  nginx-dev:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-dev.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - postgres
      - redis

volumes:
  postgres_dev_data:
  redis_dev_data:
```

### Production Compose
Create `infra/docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  # Infrastructure with production settings
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf:ro
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    command: >
      redis-server 
      --maxmemory 256mb 
      --maxmemory-policy allkeys-lru
      --appendonly yes
    volumes:
      - redis_prod_data:/data
    restart: unless-stopped

  # Application services
  db_svc:
    build:
      context: ..
      dockerfile: infra/Dockerfile.production
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - SERVICE_TOKEN=${SERVICE_TOKEN}
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    command: ["python", "services/db_svc/main.py"]

  controller_svc:
    build:
      context: ..
      dockerfile: infra/Dockerfile.production
    environment:
      - LOCAL_ROUTER_MODE=${LOCAL_ROUTER_MODE:-false}
      - SERVICE_TOKEN=${SERVICE_TOKEN}
      - DB_SERVICE_URL=http://db_svc:8001
    depends_on:
      - db_svc
    restart: unless-stopped
    command: ["python", "services/controller_svc/main.py"]

  bot_svc:
    build:
      context: ..
      dockerfile: infra/Dockerfile.production
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_WEBHOOK_MODE=true
      - TELEGRAM_WEBHOOK_URL=${TELEGRAM_WEBHOOK_URL}
      - SERVICE_TOKEN=${SERVICE_TOKEN}
    restart: unless-stopped
    command: ["python", "services/bot_svc/main.py"]

  # Load balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - controller_svc
      - bot_svc
    restart: unless-stopped

volumes:
  postgres_prod_data:
  redis_prod_data:
```

### Router Mode Compose
Create `infra/docker-compose.router.yml`:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: rssbot
      POSTGRES_USER: rssbot  
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rssbot"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # Single service in router mode
  rssbot:
    build:
      context: ..
      dockerfile: infra/Dockerfile.service
    environment:
      - LOCAL_ROUTER_MODE=true
      - DATABASE_URL=postgresql://rssbot:${POSTGRES_PASSWORD}@postgres:5432/rssbot
      - REDIS_URL=redis://redis:6379/0
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - SERVICE_TOKEN=${SERVICE_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "8004:8004"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: ["python", "services/controller_svc/main.py"]

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-router.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - rssbot

volumes:
  postgres_data:
  redis_data:
```

## 🔧 Docker Utilities

### Build Scripts
Create `scripts/docker-build.sh`:
```bash
#!/bin/bash

set -e

echo "🐳 Building RSS Bot Docker images..."

# Build base image
docker build -t rssbot:base -f infra/Dockerfile.service .

# Build production image
docker build -t rssbot:production -f infra/Dockerfile.production .

# Build service-specific images
docker build -t rssbot/db:latest -f infra/Dockerfile.db .
docker build -t rssbot/bot:latest -f infra/Dockerfile.bot .

# Tag images for registry (optional)
if [[ -n "$DOCKER_REGISTRY" ]]; then
    docker tag rssbot:production $DOCKER_REGISTRY/rssbot:latest
    docker tag rssbot/db:latest $DOCKER_REGISTRY/rssbot-db:latest
    docker tag rssbot/bot:latest $DOCKER_REGISTRY/rssbot-bot:latest
    
    echo "Images tagged for registry: $DOCKER_REGISTRY"
fi

echo "✅ Build complete!"
```

### Deployment Scripts
Create `scripts/docker-deploy.sh`:
```bash
#!/bin/bash

set -e

ENVIRONMENT=${1:-development}
COMPOSE_FILE=""

case $ENVIRONMENT in
    "dev"|"development")
        COMPOSE_FILE="infra/docker-compose.dev.yml"
        ;;
    "prod"|"production") 
        COMPOSE_FILE="infra/docker-compose.prod.yml"
        ;;
    "router")
        COMPOSE_FILE="infra/docker-compose.router.yml"
        ;;
    *)
        echo "Usage: $0 [dev|prod|router]"
        exit 1
        ;;
esac

echo "🚀 Deploying RSS Bot ($ENVIRONMENT)..."

# Load environment variables
if [[ -f ".env.$ENVIRONMENT" ]]; then
    export $(cat .env.$ENVIRONMENT | xargs)
else
    echo "⚠️  .env.$ENVIRONMENT not found, using .env"
    export $(cat .env | xargs)
fi

# Pull latest images (production)
if [[ "$ENVIRONMENT" == "production" ]]; then
    docker-compose -f $COMPOSE_FILE pull
fi

# Deploy services
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Health check
if command -v curl &> /dev/null; then
    if [[ "$ENVIRONMENT" == "router" ]]; then
        curl -f http://localhost:8004/health || echo "❌ Health check failed"
    else
        curl -f http://localhost:8004/health || echo "❌ Controller health check failed"
        curl -f http://localhost:8001/health || echo "❌ Database health check failed"
    fi
fi

echo "✅ Deployment complete!"
```

### Monitoring Scripts
Create `scripts/docker-monitor.sh`:
```bash
#!/bin/bash

echo "📊 RSS Bot Docker Monitoring"
echo "============================="

# Container status
echo -e "\n🐳 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Resource usage
echo -e "\n💾 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Disk usage
echo -e "\n💿 Disk Usage:"
docker system df

# Network status
echo -e "\n🌐 Networks:"
docker network ls | grep rssbot

# Volume status  
echo -e "\n📁 Volumes:"
docker volume ls | grep rssbot
```

## 🔒 Security Best Practices

### Image Security
```dockerfile
# Use specific versions, not 'latest'
FROM python:3.11.6-slim

# Run as non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Remove unnecessary packages
RUN apt-get remove -y gcc g++ && apt-get autoremove -y

# Set read-only filesystem
COPY --chown=app:app . /app
```

### Container Configuration
```yaml
# docker-compose security settings
services:
  app:
    # Read-only root filesystem
    read_only: true
    tmpfs:
      - /tmp
      - /var/log
    
    # Resource limits
    mem_limit: 512m
    cpus: 0.5
    
    # Security options
    security_opt:
      - no-new-privileges:true
    
    # Network isolation
    networks:
      - app_network
```

### Secrets Management
```yaml
# Using Docker secrets
secrets:
  bot_token:
    external: true
  db_password:
    external: true

services:
  bot_svc:
    secrets:
      - bot_token
    environment:
      - TELEGRAM_BOT_TOKEN_FILE=/run/secrets/bot_token
```

## 🚢 Production Deployment

### Environment Preparation
```bash
# Create production environment file
cat > .env.production << EOF
POSTGRES_DB=rssbot_prod
POSTGRES_USER=rssbot_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)
SERVICE_TOKEN=$(openssl rand -base64 32)
TELEGRAM_BOT_TOKEN=your_production_bot_token
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
LOCAL_ROUTER_MODE=false
LOG_LEVEL=INFO
EOF
```

### SSL Configuration
```bash
# Generate SSL certificates (Let's Encrypt example)
mkdir -p infra/ssl
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem infra/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem infra/ssl/
```

### Production Deployment
```bash
# Deploy to production
./scripts/docker-build.sh
./scripts/docker-deploy.sh production

# Monitor logs
docker-compose -f infra/docker-compose.prod.yml logs -f

# Check service health
curl https://yourdomain.com/health
```

## 📈 Scaling with Docker

### Horizontal Scaling
```yaml
# Scale specific services
services:
  user_svc:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
```

### Load Balancing
```nginx
# nginx configuration for load balancing
upstream user_service {
    server user_svc_1:8008;
    server user_svc_2:8008;
    server user_svc_3:8008;
}

location /users/ {
    proxy_pass http://user_service;
    proxy_set_header Host $host;
}
```

## 🧪 Testing with Docker

### Integration Testing
Create `tests/docker-compose.test.yml`:
```yaml
version: '3.8'

services:
  postgres-test:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: rssbot_test
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    tmpfs:
      - /var/lib/postgresql/data

  redis-test:
    image: redis:7-alpine
    tmpfs:
      - /data

  app-test:
    build: 
      context: ..
      dockerfile: infra/Dockerfile.service
    environment:
      - DATABASE_URL=postgresql://test_user:test_pass@postgres-test:5432/rssbot_test
      - REDIS_URL=redis://redis-test:6379/0
      - ENVIRONMENT=testing
    depends_on:
      - postgres-test
      - redis-test
    command: ["python", "-m", "pytest", "tests/"]
```

### Test Execution
```bash
# Run integration tests
docker-compose -f tests/docker-compose.test.yml up --abort-on-container-exit
docker-compose -f tests/docker-compose.test.yml down -v
```

## 📚 Docker Best Practices

### Image Optimization
1. **Multi-stage builds** - Separate build and runtime stages
2. **Layer caching** - Order Dockerfile commands by change frequency
3. **Minimal base images** - Use alpine or slim variants
4. **Security scanning** - Scan images for vulnerabilities

### Container Management
1. **Health checks** - Implement proper health checking
2. **Resource limits** - Set CPU and memory limits
3. **Logging** - Use structured logging with proper drivers
4. **Monitoring** - Implement metrics collection

### Development Workflow
1. **Volume mounting** - Mount source code for development
2. **Environment separation** - Different configs per environment
3. **Service isolation** - Each service in its own container
4. **Dependency management** - Proper service startup ordering

This Docker guide provides comprehensive coverage for containerizing and deploying the RSS Bot platform across different environments and use cases.
