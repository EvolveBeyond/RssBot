# 🚀 Production Deployment Guide

This comprehensive guide covers deploying the **RssBot Hybrid Microservices Platform** in production environments with enterprise-grade reliability, security, and scalability.

## 🎯 Production Overview

The RssBot Platform is designed for **enterprise production deployments** with:

- **🏗️ Hybrid Architecture**: Per-service connection optimization for performance and scalability
- **⚡ High Performance**: Redis-cached service decisions with sub-millisecond lookups  
- **🔒 Enterprise Security**: Service authentication, input validation, audit logging
- **📊 Comprehensive Monitoring**: Health checks, performance metrics, alerting
- **🔄 Zero-Downtime Deployments**: Live configuration changes without service interruption

## 📋 Pre-Production Checklist

### 🔧 Infrastructure Requirements

#### Minimum Production Requirements
```yaml
# Compute Resources
CPU: 4 cores minimum (8+ recommended)
Memory: 8GB minimum (16GB+ recommended)  
Storage: 50GB minimum (SSD preferred)
Network: 1Gbps minimum

# External Dependencies
PostgreSQL: 13+ (with connection pooling)
Redis: 6+ (with clustering for HA)
Load Balancer: HAProxy, Nginx, or cloud LB
Monitoring: Prometheus + Grafana (recommended)
```

### 🔒 Security Requirements

#### Essential Security Measures
- **Strong Service Tokens**: 64+ character random tokens
- **HTTPS/TLS**: All communications encrypted
- **Database Security**: Connection encryption, restricted access
- **Redis Security**: AUTH enabled, network isolation
- **Firewall Rules**: Restrictive access controls
- **Regular Updates**: OS and dependency patching

## 🐳 Container Deployment

### 📦 Docker Production Setup

#### 1. Production Dockerfile
```dockerfile
# Multi-stage build for optimal production image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r rssbot && useradd -r -g rssbot rssbot

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /root/.local /home/rssbot/.local
ENV PATH="/home/rssbot/.local/bin:$PATH"

# Copy application
WORKDIR /app
COPY src/ ./src/
COPY services/ ./services/
COPY scripts/ ./scripts/

# Set ownership and permissions
RUN chown -R rssbot:rssbot /app
USER rssbot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Use core platform entry point
CMD ["python", "-m", "rssbot"]
```

#### 2. Production Environment
```bash
# === Production Environment ===
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# === Database Configuration ===
DATABASE_URL=postgresql://rssbot:SECURE_PASSWORD@db-host:5432/rssbot
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50

# === Redis Configuration ===
REDIS_URL=redis://:SECURE_PASSWORD@redis-host:6379/0
REDIS_MAX_CONNECTIONS=100

# === Security ===
SERVICE_TOKEN=VERY_SECURE_64_CHAR_TOKEN_CHANGE_THIS_IN_PRODUCTION_12345678

# === External Services ===
TELEGRAM_BOT_TOKEN=1234567890:REAL_PRODUCTION_BOT_TOKEN
OPENAI_API_KEY=sk-REAL_OPENAI_API_KEY_FOR_PRODUCTION
STRIPE_SECRET_KEY=sk_live_REAL_STRIPE_SECRET_KEY
```

## ☸️ Kubernetes Deployment

### 📊 Kubernetes Manifests

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rssbot-platform
  namespace: rssbot
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: rssbot
        image: rssbot-platform:v2.0.0
        ports:
        - containerPort: 8004
        livenessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 30
          periodSeconds: 15
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi" 
            cpu: "1000m"
```

## 🔧 Performance Optimization

### ⚡ Redis Configuration

```redis
# redis.conf for production
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

### 🗄️ PostgreSQL Optimization

```postgresql
# postgresql.conf optimizations
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 64MB
maintenance_work_mem = 512MB
max_connections = 200
```

## 📊 Monitoring & Alerting

### 🎯 Health Monitoring

```bash
# Health check endpoints
GET /health                           # Platform health
GET /services                         # Service status
GET /admin/cache/stats               # Cache performance
GET /metrics                         # Prometheus metrics
```

### 📈 Key Metrics to Monitor

```yaml
# Critical Performance Metrics
- cache_hit_ratio: > 95%
- service_response_time: < 100ms
- error_rate: < 0.1%
- memory_usage: < 80%
- cpu_usage: < 70%

# Business Metrics  
- requests_per_second: Monitor trends
- active_services: All services healthy
- message_processing_rate: RSS throughput
```

## 🔒 Security Hardening

### 🛡️ Network Security

```bash
# Firewall rules (iptables example)
# Allow only necessary ports
iptables -A INPUT -p tcp --dport 8004 -j ACCEPT  # Platform
iptables -A INPUT -p tcp --dport 22 -j ACCEPT    # SSH
iptables -A INPUT -p tcp --dport 443 -j ACCEPT   # HTTPS
iptables -A INPUT -j DROP  # Drop all other traffic
```

### 🔐 Application Security

```python
# Security middleware configuration
SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff", 
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'"
}
```

## 🔄 Deployment Strategies

### 🚀 Zero-Downtime Deployment

```bash
# Rolling deployment strategy
1. Deploy new version to 33% of instances
2. Health check new instances
3. Route traffic gradually to new instances  
4. Deploy to remaining instances
5. Verify all instances healthy
```

### 🔄 Service Configuration Updates

```bash
# Live configuration without restart
curl -X POST http://load-balancer/admin/bulk-connection-methods \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: $PROD_TOKEN" \
     -d '{
       "ai_svc": "router",      # High performance
       "bot_svc": "rest",       # Scalability  
       "payment_svc": "rest"    # Security isolation
     }'
```

## 🚨 Disaster Recovery

### 💾 Backup Strategy

```bash
# Database backups
pg_dump -h $DB_HOST -U rssbot -d rssbot > backup_$(date +%Y%m%d_%H%M%S).sql

# Redis backups  
redis-cli --rdb dump.rdb

# Configuration backups
kubectl get configmaps -o yaml > configmaps_backup.yaml
kubectl get secrets -o yaml > secrets_backup.yaml
```

### 🔄 Recovery Procedures

```bash
# Database recovery
psql -h $DB_HOST -U rssbot -d rssbot < backup_file.sql

# Redis recovery
redis-cli --pipe < dump.rdb

# Service recovery
kubectl apply -f k8s/
kubectl rollout restart deployment/rssbot-platform
```

## 🎯 Production Tuning

### ⚙️ Service-Specific Optimization

```python
# High-performance configuration
ROUTER_SERVICES = [
    "ai_svc",          # AI processing needs speed
    "formatting_svc",  # Content formatting  
    "user_svc"         # User data queries
]

# Scalable configuration
REST_SERVICES = [
    "bot_svc",         # Telegram isolation
    "payment_svc",     # Security requirements
    "channel_mgr_svc"  # RSS feed processing
]

# Apply optimizations
for service in ROUTER_SERVICES:
    await update_service_method(service, "router")
    
for service in REST_SERVICES:
    await update_service_method(service, "rest")
```

### 📊 Load Testing

```bash
# Performance testing with realistic load
# Test service decisions performance
ab -n 10000 -c 100 http://platform:8004/health

# Test API endpoints
ab -n 5000 -c 50 -H "X-Service-Token: $TOKEN" \
   http://platform:8004/services

# Test service configuration changes
ab -n 1000 -c 10 -p config_data.json -T application/json \
   http://platform:8004/services/ai_svc/connection-method
```

## 🔍 Troubleshooting

### 🚨 Common Production Issues

#### 1. High Memory Usage
```bash
# Check Redis memory usage
redis-cli info memory

# Check application memory
kubectl top pods -n rssbot

# Solutions:
- Increase Redis maxmemory
- Scale horizontally
- Optimize cache TTL
```

#### 2. Slow Service Responses
```bash
# Check cache performance  
curl -H "X-Service-Token: $TOKEN" \
     http://platform:8004/admin/cache/stats

# Solutions:
- Check Redis connectivity
- Increase cache TTL
- Scale Redis cluster
```

#### 3. Service Discovery Issues
```bash
# Check service registry
curl -H "X-Service-Token: $TOKEN" \
     http://platform:8004/services

# Solutions:
- Restart platform instances
- Clear cache and rebuild
- Check database connectivity
```

## 📈 Scaling Guidelines

### 🔄 Horizontal Scaling

```yaml
# Kubernetes HPA (Horizontal Pod Autoscaler)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rssbot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rssbot-platform
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### ⚡ Vertical Scaling

```bash
# Scale individual components
# Redis scaling
redis.maxmemory: 8GB
redis.max-connections: 10000

# Database scaling  
postgresql.shared_buffers: 4GB
postgresql.max_connections: 500

# Application scaling
cpu.limits: 4 cores
memory.limits: 8GB
```

## 📚 Production Checklist

### ✅ Pre-Deployment Checklist

- [ ] **Security**: Strong passwords, encrypted connections, firewall rules
- [ ] **Performance**: Redis configured, database optimized, resource limits set
- [ ] **Monitoring**: Health checks, metrics collection, alerting configured  
- [ ] **Backup**: Database backup, Redis backup, configuration backup
- [ ] **Documentation**: Runbooks, incident procedures, contact information

### ✅ Post-Deployment Checklist

- [ ] **Health Verification**: All services healthy and responding
- [ ] **Performance Validation**: Response times within SLA
- [ ] **Security Verification**: All security measures active
- [ ] **Monitoring Activation**: Alerts configured and tested
- [ ] **Documentation Update**: Production configuration documented

---

**The RssBot Platform is now production-ready with enterprise-grade reliability, security, and performance! 🚀✨**