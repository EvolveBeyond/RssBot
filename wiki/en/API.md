# 📚 API Reference

Complete API documentation for RssBot Platform's REST endpoints, service management, and integration capabilities.

## 🎯 API Overview

RssBot Platform provides a comprehensive REST API for:

- **🎛️ Service Management**: Configure connection methods, health monitoring
- **🗄️ Database Operations**: Feed management, user data, analytics
- **🤖 Bot Operations**: Message handling, subscription management
- **🧠 AI Processing**: Content enhancement, summarization
- **💳 Payment Processing**: Subscription management, billing
- **⚙️ Admin Operations**: Platform configuration, monitoring

## 🔗 Base URLs

| Environment     | Base URL                             | Description         |
|-----------------|--------------------------------------|---------------------|
| **Development** | `http://localhost:8004`              | Local development   |
| **Staging**     | `https://staging-api.yourdomain.com` | Staging environment |
| **Production**  | `https://api.yourdomain.com`         | Production API      |

## 🔐 Authentication

### Service Token Authentication

All API requests require a service token in the header:

```bash
curl -H "Authorization: Bearer your_service_token_here" \
     -H "Content-Type: application/json" \
     http://localhost:8004/api/endpoint
```

### Admin API Key

Admin endpoints require an additional API key:

```bash
curl -H "X-API-Key: your_admin_api_key" \
     -H "Authorization: Bearer your_service_token" \
     http://localhost:8004/admin/endpoint
```

## 🎛️ Core Platform APIs

### Health & Status

#### GET /health
Get overall platform health status.

```bash
curl http://localhost:8004/health
```

**Response:**
```json
{
  "status": "healthy",
  "architecture": "per_service_core_controller",
  "services_count": 6,
  "database_status": "connected",
  "cache_status": "connected",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

#### GET /services
List all registered services and their status.

```bash
curl http://localhost:8004/services
```

**Response:**
```json
[
  {
    "name": "db_svc",
    "status": "running",
    "connection_method": "router",
    "health_score": 0.95,
    "last_seen": "2024-01-15T10:29:45Z",
    "port": 8001,
    "url": "http://localhost:8001"
  },
  {
    "name": "ai_svc",
    "status": "running", 
    "connection_method": "hybrid",
    "health_score": 0.88,
    "last_seen": "2024-01-15T10:29:50Z",
    "port": 8003
  }
]
```

### Service Management

#### POST /services/{service_name}/connection-method
Change a service's connection method.

**Request:**
```bash
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
  -H "Content-Type: application/json" \
  -d '{"connection_method": "router"}'
```

**Parameters:**
- `connection_method`: `"router"`, `"rest"`, `"hybrid"`, or `"disabled"`

**Response:**
```json
{
  "service_name": "ai_svc",
  "old_method": "rest",
  "new_method": "router",
  "changed_at": "2024-01-15T10:30:00Z",
  "status": "updated"
}
```

#### GET /services/{service_name}/status
Get detailed status for a specific service.

```bash
curl http://localhost:8004/services/ai_svc/status
```

**Response:**
```json
{
  "name": "ai_svc",
  "status": "running",
  "connection_method": "hybrid",
  "health": {
    "score": 0.88,
    "latency_ms": 45,
    "success_rate": 0.97,
    "last_check": "2024-01-15T10:29:50Z"
  },
  "metrics": {
    "requests_total": 1547,
    "errors_total": 23,
    "avg_response_time_ms": 234
  },
  "configuration": {
    "max_tokens": 1000,
    "model": "gpt-3.5-turbo",
    "temperature": 0.7
  }
}
```

## 🗄️ Database Service APIs

### Feed Management

#### GET /services/db_svc/feeds
List all RSS feeds.

```bash
curl http://localhost:8004/services/db_svc/feeds
```

**Query Parameters:**
- `limit` (optional): Maximum number of feeds to return (default: 50)
- `offset` (optional): Number of feeds to skip (default: 0)
- `active_only` (optional): Only return active feeds (default: false)

**Response:**
```json
{
  "feeds": [
    {
      "id": 1,
      "url": "https://feeds.feedburner.com/oreilly",
      "title": "O'Reilly Media",
      "description": "Technology and business insights",
      "last_updated": "2024-01-15T10:25:00Z",
      "active": true,
      "chat_id": -1001234567890,
      "subscribers_count": 156
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### POST /services/db_svc/feeds
Create a new RSS feed.

**Request:**
```bash
curl -X POST http://localhost:8004/services/db_svc/feeds \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/rss.xml",
    "title": "Example Feed",
    "chat_id": -1001234567890,
    "update_interval": 3600
  }'
```

**Response:**
```json
{
  "id": 2,
  "url": "https://example.com/rss.xml",
  "title": "Example Feed", 
  "chat_id": -1001234567890,
  "update_interval": 3600,
  "active": true,
  "created_at": "2024-01-15T10:35:00Z"
}
```

#### PUT /services/db_svc/feeds/{feed_id}
Update an existing RSS feed.

**Request:**
```bash
curl -X PUT http://localhost:8004/services/db_svc/feeds/2 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Feed Title",
    "active": false
  }'
```

#### DELETE /services/db_svc/feeds/{feed_id}
Delete an RSS feed.

```bash
curl -X DELETE http://localhost:8004/services/db_svc/feeds/2
```

### User Management

#### GET /services/db_svc/users
List all users.

```bash
curl http://localhost:8004/services/db_svc/users?limit=20&offset=0
```

#### POST /services/db_svc/users
Create or update a user.

**Request:**
```bash
curl -X POST http://localhost:8004/services/db_svc/users \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "username": "johndoe",
    "first_name": "John",
    "subscription_type": "free"
  }'
```

## 🤖 Bot Service APIs

### Message Operations

#### POST /services/bot_svc/send-message
Send a message to a Telegram chat.

**Request:**
```bash
curl -X POST http://localhost:8004/services/bot_svc/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": -1001234567890,
    "text": "Hello from RssBot!",
    "parse_mode": "HTML"
  }'
```

**Response:**
```json
{
  "message_id": 12345,
  "chat_id": -1001234567890,
  "sent_at": "2024-01-15T10:40:00Z",
  "status": "sent"
}
```

#### POST /services/bot_svc/broadcast
Broadcast a message to multiple chats.

**Request:**
```bash
curl -X POST http://localhost:8004/services/bot_svc/broadcast \
  -H "Content-Type: application/json" \
  -d '{
    "chat_ids": [-1001234567890, -1001234567891],
    "text": "RSS Feed Update!",
    "parse_mode": "HTML"
  }'
```

### Webhook Management

#### POST /services/bot_svc/set-webhook
Configure Telegram webhook.

**Request:**
```bash
curl -X POST http://localhost:8004/services/bot_svc/set-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/webhook",
    "secret_token": "your_webhook_secret"
  }'
```

#### DELETE /services/bot_svc/webhook
Remove Telegram webhook (switch to polling).

```bash
curl -X DELETE http://localhost:8004/services/bot_svc/webhook
```

## 🧠 AI Service APIs

### Content Processing

#### POST /services/ai_svc/summarize
Summarize content using AI.

**Request:**
```bash
curl -X POST http://localhost:8004/services/ai_svc/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Long article content here...",
    "max_length": 200,
    "language": "en"
  }'
```

**Response:**
```json
{
  "original_text": "Long article content here...",
  "summary": "Brief summary of the article...",
  "summary_length": 45,
  "processing_time_ms": 1250,
  "model_used": "gpt-3.5-turbo"
}
```

#### POST /services/ai_svc/enhance
Enhance content with AI.

**Request:**
```bash
curl -X POST http://localhost:8004/services/ai_svc/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Original content",
    "enhancement_type": "readability",
    "target_audience": "general"
  }'
```

#### POST /services/ai_svc/translate
Translate content to another language.

**Request:**
```bash
curl -X POST http://localhost:8004/services/ai_svc/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "target_language": "es",
    "source_language": "en"
  }'
```

## 💳 Payment Service APIs

### Subscription Management

#### GET /services/payment_svc/subscriptions
List user subscriptions.

```bash
curl http://localhost:8004/services/payment_svc/subscriptions?user_id=123456789
```

#### POST /services/payment_svc/create-checkout
Create a Stripe checkout session.

**Request:**
```bash
curl -X POST http://localhost:8004/services/payment_svc/create-checkout \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123456789,
    "price_id": "price_premium_plan",
    "success_url": "https://yourdomain.com/success",
    "cancel_url": "https://yourdomain.com/cancel"
  }'
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_...",
  "session_id": "cs_test_1234567890",
  "expires_at": "2024-01-15T11:40:00Z"
}
```

## ⚙️ Admin APIs

### Platform Configuration

#### GET /admin/config
Get current platform configuration.

```bash
curl -H "X-API-Key: your_admin_key" \
     http://localhost:8004/admin/config
```

#### POST /admin/config/reload
Reload platform configuration without restart.

```bash
curl -X POST -H "X-API-Key: your_admin_key" \
     http://localhost:8004/admin/config/reload
```

### Monitoring & Metrics

#### GET /admin/metrics
Get platform performance metrics.

```bash
curl -H "X-API-Key: your_admin_key" \
     http://localhost:8004/admin/metrics
```

**Response:**
```json
{
  "platform": {
    "uptime_seconds": 86400,
    "requests_total": 15476,
    "errors_total": 23,
    "avg_response_time_ms": 45
  },
  "services": {
    "db_svc": {
      "requests": 8234,
      "errors": 5,
      "avg_response_time_ms": 12
    },
    "ai_svc": {
      "requests": 1245,
      "errors": 8,
      "avg_response_time_ms": 234
    }
  },
  "cache": {
    "hit_rate": 0.87,
    "total_hits": 13463,
    "total_misses": 2013
  }
}
```

#### GET /admin/logs/{service_name}
Get logs for a specific service.

```bash
curl -H "X-API-Key: your_admin_key" \
     "http://localhost:8004/admin/logs/ai_svc?limit=100&level=ERROR"
```

## 🚨 Error Handling

### Standard Error Response

All APIs return consistent error responses:

```json
{
  "error": {
    "code": "SERVICE_NOT_FOUND",
    "message": "Service 'unknown_svc' not found",
    "details": {
      "service_name": "unknown_svc",
      "available_services": ["db_svc", "ai_svc", "bot_svc"]
    },
    "timestamp": "2024-01-15T10:45:00Z",
    "request_id": "req_1234567890"
  }
}
```

### Common Error Codes

| Code                  | HTTP Status | Description                          |
|-----------------------|-------------|--------------------------------------|
| `INVALID_REQUEST`     | 400         | Malformed request body or parameters |
| `UNAUTHORIZED`        | 401         | Missing or invalid authentication    |
| `FORBIDDEN`           | 403         | Insufficient permissions             |
| `SERVICE_NOT_FOUND`   | 404         | Requested service doesn't exist      |
| `METHOD_NOT_ALLOWED`  | 405         | HTTP method not supported            |
| `RATE_LIMIT_EXCEEDED` | 429         | Too many requests                    |
| `SERVICE_UNAVAILABLE` | 503         | Service temporarily unavailable      |
| `INTERNAL_ERROR`      | 500         | Unexpected server error              |

## 📊 Rate Limiting

### Rate Limit Headers

All API responses include rate limiting information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642234800
X-RateLimit-Window: 3600
```

### Rate Limits by Endpoint Type

| Endpoint Type           | Rate Limit  | Window      |
|-------------------------|-------------|-------------|
| **Health/Status**       | 100 req/min | Per IP      |
| **Service Management**  | 50 req/min  | Per API key |
| **Database Operations** | 200 req/min | Per API key |
| **AI Processing**       | 60 req/min  | Per API key |
| **Admin Operations**    | 30 req/min  | Per API key |

## 🔧 SDK and Libraries

### Python SDK

```python
from rssbot_client import RssBotClient

client = RssBotClient(
    base_url="http://localhost:8004",
    service_token="your_service_token"
)

# Get platform health
health = await client.get_health()

# Manage services
await client.set_connection_method("ai_svc", "hybrid")

# Send messages
await client.send_message(
    chat_id=-1001234567890,
    text="Hello from Python!"
)
```

### JavaScript SDK

```javascript
import { RssBotClient } from '@rssbot/client';

const client = new RssBotClient({
  baseUrl: 'http://localhost:8004',
  serviceToken: 'your_service_token'
});

// Get services
const services = await client.getServices();

// Process with AI
const summary = await client.ai.summarize({
  text: 'Long content...',
  maxLength: 200
});
```

---

**📚 This API reference covers all major endpoints. For interactive API exploration, visit `/docs` on your running platform instance.**
