# ⚙️ Configuration Guide

Complete configuration reference for RssBot Platform environment variables, service settings, and deployment options.

## 📋 Configuration Overview

RssBot Platform uses a **hierarchical configuration system** with the following priority order:

1. **Environment Variables** (highest priority)

2. **`.env` File**

3. **Code Defaults** (lowest priority)

## 🔧 Environment Variables Reference

### Core Platform Settings

```env
# ===========================================
# 🏗️ Core Platform Configuration
# ===========================================

# Runtime environment
ENVIRONMENT=development
# Options: development, production, testing

# Logging configuration
LOG_LEVEL=INFO
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Controller service settings
CONTROLLER_SERVICE_PORT=8004
HOST=0.0.0.0

# Platform security
SERVICE_TOKEN=your_secure_service_token_here
# CRITICAL: Change in production!

# Service discovery settings
SERVICE_DISCOVERY_INTERVAL=45
# Seconds between service health checks

LOCAL_ROUTER_MODE=false
# Enable for development (bypasses service discovery)
```

### Database Configuration

```env
# ===========================================
# 🗄️ Database Configuration
# ===========================================

# Primary database connection
DATABASE_URL=postgresql://user:password@host:5432/database
# Examples:
# PostgreSQL: postgresql://rssbot:secure_pass@localhost:5432/rssbot_db
# SQLite: sqlite:///./rssbot.db

# Database pool settings
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DB_POOL_TIMEOUT=30

# Database SSL (production)
DB_SSL_MODE=prefer
# Options: disable, allow, prefer, require

# Connection retry settings
DB_RETRY_ATTEMPTS=3
DB_RETRY_DELAY=5
```

### Redis Cache Configuration

```env
# ===========================================
# ⚡ Redis Cache Configuration
# ===========================================

# Redis connection
REDIS_URL=redis://localhost:6379/0
# With auth: redis://:password@host:6379/0
# With SSL: rediss://host:6379/0

# Redis connection pool
REDIS_MAX_CONNECTIONS=20
REDIS_RETRY_ON_TIMEOUT=true
REDIS_SOCKET_KEEPALIVE=true

# Cache settings
CACHE_TTL=300
# Default TTL in seconds (5 minutes)

CACHE_MAX_SIZE=1000
# Maximum number of cached items

CACHE_COMPRESSION=true
# Enable data compression for cache
```

### Service Port Configuration

```env
# ===========================================
# 📡 Service Port Configuration
# ===========================================

# Core services
DB_SERVICE_PORT=8001
BOT_SERVICE_PORT=8002
AI_SERVICE_PORT=8003
CONTROLLER_SERVICE_PORT=8004

# Additional services
FORMATTING_SERVICE_PORT=8005
USER_SERVICE_PORT=8006
PAYMENT_SERVICE_PORT=8007
CHANNEL_MGR_SERVICE_PORT=8008
MINIAPP_SERVICE_PORT=8009
ADMIN_SERVICE_PORT=8010

# Port range for auto-assignment
SERVICE_PORT_RANGE_START=8001
SERVICE_PORT_RANGE_END=8099
```

### Telegram Bot Configuration

```env
# ===========================================
# 🤖 Telegram Bot Configuration
# ===========================================

# Bot token from @BotFather
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234567890-123456789012345

# Webhook settings (production)
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_token
TELEGRAM_WEBHOOK_MODE=false
# Set to true for webhook mode, false for polling

# Bot behavior
TELEGRAM_PARSE_MODE=HTML
# Options: HTML, Markdown, MarkdownV2

TELEGRAM_DISABLE_WEB_PAGE_PREVIEW=true
TELEGRAM_PROTECT_CONTENT=false

# Rate limiting
TELEGRAM_RATE_LIMIT=30
# Messages per minute per user
```

### AI Service Configuration

```env
# ===========================================
# 🧠 AI Service Configuration
# ===========================================

# OpenAI settings
OPENAI_API_KEY=sk-your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
# Options: gpt-3.5-turbo, gpt-4, gpt-4-turbo

OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7
OPENAI_TIMEOUT=30

# AI features
AI_SUMMARIZATION_ENABLED=true
AI_TRANSLATION_ENABLED=true
AI_CONTENT_ENHANCEMENT=true

# AI rate limiting
AI_REQUESTS_PER_MINUTE=60
AI_MAX_CONCURRENT_REQUESTS=10
```

### Payment Service Configuration

```env
# ===========================================
# 💳 Payment Service Configuration
# ===========================================

# Stripe settings
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret

# Pricing configuration
STRIPE_PRICE_ID_BASIC=price_basic_plan_id
STRIPE_PRICE_ID_PREMIUM=price_premium_plan_id

# Payment features
PAYMENTS_ENABLED=false
# Enable payment processing

FREE_TIER_FEED_LIMIT=5
PREMIUM_FEED_LIMIT=100
```

### Security Configuration

```env
# ===========================================
# 🔒 Security Configuration
# ===========================================

# JWT settings
JWT_SECRET_KEY=your_super_secret_jwt_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# API security
API_KEY_HEADER=X-API-Key
ADMIN_API_KEY=your_secure_admin_api_key

# Rate limiting
API_RATE_LIMIT=1000
# Requests per hour per IP

API_BURST_LIMIT=100
# Burst requests per minute

# CORS settings
CORS_ALLOWED_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]
CORS_ALLOW_CREDENTIALS=true

# Security headers
SECURITY_HEADERS_ENABLED=true
HSTS_MAX_AGE=31536000
```

### Monitoring & Observability

```env
# ===========================================
# 📊 Monitoring Configuration
# ===========================================

# Health checks
HEALTH_CHECK_INTERVAL=30
# Seconds between health checks

HEALTH_CHECK_TIMEOUT=5
# Timeout for individual health checks

HEALTH_CHECK_RETRIES=3
# Retry attempts for failed checks

# Metrics
ENABLE_METRICS=true
METRICS_PORT=9090
METRICS_PATH=/metrics

# Logging
LOG_FORMAT=json
# Options: json, text

LOG_FILE=logs/rssbot.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5

# Performance monitoring
PERFORMANCE_MONITORING=true
SLOW_QUERY_THRESHOLD=1000
# Milliseconds
```

## 🏗️ Service-Specific Configuration

### Connection Method Configuration

Each service can independently choose its connection method:

```bash
# Set via API
curl -X POST http://localhost:8004/services/{service_name}/connection-method \
  -H "Content-Type: application/json" \
  -d '{"connection_method": "router"}'

# Available methods:
# - router: Direct function calls (fastest)

# - rest: HTTP API calls (most scalable)

# - hybrid: Intelligent switching (best of both)
# - disabled: Service disabled
```

### Default Connection Methods

```env
# Set default connection methods for services
DEFAULT_CONNECTION_METHOD=router

# Service-specific defaults
DB_CONNECTION_METHOD=router
BOT_CONNECTION_METHOD=rest
AI_CONNECTION_METHOD=hybrid
FORMATTING_CONNECTION_METHOD=router
USER_CONNECTION_METHOD=rest
PAYMENT_CONNECTION_METHOD=rest
```

### Service Discovery Configuration

```env
# Service registry settings
AUTO_SERVICE_REGISTRATION=true
SERVICE_HEARTBEAT_INTERVAL=30
SERVICE_TIMEOUT=60

# Health check configuration
HEALTH_CHECK_ENDPOINT=/health
HEALTH_CHECK_EXPECTED_STATUS=200
HEALTH_CHECK_EXPECTED_RESPONSE={"status": "healthy"}

# Load balancing
LOAD_BALANCING_ALGORITHM=weighted_round_robin
# Options: round_robin, weighted_round_robin, least_connections

LOAD_BALANCING_WEIGHTS_AUTO=true
```

## 🐳 Docker Configuration

### Docker Environment Variables

```env
# Container-specific settings
DOCKER_NETWORK=rssbot_network
DOCKER_COMPOSE_PROJECT_NAME=rssbot

# Volume mounts
DATA_VOLUME_PATH=/app/data
LOGS_VOLUME_PATH=/app/logs
CONFIG_VOLUME_PATH=/app/config

# Container resources
CONTAINER_MEMORY_LIMIT=512m
CONTAINER_CPU_LIMIT=0.5
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  rssbot:
    build: .
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://rssbot:${DB_PASSWORD}@postgres:5432/rssbot_db
      - REDIS_URL=redis://redis:6379/0
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    ports:
      - "8004:8004"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

## ☸️ Kubernetes Configuration

### ConfigMap Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rssbot-config
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  CONTROLLER_SERVICE_PORT: "8004"
  SERVICE_DISCOVERY_INTERVAL: "45"
  HEALTH_CHECK_INTERVAL: "30"
  CACHE_TTL: "300"
---
apiVersion: v1
kind: Secret
metadata:
  name: rssbot-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:password@postgres:5432/rssbot"
  TELEGRAM_BOT_TOKEN: "your_bot_token_here"
  SERVICE_TOKEN: "your_secure_service_token"
  JWT_SECRET_KEY: "your_jwt_secret_key"
```

## 🏭 Production Configuration

### Production Environment Template

```env
# ===========================================
# 🏭 Production Configuration
# ===========================================

ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security - MUST CHANGE THESE!
SERVICE_TOKEN=random_generated_secure_token_here
JWT_SECRET_KEY=another_random_generated_secure_key
ADMIN_API_KEY=secure_admin_key_here

# Database - Production PostgreSQL
DATABASE_URL=postgresql://rssbot_prod:secure_password@prod-db:5432/rssbot_prod
DB_SSL_MODE=require

# Redis - Production cluster
REDIS_URL=redis://prod-redis-cluster:6379/0

# External APIs
TELEGRAM_BOT_TOKEN=production_bot_token
TELEGRAM_WEBHOOK_MODE=true
TELEGRAM_WEBHOOK_URL=https://api.yourdomain.com/webhook

OPENAI_API_KEY=production_openai_key
STRIPE_SECRET_KEY=sk_live_your_live_stripe_key

# Performance
SERVICE_DISCOVERY_INTERVAL=60
HEALTH_CHECK_INTERVAL=45
CACHE_TTL=600

# Security
API_RATE_LIMIT=5000
CORS_ALLOWED_ORIGINS=["https://yourdomain.com"]
SECURITY_HEADERS_ENABLED=true

# Monitoring
ENABLE_METRICS=true
PERFORMANCE_MONITORING=true
```

### Production Security Checklist

- ✅ Change all default secrets and tokens
- ✅ Enable SSL/TLS for database connections
- ✅ Use webhook mode for Telegram bot
- ✅ Enable security headers
- ✅ Configure proper CORS origins
- ✅ Set up monitoring and alerting
- ✅ Use production-grade database
- ✅ Enable Redis persistence
- ✅ Configure backup strategies

## 🔧 Configuration Validation

### Automatic Validation

RssBot Platform automatically validates critical configuration:

```python
# Configuration validation on startup
class ConfigValidator:
    def validate_production_config(self, config: Config):
        errors = []
        if config.is_production():
            if config.service_token == "dev_service_token_change_in_production":
                errors.append("SERVICE_TOKEN must be changed in production")

            if not config.database_url.startswith("postgresql://"):
                errors.append("Production should use PostgreSQL")

            if not config.telegram_webhook_mode:
                errors.append("Production should use webhook mode")


        if errors:
            raise ConfigurationError("\n".join(errors))
```

### Configuration Testing

```bash
# Test configuration
python -m rssbot --validate-config

# Test specific service configuration
curl http://localhost:8004/admin/config/validate

# Test database connection
curl http://localhost:8004/admin/config/test-database

# Test Redis connection

curl http://localhost:8004/admin/config/test-redis
```

## 📱 Configuration Management

### Dynamic Configuration Updates

```bash
# Update service configuration without restart
curl -X POST http://localhost:8004/admin/config/reload

# Update specific service settings
curl -X POST http://localhost:8004/services/ai_svc/config \
  -H "Content-Type: application/json" \
  -d '{"max_tokens": 1500, "temperature": 0.8}'

# View current configuration
curl http://localhost:8004/admin/config/current
```

### Configuration Backup

```bash
# Export current configuration
curl http://localhost:8004/admin/config/export > config_backup.json

# Import configuration
curl -X POST http://localhost:8004/admin/config/import \
  -H "Content-Type: application/json" \
  -d @config_backup.json
```

---

**⚙️ Proper configuration is crucial for optimal RssBot Platform performance, security, and reliability. Follow this guide for production-ready deployments.**