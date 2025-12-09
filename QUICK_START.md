# RSS Bot - Quick Start Guide

## 🚀 **Get Running in 5 Minutes**

This guide gets you up and running with the RSS Bot platform quickly on any system.

---

## **Prerequisites** ✅

You need:
- **Python 3.11+** (check with `python3 --version`)
- **Git** (check with `git --version`) 
- **Internet connection** (for package installation)

---

## **Step 1: Dependencies**

Install required Python packages:

```bash
# Core dependencies
pip3 install --user sqlmodel fastapi uvicorn httpx pydantic

# RSS and web scraping
pip3 install --user feedparser beautifulsoup4 requests

# Telegram bot
pip3 install --user aiogram

# Optional: Database (if using PostgreSQL)
# pip3 install --user psycopg2-binary

# Optional: Redis (for background jobs)  
# pip3 install --user redis
```

---

## **Step 2: Configure Environment**

```bash
cd /mnt/HDD/Documents/Project/python/RssBot

# Copy configuration template
cp .env.example .env

# Edit configuration (minimal required)
nano .env
# OR
vim .env
```

**Minimal `.env` configuration:**
```bash
DATABASE_URL=sqlite:///./rssbot.db
LOCAL_ROUTER_MODE=true
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
SERVICE_TOKEN=dev_service_token_change_in_production
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

**Get Telegram Bot Token:**
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow instructions to create bot
4. Copy token to `.env` file

---

## **Step 3: Test Installation**

```bash
# Test basic functionality
python3 -c "
import sys
sys.path.append('services/db_svc')
from db.models import normalize_feed_url
print('✅ RSS Bot models working!')
print('Normalized URL:', normalize_feed_url('HTTPS://EXAMPLE.COM/feed.xml'))
"
```

---

## **Step 4: Start Platform**

### **Option A: Single Process (Recommended for Development)**

```bash
# Start all services in one process (fast and simple)
cd services/controller_svc
LOCAL_ROUTER_MODE=true python3 main.py
```

### **Option B: Individual Services (Traditional Microservices)**

```bash
# Terminal 1: Database Service
cd services/db_svc && python3 main.py

# Terminal 2: Controller Service  
cd services/controller_svc && python3 main.py

# Terminal 3: Bot Service (optional)
cd services/bot_svc && python3 main.py
```

---

## **Step 5: Verify It's Working**

### **Check Service Health:**
```bash
curl http://localhost:8004/health
# Expected: {"status":"healthy","service":"controller_svc",...}
```

### **View API Documentation:**
Open in browser: http://localhost:8004/docs

### **Test Database:**
```bash
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8004/db/tables
# Expected: {"tables":{},"models":[...],"count":0}
```

### **Test Feed Deduplication:**
```bash
# Add same feed twice to different channels - should create 1 canonical feed
curl -X POST "http://localhost:8004/db/feed-assignment" \
  -H "X-Service-Token: dev_service_token_change_in_production" \
  -H "Content-Type: application/json" \
  -d '{
    "feed_url": "https://example.com/feed.xml",
    "channel_id": 1,
    "assigned_by_user_id": 1
  }'
```

---

## **Step 6: Explore Features**

### **Available Endpoints:**
- **Dashboard**: http://localhost:8004/ (if miniapp service running)
- **API Docs**: http://localhost:8004/docs
- **Database API**: http://localhost:8004/db/*
- **User API**: http://localhost:8004/users/* (if in router mode)

### **Test Deduplication:**
```bash
# Run comprehensive tests
python3 services/db_svc/scripts/validate_schema.py

# Test URL normalization
python3 services/db_svc/scripts/run_tests.py
```

### **Migration System:**
```bash
# Preview what migration would do (safe)
./scripts/migrate_dedup.sh --dry-run

# Apply new schema (if you have existing data)
./scripts/migrate_dedup.sh --apply
```

---

## **🎯 Common Issues & Solutions**

### **"Module not found" Error**
```bash
# Install missing package
pip3 install --user PACKAGE_NAME

# Or install all at once:
pip3 install --user sqlmodel fastapi uvicorn httpx aiogram feedparser beautifulsoup4
```

### **"Permission denied" on Scripts**
```bash
chmod +x scripts/*.sh
chmod +x services/*/scripts/*.py
```

### **"Port already in use"**
```bash
# Check what's using port 8004
sudo lsof -i :8004
# Kill process or change port in .env
```

### **Database Issues**
```bash
# Reset database (removes all data)
rm -f rssbot.db
rm -f services/db_svc/rssbot.db

# Or use PostgreSQL instead of SQLite:
# DATABASE_URL=postgresql://user:pass@localhost:5432/rssbot
```

---

## **🚀 Next Steps**

Once running:

1. **Add RSS Feeds**: Use the `/db/feed-assignment` endpoint
2. **Configure Styling**: Create styles via the Style API
3. **Set Up Telegram Bot**: Test with your bot token  
4. **Explore Documentation**: See `docs/` directory for detailed guides
5. **Deploy to Production**: See `DEPLOYMENT_CHECKLIST.md`

---

## **🆘 Need Help?**

- **Documentation**: Check `docs/` directory
- **API Reference**: Visit http://localhost:8004/docs when running
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Production**: See `docs/PRODUCTION.md`
- **Issues**: Create GitHub issue with error details

---

**🎉 You're now running the RSS Bot platform with canonical feed deduplication!**

The platform will automatically:
- ✅ Deduplicate RSS feeds across users/channels
- ✅ Apply per-channel styling 
- ✅ Track usage for billing
- ✅ Handle content deduplication
- ✅ Provide comprehensive APIs

Start adding feeds and exploring the features! 🚀