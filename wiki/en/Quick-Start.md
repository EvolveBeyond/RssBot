# ⚡ Quick Start Guide

Get RssBot Platform running in under 5 minutes for testing and development.

## 🎯 Goal

This guide helps you:
- ✅ **Quickly test** the platform capabilities
- ✅ **Skip complex configuration** for initial exploration
- ✅ **See core features** in action
- ✅ **Validate installation** success

## 🚀 5-Minute Setup

### Prerequisites
- Python 3.11+
- Git
- 5 minutes of your time

### Step 1: Clone and Install (2 minutes)

```bash
# Clone repository
git clone https://github.com/your-org/rssbot.git
cd rssbot

# Quick install with Rye (recommended)
curl -sSf https://rye.astral.sh/get | bash && source ~/.bashrc
rye sync

# Alternative: Use pip
python -m venv venv && source venv/bin/activate && pip install -r requirements.lock
```

### Step 2: Start Platform (1 minute)

```bash
# Start with default settings (SQLite + in-memory cache)
python -m rssbot
```

**✅ Success!** Platform is running at `http://localhost:8004`

### Step 3: Verify Installation (1 minute)

```bash
# Check platform health
curl http://localhost:8004/health

# Expected response:
{
  "status": "healthy",
  "architecture": "per_service_core_controller",
  "services_count": 6,
  "timestamp": "2024-01-XX..."
}
```

### Step 4: Explore Services (1 minute)

```bash
# List all services
curl http://localhost:8004/services

# Configure a service (example)
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
  -H "Content-Type: application/json" \
  -d '{"connection_method": "router"}'
```

## 🎮 Interactive Demo

### Test Service Discovery Performance

```bash
# Cold start (first call)
time curl http://localhost:8004/services

# Warm cache (subsequent calls - should be much faster)
time curl http://localhost:8004/services
time curl http://localhost:8004/services
```

### Test Connection Method Switching

```bash
# Set AI service to router mode
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
  -d '{"connection_method": "router"}'

# Verify the change
curl http://localhost:8004/services/ai_svc/status

# Switch to REST mode
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
  -d '{"connection_method": "rest"}'

# See the difference in response
curl http://localhost:8004/services/ai_svc/status
```

### Test Zero-Downtime Configuration

```bash
# Platform should stay responsive during reconfig
curl http://localhost:8004/health &
curl -X POST http://localhost:8004/services/bot_svc/connection-method \
  -d '{"connection_method": "hybrid"}' &
curl http://localhost:8004/health
```

## 🔧 Quick Configuration

### Minimal .env for Testing

Create a `.env` file with just the essentials:

```env
# Basic settings for quick testing
ENVIRONMENT=development
LOG_LEVEL=INFO
CONTROLLER_SERVICE_PORT=8004

# Optional: Add your bot token to test Telegram integration
# TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### Enable Redis for Better Performance (Optional)

```bash
# Install and start Redis (Ubuntu/Debian)
sudo apt install redis-server
sudo systemctl start redis

# Or macOS with Homebrew
brew install redis && brew services start redis

# Add to .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env

# Restart platform to use Redis
python -m rssbot
```

## 🧪 Feature Demo

### 1. Service Discovery Demo

```bash
# Watch service registration in real-time
curl http://localhost:8004/admin/discovery/events

# Force refresh service registry
curl -X POST http://localhost:8004/admin/discovery/refresh

# Check registry cache status
curl http://localhost:8004/admin/cache/stats
```

### 2. Health Monitoring Demo

```bash
# Overall platform health
curl http://localhost:8004/health

# Individual service health
curl http://localhost:8004/services/db_svc/health
curl http://localhost:8004/services/bot_svc/health

# Health summary
curl http://localhost:8004/admin/health/summary
```

### 3. Performance Metrics Demo

```bash
# Platform performance metrics
curl http://localhost:8004/admin/metrics

# Service call statistics
curl http://localhost:8004/admin/stats/calls

# Cache hit/miss ratios
curl http://localhost:8004/admin/stats/cache
```

## 📊 Expected Performance

After setup, you should see:

| Metric                | Expected Value | Indicates              |
|-----------------------|----------------|------------------------|
| **Startup Time**      | < 5 seconds    | Fast platform boot     |
| **Health Check**      | < 100ms        | Responsive APIs        |
| **Service Discovery** | < 1ms (cached) | Redis performance      |
| **Service Switch**    | < 50ms         | Zero-downtime config   |
| **Memory Usage**      | < 100MB        | Efficient resource use |

## 🎯 Test Scenarios

### Scenario 1: Basic Platform Test
```bash
# 1. Start platform
python -m rssbot

# 2. Test health
curl http://localhost:8004/health

# 3. List services
curl http://localhost:8004/services

# ✅ Success: Platform is functional
```

### Scenario 2: Service Configuration Test
```bash
# 1. Check current service status
curl http://localhost:8004/services/ai_svc/status

# 2. Change connection method
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
  -d '{"connection_method": "hybrid"}'

# 3. Verify change took effect
curl http://localhost:8004/services/ai_svc/status

# ✅ Success: Zero-downtime configuration works
```

### Scenario 3: Performance Test
```bash
# 1. Cold start timing
time curl http://localhost:8004/services >/dev/null

# 2. Warm cache timing (should be much faster)
time curl http://localhost:8004/services >/dev/null
time curl http://localhost:8004/services >/dev/null

# ✅ Success: Caching provides performance boost
```

## 🚨 Quick Troubleshooting

### Platform Won't Start

```bash
# Check Python version
python --version  # Should be 3.11+

# Check for port conflicts
lsof -i :8004

# Try alternative port
CONTROLLER_SERVICE_PORT=8005 python -m rssbot
```

### Slow Performance

```bash
# Install Redis for caching
sudo apt install redis-server  # Ubuntu
brew install redis             # macOS

# Enable Redis in environment
echo "REDIS_URL=redis://localhost:6379/0" >> .env
```

### Import/Dependency Errors

```bash
# Reinstall dependencies
rye sync --force

# Or with pip
pip install -r requirements.lock --upgrade
```

### Service Health Issues

```bash
# Check individual service logs
curl http://localhost:8004/admin/logs/db_svc

# Reset service registry
curl -X POST http://localhost:8004/admin/discovery/reset

# Restart platform
# Ctrl+C and then: python -m rssbot
```

## 🎯 Success Criteria

You've successfully completed the quick start if:

- ✅ Platform starts without errors
- ✅ Health check returns `"status": "healthy"`
- ✅ Services list shows all 6+ services
- ✅ Connection method changes work
- ✅ Performance is responsive (< 100ms for health checks)

## 🎉 What's Next?

After this quick start:

### Immediate Next Steps
1. **🤖 [Create Your First Bot](First-Bot)** - Build a working RSS bot
2. **⚙️ [Configure Environment](Configuration)** - Set up databases and APIs
3. **🏗️ [Learn Architecture](Architecture)** - Understand the system design

### For Production Use
1. **🚀 [Production Deployment](Production)** - Scale and secure your platform
2. **🐳 [Docker Setup](Docker)** - Containerize your deployment
3. **📊 [Monitoring Setup](Monitoring)** - Add observability

### For Development
1. **👨‍💻 [Development Guide](Development)** - Contribute to the platform
2. **🧪 [Testing Guide](Testing)** - Run and write tests
3. **📚 [API Reference](API)** - Explore all endpoints

## 💡 Pro Tips

### Development Workflow
```bash
# Use auto-reload for development
uvicorn rssbot.core.controller:create_platform_app --reload

# Enable debug logging
LOG_LEVEL=DEBUG python -m rssbot

# Use hybrid mode for best of both worlds
curl -X POST http://localhost:8004/services/*/connection-method \
  -d '{"connection_method": "hybrid"}'
```

### Performance Optimization
```bash
# Enable Redis caching
REDIS_URL=redis://localhost:6379/0

# Reduce discovery interval for development
SERVICE_DISCOVERY_INTERVAL=10

# Use router mode for core services
# (set via API or config)
```

### Monitoring and Debugging
```bash
# Watch live logs
tail -f logs/*.log

# Monitor performance
watch 'curl -s http://localhost:8004/admin/stats'

# Check memory usage
ps aux | grep python
```

---

**🚀 Congratulations! You now have RssBot Platform running. Time to build something amazing!**
