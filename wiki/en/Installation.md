# 📦 Installation Guide

Complete setup instructions for the RssBot Platform across different environments.

## 📋 System Requirements

### Minimum Requirements
- **Python**: 3.11 or higher
- **RAM**: 2GB minimum (4GB recommended)
- **Storage**: 1GB free space
- **Network**: Internet access for external APIs

### Recommended Software
- **Package Manager**: [Rye](https://rye.astral.sh/) (preferred) or pip
- **Database**: PostgreSQL 12+ or Redis 5+
- **Containerization**: Docker 20+ and Docker Compose
- **Version Control**: Git 2.30+

## 🚀 Installation Methods

Choose your preferred installation method:

### Method 1: Quick Install with Rye (Recommended)

```bash
# 1. Install Rye if not already installed
curl -sSf https://rye.astral.sh/get | bash
source ~/.bashrc  # or restart your terminal

# 2. Clone the repository
git clone https://github.com/your-org/rssbot.git
cd rssbot

# 3. Install all dependencies
rye sync

# 4. Copy environment template
cp .env.example .env

# 5. Start the platform
python -m rssbot
```

### Method 2: Traditional pip Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/rssbot.git
cd rssbot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.lock

# 4. Copy environment template
cp .env.example .env

# 5. Start the platform
python -m rssbot
```

### Method 3: Docker Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/rssbot.git
cd rssbot

# 2. Copy and configure environment
cp .env.example .env
# Edit .env as needed

# 3. Start with Docker Compose
docker-compose up -d

# 4. Check status
docker-compose ps
```

## ⚙️ Environment Configuration

### Required Environment Variables

Edit your `.env` file with these essential settings:

```env
# ===========================================
# 🏗️ Core Platform Settings
# ===========================================

# Environment (development, production, testing)
ENVIRONMENT=development

# Logging level
LOG_LEVEL=INFO

# Platform controller settings
CONTROLLER_SERVICE_PORT=8004
SERVICE_TOKEN=your_secure_service_token_here

# ===========================================
# 🗄️ Database Configuration
# ===========================================

# Primary database (choose one)
DATABASE_URL=postgresql://user:password@localhost:5432/rssbot
# Or for local development:
# DATABASE_URL=sqlite:///./rssbot.db

# Redis cache
REDIS_URL=redis://localhost:6379/0

# ===========================================
# 🤖 Telegram Bot Configuration
# ===========================================

# Get from @BotFather
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234567890-1234567890123456

# Webhook settings (optional)
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret

# ===========================================
# 🧠 External API Keys (Optional)
# ===========================================

# OpenAI for AI features
OPENAI_API_KEY=sk-your_openai_key_here

# Stripe for payments
STRIPE_SECRET_KEY=sk_test_your_stripe_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

### Optional Environment Variables

```env
# Service-specific ports (auto-assigned if not set)
DB_SERVICE_PORT=8001
BOT_SERVICE_PORT=8002
AI_SERVICE_PORT=8003
FORMATTING_SERVICE_PORT=8005
USER_SERVICE_PORT=8006
PAYMENT_SERVICE_PORT=8007

# Performance tuning
SERVICE_DISCOVERY_INTERVAL=45
LOCAL_ROUTER_MODE=false

# Security
JWT_SECRET_KEY=your_jwt_secret_key
API_RATE_LIMIT=1000

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

## 🗄️ Database Setup

### Option 1: SQLite (Development)

SQLite works out of the box with no additional setup:

```env
DATABASE_URL=sqlite:///./rssbot.db
```

### Option 2: PostgreSQL (Recommended for Production)

#### Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)

#### Create Database and User

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE USER rssbot WITH PASSWORD 'secure_password';
CREATE DATABASE rssbot_db OWNER rssbot;
GRANT ALL PRIVILEGES ON DATABASE rssbot_db TO rssbot;
\q
```

#### Update Environment

```env
DATABASE_URL=postgresql://rssbot:secure_password@localhost:5432/rssbot_db
```

### Option 3: Redis Set-up (Optional but Recommended)

Redis provides significant performance improvements for service discovery.

#### Install Redis

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
```bash
# Using WSL or download Windows port
```

#### Test Redis Connection

```bash
redis-cli ping
# Should return: PONG
```

#### Update Environment

```env
REDIS_URL=redis://localhost:6379/0
```

## 🤖 Telegram Bot Setup

### Create a New Bot

1. **Message @BotFather** on Telegram
2. **Send `/newbot`** command
3. **Choose a name** for your bot (e.g., "My RSS Bot")
4. **Choose a username** ending in "bot" (e.g., "myrssbot")
5. **Copy the token** provided by BotFather

### Configure Bot Token

```env
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234567890-1234567890123456
```

### Optional: Set Bot Commands

```bash
# Message @BotFather again
/setcommands

# Select your bot and set these commands:
start - Start the bot
help - Get help information
subscribe - Subscribe to RSS feeds
unsubscribe - Unsubscribe from feeds
list - List your subscriptions
settings - Manage your settings
```

## ✅ Verification Steps

### 1. Check Platform Health

```bash
curl http://localhost:8004/health

# Expected response:
{
  "status": "healthy",
  "architecture": "per_service_core_controller",
  "services_count": 6,
  "database_status": "connected",
  "cache_status": "connected"
}
```

### 2. Verify Service Registry

```bash
curl http://localhost:8004/services

# Should show list of available services with their status
```

### 3. Test Database Connection

```bash
curl http://localhost:8004/services/db_svc/health

# Expected response:
{
  "status": "healthy",
  "connection": "active",
  "tables_count": 5
}
```

### 4. Test Telegram Bot

Start a conversation with your bot and send `/start`. You should receive a welcome message.

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find what's using the port
lsof -i :8004

# Kill the process
kill -9 <PID>

# Or use a different port
export CONTROLLER_SERVICE_PORT=8005
```

#### Python Version Issues
```bash
# Check Python version
python --version  # Should be 3.11+

# If using older version, install Python 3.11+
# Ubuntu/Debian:
sudo apt install python3.11 python3.11-venv

# macOS:
brew install python@3.11
```

#### Database Connection Issues
```bash
# Test PostgreSQL connection
pg_isready -h localhost -p 5432

# Test Redis connection
redis-cli ping

# Check if services are running
systemctl status postgresql
systemctl status redis-server
```

#### Rye Installation Issues
```bash
# Manual Rye installation
curl -sSf https://rye.astral.sh/get | bash
echo 'source "$HOME/.rye/env"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
rye --version
```

#### Import Errors
```bash
# Reinstall dependencies
rye sync --force

# Or with pip
pip install -r requirements.lock --force-reinstall
```

### Platform-Specific Issues

#### Windows
- Use PowerShell or WSL for better compatibility
- Replace `source` with `venv\Scripts\activate`
- Use Windows paths for SQLite: `sqlite:///C:/path/to/rssbot.db`

#### macOS
- Install Xcode Command Line Tools: `xcode-select --install`
- Use Homebrew for package management
- May need to install additional certificates for HTTPS

#### Linux
- Ensure Python development headers: `sudo apt install python3-dev`
- Install build essentials: `sudo apt install build-essential`
- Check firewall settings for port access

### Performance Issues

#### Slow Startup
```bash
# Enable Redis for faster service discovery
REDIS_URL=redis://localhost:6379/0

# Use local router mode for development
LOCAL_ROUTER_MODE=true
```

#### Memory Issues
```bash
# Reduce service discovery interval
SERVICE_DISCOVERY_INTERVAL=60

# Use SQLite for development
DATABASE_URL=sqlite:///./rssbot.db
```

## 🎯 Next Steps

After successful installation:

1. **📖 Read the [Quick Start Guide](Quick-Start)** - Get your first bot running
2. **⚙️ Review [Configuration](Configuration)** - Understand all settings
3. **🏗️ Learn about [Architecture](Architecture)** - Understand the system design
4. **🤖 Create [Your First Bot](First-Bot)** - Build a real RSS bot
5. **🚀 Plan [Production Deployment](Production)** - Scale your platform

## 🆘 Getting Help

If you encounter issues:

- **📚 Check [Troubleshooting Guide](Troubleshooting)** - Common solutions
- **🐛 Search [GitHub Issues](https://github.com/your-org/rssbot/issues)** - Known problems
- **💬 Ask in [Discussions](https://github.com/your-org/rssbot/discussions)** - Community help
- **📧 Contact Support** - For critical issues

---

**🎉 Congratulations! RssBot Platform is now installed and ready to use.**
