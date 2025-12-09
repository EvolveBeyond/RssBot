# RSS Bot Platform - Deployment Checklist

## ✅ Created Files and Directory Structure

### Project Structure
```
RssBot/
├── services/
│   ├── db_svc/
│   │   ├── db/
│   │   │   ├── models.py          # SQLModel definitions + ModelRegistry
│   │   │   └── engine.py          # Database engine + introspection
│   │   ├── alembic/               # Database migrations
│   │   │   ├── env.py
│   │   │   ├── script.py.mako
│   │   │   └── versions/
│   │   ├── alembic.ini
│   │   └── main.py                # Database service API
│   ├── bot_svc/
│   │   ├── bot_worker.py          # Aiogram bot implementation
│   │   └── main.py                # Bot HTTP API wrapper
│   ├── payment_svc/
│   │   └── main.py                # Payment gateway + Telegram Payments
│   ├── controller_svc/
│   │   └── main.py                # Service orchestrator + registry
│   ├── ai_svc/
│   │   └── main.py                # LLM adapter (OpenAI + mock)
│   ├── formatting_svc/
│   │   └── main.py                # Content transformation + job queue
│   ├── channel_mgr_svc/
│   │   └── main.py                # RSS feed management + monitoring
│   ├── user_svc/
│   │   └── main.py                # User profiles + subscriptions
│   └── miniapp_svc/
│       └── main.py                # Dashboard backend + UI
├── infra/
│   ├── docker-compose.yml         # Complete service stack
│   ├── Dockerfile.service         # Multi-service Docker image
│   ├── nginx.conf                 # Reverse proxy configuration
│   └── init.sql                   # Database initialization
├── scripts/
│   ├── smoke_test.sh              # Health check script
│   └── start_dev.sh               # Native development startup
├── contracts/
│   ├── db_service.json            # Database service OpenAPI spec
│   ├── bot_service.json           # Bot service API contract
│   └── formatting_service.json   # Formatting service contract
├── pyproject.toml                 # Rye project configuration
├── .env.example                   # Environment template
├── README.md                      # Complete documentation
└── DEPLOYMENT_CHECKLIST.md       # This file
```

## 🚀 Quick Start Commands

### Option 1: Router Mode (Single Process - Recommended for Development)
```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your configuration
echo "LOCAL_ROUTER_MODE=true" >> .env

# 2. Start infrastructure services
docker-compose -f infra/docker-compose.yml up -d postgres redis

# 3. Start controller with mounted services
cd services/controller_svc && rye run python main.py  # Port 8004

# 4. Access all services via controller
# Database API: http://localhost:8004/db/health
# User API: http://localhost:8004/users/health
# All services mounted under controller!
```

### Option 2: Full Docker Stack (Recommended for Testing)
```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your Telegram bot token and other settings

# 2. Start entire platform
docker-compose -f infra/docker-compose.yml up -d

# 3. Check service health
./scripts/smoke_test.sh

# 4. Access dashboard
open http://localhost:8009/dashboard
```

### Option 3: REST Mode - Native Development (Traditional Microservices)
```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with LOCAL_ROUTER_MODE=false

# 2. Start infrastructure services
docker-compose -f infra/docker-compose.yml up -d postgres redis

# 3. Start all application services natively
./scripts/start_dev.sh

# 4. Run health checks
./scripts/smoke_test.sh
```

### Option 4: Manual Service Startup (For Debugging)
```bash
# 1. Start infrastructure
docker-compose -f infra/docker-compose.yml up -d postgres redis

# 2. Start services individually (each in separate terminal)
cd services/db_svc && rye run python main.py           # Port 8001
cd services/controller_svc && rye run python main.py  # Port 8004  
cd services/bot_svc && rye run python main.py         # Port 8002
cd services/formatting_svc && rye run python main.py  # Port 8006
cd services/payment_svc && rye run python main.py     # Port 8003
cd services/user_svc && rye run python main.py        # Port 8008
cd services/channel_mgr_svc && rye run python main.py # Port 8007
cd services/ai_svc && rye run python main.py          # Port 8005
cd services/miniapp_svc && rye run python main.py     # Port 8009
```

## 🔧 System Requirements (Arch Linux)

### Required System Packages
```bash
sudo pacman -S python python-pip postgresql redis git curl
```

### Optional Development Tools
```bash
sudo pacman -S docker docker-compose nginx
```

### Rye Installation (if not installed)
```bash
curl -sSf https://rye-up.com/get | bash
source ~/.bashrc
```

## ⚙️ Configuration

### Essential Environment Variables (.env)
```bash
# Required - Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database (use Docker or local PostgreSQL)
DATABASE_URL=postgresql://rssbot:password@localhost:5432/rssbot

# Redis (for job queue)
REDIS_URL=redis://localhost:6379/0

# Service Security (change in production)
SERVICE_TOKEN=dev_service_token_change_in_production

# Optional - OpenAI for AI features
OPENAI_API_KEY=your_openai_api_key
```

## 🔍 Service Endpoints

### Router Mode (LOCAL_ROUTER_MODE=true)
All services accessible via controller at port 8004:
- Controller Health: http://localhost:8004/health
- Database API: http://localhost:8004/db/health
- User API: http://localhost:8004/users/health
- Example API: http://localhost:8004/example/health
- Local Services Info: http://localhost:8004/local-services
- Combined API Docs: http://localhost:8004/docs

### REST Mode (LOCAL_ROUTER_MODE=false)
#### Health Checks
- Database Service: http://localhost:8001/health
- Bot Service: http://localhost:8002/health  
- Payment Service: http://localhost:8003/health
- Controller Service: http://localhost:8004/health
- AI Service: http://localhost:8005/health
- Formatting Service: http://localhost:8006/health
- Channel Manager: http://localhost:8007/health
- User Service: http://localhost:8008/health
- MiniApp Service: http://localhost:8009/health

#### API Documentation (FastAPI auto-generated)
- Database API: http://localhost:8001/docs
- Bot API: http://localhost:8002/docs
- Payment API: http://localhost:8003/docs
- Controller API: http://localhost:8004/docs
- AI API: http://localhost:8005/docs
- Formatting API: http://localhost:8006/docs
- Channel Manager API: http://localhost:8007/docs
- User API: http://localhost:8008/docs
- Dashboard: http://localhost:8009/dashboard

## 🧪 Testing and Verification

### Run Smoke Tests
```bash
./scripts/smoke_test.sh
```

### Test Individual Services
```bash
# Test database introspection
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8001/tables

# Test bot status (requires bot token)
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8002/status

# Test content formatting
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     -H "Content-Type: application/json" \
     -d '{"feed_id":"test","raw_content":"Hello world","channel_profile":{"id":123}}' \
     http://localhost:8006/format
```

## 🏗️ Architecture Overview

### Service Groups

**Group A - Infrastructure Services:**
- `db_svc`: Database with SQLModel introspection
- `bot_svc`: Telegram gateway (aiogram)
- `payment_svc`: Payment processing (Telegram Payments + external)
- `controller_svc`: Service registry and orchestration
- `ai_svc`: LLM adapter (OpenAI integration)

**Group B - Domain Services:**
- `formatting_svc`: Content transformation and styling
- `channel_mgr_svc`: RSS feed monitoring and channel management
- `user_svc`: User profiles and subscription management
- `miniapp_svc`: Dashboard and management UI

### Communication Patterns
- **Synchronous**: HTTP/REST via FastAPI
- **Asynchronous**: Redis Streams for background jobs
- **Security**: Service tokens via `X-Service-Token` header (dev mode)
- **Discovery**: Services register with controller on startup

## 🔄 Router Mode vs REST Mode Comparison

| Feature | Router Mode (LOCAL_ROUTER_MODE=true) | REST Mode (LOCAL_ROUTER_MODE=false) |
|---------|--------------------------------------|-------------------------------------|
| **Latency** | Ultra-low (function calls) | Higher (HTTP overhead) |
| **Deployment** | Single process | Multiple processes |
| **Scaling** | Vertical only | Horizontal per service |
| **Debugging** | Shared process/logs | Isolated service logs |
| **Resource Usage** | Shared memory/CPU | Independent resources |
| **Development** | Faster iteration | Traditional microservices |
| **Production** | Single server only | Distributed deployment |
| **Fault Isolation** | Lower (shared process) | Higher (process boundaries) |

### When to Use Router Mode
✅ **Single server deployments**  
✅ **Development environments**  
✅ **Low-latency requirements**  
✅ **Simplified operations**  
✅ **Resource-constrained environments**

### When to Use REST Mode  
✅ **Multi-server distributed deployments**  
✅ **Production high-availability setups**  
✅ **Independent service scaling**  
✅ **Team-based service ownership**  
✅ **Fault isolation requirements**

## 🎯 Next Steps for Development

### 1. Test Both Modes
```bash
# Test router mode
echo "LOCAL_ROUTER_MODE=true" >> .env
./scripts/test_router_mode.sh

# Test REST mode  
echo "LOCAL_ROUTER_MODE=false" >> .env
./scripts/smoke_test.sh
```

### 2. Create New Services
```bash
# Copy example service template
cp -r services/example_svc services/my_new_svc
# Edit router.py and main.py for your service logic
# Service will auto-mount in router mode!
```

### 3. Configure Telegram Bot
```bash
# Set your bot token in .env
# Test bot responsiveness: /ping command
# Configure webhook for production deployment
```

### 4. Add RSS Feeds
```bash
# Use channel manager API to add feeds
# Test feed parsing and content formatting
# Verify message delivery to Telegram channels
```

### 5. Implement Business Logic
- RSS feed parsing and content extraction
- User subscription management
- Payment processing workflows
- AI-powered content enhancement
- Analytics and monitoring

### 6. Production Deployment
- Choose deployment mode (router vs REST)
- Replace service tokens with mTLS or JWT
- Configure proper secrets management
- Set up monitoring and logging
- Deploy with Kubernetes or Docker Swarm
- Configure ingress and TLS certificates

## 📚 Development Notes

### Database Migrations
```bash
cd services/db_svc
rye run alembic revision --autogenerate -m "Initial migration"
rye run alembic upgrade head
```

### Adding New Services
1. Create service directory under `services/`
2. Implement FastAPI app with `/health` and `/ready` endpoints
3. Add service token verification middleware
4. Register with controller service on startup
5. Update docker-compose.yml and scripts

### Custom Formatting Styles
- Implement in `formatting_svc/main.py`
- Use Jinja2 templates for advanced formatting
- Integrate with AI service for content enhancement

## 🔒 Security Considerations

### Development Mode
- Service tokens are shared secrets (change in production)
- No TLS encryption between services
- Webhook signatures not fully implemented

### Production Requirements
- Implement mTLS or JWT for service-to-service auth
- Use proper secret management (HashiCorp Vault, K8s secrets)
- Enable webhook signature verification
- Configure rate limiting and DDoS protection
- Implement audit logging

## 🐛 Troubleshooting

### Common Issues
1. **Port conflicts**: Adjust ports in .env file
2. **Database connection**: Verify PostgreSQL is running
3. **Bot token issues**: Check token format and permissions
4. **Service registration**: Check controller service logs

### Debugging Commands
```bash
# Check service logs (Docker)
docker-compose -f infra/docker-compose.yml logs service_name

# Check running processes (Native)
ps aux | grep python

# Test network connectivity
curl -v http://localhost:8001/health
```

---

🎉 **The RSS Bot platform scaffold is complete!** All services are implemented with clear contracts, proper separation of concerns, and ready for business logic implementation.