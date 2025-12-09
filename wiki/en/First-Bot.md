# 🤖 Create Your First RSS Bot

Step-by-step guide to create and deploy your first RSS bot using RssBot Platform.

## 🎯 What You'll Build

By the end of this guide, you'll have:
- ✅ **A working Telegram bot** that processes RSS feeds
- ✅ **RSS feed subscriptions** for your channels/groups
- ✅ **Automated content delivery** with smart formatting
- ✅ **Basic understanding** of RssBot Platform capabilities

## 📋 Prerequisites

Before starting, ensure you have:
- ✅ **RssBot Platform installed** ([Installation Guide](Installation))
- ✅ **Telegram Bot Token** from @BotFather
- ✅ **Basic understanding** of Telegram bots
- ✅ **10-15 minutes** of time

## 🚀 Step 1: Set Up Your Bot

### Get a Bot Token from @BotFather

1. **Message @BotFather** on Telegram
2. **Send `/newbot`** command
3. **Choose a name** (e.g., "My RSS Reader")
4. **Choose a username** ending in "bot" (e.g., "myrssreaderbot")
5. **Copy the token** you receive

### Configure RssBot Platform

Add your bot token to the `.env` file:

```env
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234567890-123456789012345
```

### Start the Platform

```bash
# Start RssBot Platform
python -m rssbot

# Verify it's running
curl http://localhost:8004/health
```

## 🤖 Step 2: Test Your Bot

### Start a Conversation

1. **Find your bot** on Telegram using the username you created
2. **Send `/start`** to begin
3. **You should receive** a welcome message

### Verify Bot Service

```bash
# Check bot service status
curl http://localhost:8004/services/bot_svc/status

# Should show the service is running and connected
```

## 📡 Step 3: Add Your First RSS Feed

### Using the API

```bash
# Add a popular tech news feed
curl -X POST http://localhost:8004/services/db_svc/feeds \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://feeds.feedburner.com/oreilly",
    "title": "O'\''Reilly Media News",
    "chat_id": YOUR_TELEGRAM_USER_ID,
    "update_interval": 3600
  }'
```

### Get Your Telegram User ID

To find your user ID, you can:

**Method 1: Use @userinfobot**
1. Message @userinfobot on Telegram
2. It will reply with your user ID

**Method 2: Check RssBot logs**
1. Send any message to your bot
2. Check the platform logs for your user ID

**Method 3: Use the API**
```bash
# List recent bot interactions
curl http://localhost:8004/services/bot_svc/recent-users
```

### Using Bot Commands

Alternatively, you can add feeds directly through your bot:

1. **Send** `/subscribe https://feeds.feedburner.com/oreilly` to your bot
2. **Follow the prompts** to configure the feed
3. **Confirm** the subscription

## ⚙️ Step 4: Configure Feed Processing

### Basic Configuration

```bash
# Set update interval to 30 minutes
curl -X PUT http://localhost:8004/services/db_svc/feeds/1 \
  -H "Content-Type: application/json" \
  -d '{
    "update_interval": 1800,
    "active": true
  }'
```

### Enable AI Enhancement (Optional)

```bash
# Configure AI service for content summarization
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
  -H "Content-Type: application/json" \
  -d '{"connection_method": "hybrid"}'

# Enable AI processing for your feed
curl -X PUT http://localhost:8004/services/db_svc/feeds/1 \
  -H "Content-Type: application/json" \
  -d '{
    "ai_processing": true,
    "ai_summary": true,
    "ai_max_length": 200
  }'
```

## 📝 Step 5: Customize Message Formatting

### Default Format

By default, RssBot sends messages in this format:
```
📰 **Article Title**

Summary or first paragraph...

🔗 [Read More](https://example.com/article)
📅 Published: Jan 15, 2024
```

### Custom Format Template

```bash
# Set custom message template
curl -X PUT http://localhost:8004/services/db_svc/feeds/1 \
  -H "Content-Type: application/json" \
  -d '{
    "message_template": "🚀 **{title}**\n\n{summary}\n\n👉 {link}\n🕒 {published_date}"
  }'
```

### Template Variables

Available template variables:
- `{title}` - Article title
- `{summary}` - Article summary or description
- `{link}` - Article URL
- `{published_date}` - Publication date
- `{author}` - Author name (if available)
- `{category}` - Article category (if available)

## 🎯 Step 6: Test Feed Updates

### Manual Feed Update

```bash
# Trigger manual feed update
curl -X POST http://localhost:8004/services/db_svc/feeds/1/update

# Check for new items
curl http://localhost:8004/services/db_svc/feeds/1/items?limit=5
```

### Monitor Feed Processing

```bash
# Watch feed processing in real-time
curl http://localhost:8004/services/db_svc/feeds/1/status

# Check processing logs
curl http://localhost:8004/admin/logs/channel_mgr_svc?limit=20
```

## 📱 Step 7: Advanced Bot Commands

### Set Up Bot Commands

Configure your bot's command menu by messaging @BotFather:

```
/setcommands

# Then send these commands:
start - Start the bot and see welcome message
help - Get help and usage information
subscribe - Subscribe to an RSS feed
unsubscribe - Remove RSS feed subscription
list - List all your subscriptions
settings - Manage your preferences
status - Check feed status and statistics
```

### Implement Custom Commands

Your bot automatically supports these commands:

- `/start` - Welcome message and quick start
- `/help` - Detailed help information
- `/subscribe <url>` - Add new RSS feed
- `/unsubscribe <id>` - Remove RSS feed
- `/list` - Show all subscriptions
- `/settings` - Configure preferences

### Test Commands

Try these commands with your bot:

```
/list
# Should show your O'Reilly Media subscription

/settings
# Opens settings menu with options

/subscribe https://rss.cnn.com/rss/edition.rss
# Adds CNN RSS feed
```

## 🔧 Step 8: Performance Optimization

### Configure Connection Methods

For optimal performance, configure services appropriately:

```bash
# Set database service to router mode (fastest for core operations)
curl -X POST http://localhost:8004/services/db_svc/connection-method \
  -d '{"connection_method": "router"}'

# Set bot service to hybrid mode (balanced performance)
curl -X POST http://localhost:8004/services/bot_svc/connection-method \
  -d '{"connection_method": "hybrid"}'

# Set AI service to REST mode (if using external AI)
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
  -d '{"connection_method": "rest"}'
```

### Enable Redis Caching

For better performance, configure Redis:

```bash
# Install Redis if not already installed
sudo apt install redis-server  # Ubuntu/Debian
brew install redis             # macOS

# Add to .env file
echo "REDIS_URL=redis://localhost:6379/0" >> .env

# Restart platform
python -m rssbot
```

## 📊 Step 9: Monitor Your Bot

### Check Bot Statistics

```bash
# Overall bot statistics
curl http://localhost:8004/services/bot_svc/stats

# Feed performance metrics
curl http://localhost:8004/services/db_svc/feeds/1/metrics

# Platform health
curl http://localhost:8004/health
```

### Monitor Feed Activity

```bash
# Recent feed items
curl http://localhost:8004/services/db_svc/feeds/1/items?limit=10

# Processing statistics
curl http://localhost:8004/admin/stats/feeds

# Error logs (if any)
curl http://localhost:8004/admin/logs/bot_svc?level=ERROR
```

## 🎉 Step 10: Scale and Extend

### Add More Feeds

```bash
# Add multiple feeds at once
curl -X POST http://localhost:8004/services/db_svc/feeds/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "feeds": [
      {
        "url": "https://rss.cnn.com/rss/edition.rss",
        "title": "CNN News",
        "chat_id": YOUR_USER_ID
      },
      {
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "title": "BBC News", 
        "chat_id": YOUR_USER_ID
      }
    ]
  }'
```

### Create Channel Bot

1. **Create a Telegram channel**
2. **Add your bot as admin** with post message permissions
3. **Get channel ID** (starts with -100)
4. **Subscribe channel to feeds**:

```bash
curl -X POST http://localhost:8004/services/db_svc/feeds \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://feeds.feedburner.com/oreilly",
    "title": "Tech News for Channel",
    "chat_id": -1001234567890,
    "update_interval": 1800
  }'
```

### Enable Advanced Features

```bash
# Enable duplicate detection
curl -X PUT http://localhost:8004/services/db_svc/feeds/1 \
  -d '{"duplicate_detection": true}'

# Enable content filtering
curl -X PUT http://localhost:8004/services/db_svc/feeds/1 \
  -d '{"content_filter": ["technology", "programming"]}'

# Enable scheduled posting
curl -X PUT http://localhost:8004/services/db_svc/feeds/1 \
  -d '{"scheduled_posting": true, "posting_hours": [9, 12, 15, 18]}'
```

## 🚨 Common Issues and Solutions

### Bot Not Responding

```bash
# Check bot service health
curl http://localhost:8004/services/bot_svc/health

# Restart bot service if needed
curl -X POST http://localhost:8004/services/bot_svc/restart
```

### Feeds Not Updating

```bash
# Check channel manager service
curl http://localhost:8004/services/channel_mgr_svc/status

# Manually trigger feed processing
curl -X POST http://localhost:8004/admin/feeds/process-all
```

### Permission Errors

- Ensure bot is admin in channels
- Check bot token is valid
- Verify chat IDs are correct

## 🎯 Next Steps

Congratulations! You now have a working RSS bot. Here's what you can do next:

### Immediate Enhancements
1. **📱 [Add More Features](Development)** - Custom commands and handlers
2. **🎨 [Customize Templates](Configuration)** - Advanced message formatting  
3. **🧠 [Enable AI Features](AI-Integration)** - Content enhancement and summarization

### Scaling and Production
1. **🚀 [Production Deployment](Production)** - Deploy for real users
2. **🐳 [Docker Setup](Docker)** - Containerized deployment
3. **📊 [Monitoring Setup](Monitoring)** - Performance tracking

### Advanced Features
1. **💳 [Payment Integration](Payment-Integration)** - Subscription management
2. **👥 [User Management](User-Management)** - Advanced user features
3. **📈 [Analytics](Analytics)** - Usage analytics and insights

---

**🎉 Amazing! You've successfully created your first RSS bot with RssBot Platform. Start exploring the advanced features to make it even more powerful! 🚀**