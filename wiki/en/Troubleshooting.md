# 🚨 Troubleshooting Guide

Common issues and solutions for RssBot Platform deployment, configuration, and operation.

## 📋 Quick Diagnosis

### Platform Health Check

```bash
# Check overall platform status
curl http://localhost:8004/health

# Expected healthy response:
{
  "status": "healthy",
  "architecture": "per_service_core_controller",
  "services_count": 6,
  "database_status": "connected",
  "cache_status": "connected"
}
```

### Service Status Check

```bash
# Check individual services
curl http://localhost:8004/services

# Check specific service
curl http://localhost:8004/services/db_svc/status
```

## 🚀 Installation & Startup Issues

### Platform Won't Start

**Symptoms:**
- `python -m rssbot` fails
- Import errors
- Port binding errors

**Solutions:**

#### Python Version Issues
```bash
# Check Python version (should be 3.11+)
python --version

# If wrong version:
# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv

# macOS  
brew install python@3.11
```

#### Port Already in Use
```bash
# Find what's using port 8004
lsof -i :8004
ss -tlnp | grep :8004

# Kill the process
kill -9 <PID>

# Or use different port
export CONTROLLER_SERVICE_PORT=8005
python -m rssbot
```

#### Missing Dependencies
```bash
# Reinstall dependencies
rye sync --force

# Or with pip
pip install -r requirements.lock --force-reinstall

# Check for conflicting packages
pip check
```

### Import/Module Errors

**Error:** `ModuleNotFoundError: No module named 'rssbot'`

**Solutions:**
```bash
# Ensure you're in project root
pwd  # Should be .../RssBot

# Install in development mode
pip install -e .

# Or use rye
rye sync

# Check Python path
python -c "import sys; print(sys.path)"
```

**Error:** `ImportError: cannot import name 'BaseSettings'`

**Solutions:**
```bash
# Update pydantic-settings
pip install --upgrade pydantic-settings

# Or downgrade pydantic if needed
pip install pydantic==2.5.0
```