# 🚀 RssBot Platform

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-5.0+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

> **The world's most advanced self-healing, per-service hybrid microservices platform for Telegram-RSS bots**

## ✨ Key Features

- **🏗️ Per-Service Architecture**: Each service independently chooses `router`/`rest`/`hybrid`/`disabled`
- **⚡ Redis-Cached Registry**: Sub-millisecond service discovery with automatic fallback
- **🔧 Zero-Downtime Configuration**: Live service reconfiguration without restarts
- **🏥 Self-Healing**: Automatic health monitoring and intelligent routing
- **🤖 AI-Powered**: OpenAI integration for intelligent content processing
- **🔒 Enterprise Security**: Service authentication, input validation, comprehensive monitoring

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/EvolveBeyond/RssBot.git
cd RssBot

# Install dependencies
pip install rye && rye sync

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start the platform
python -m rssbot
```

## 🏗️ Architecture

### Core Platform (`src/rssbot/`)
- **Core Controller**: Platform orchestration engine
- **Cached Registry**: Redis-backed service discovery
- **Service Proxy**: Intelligent inter-service routing
- **Migration Utils**: Legacy system compatibility

### Services (`services/`)
- **AI Service**: OpenAI integration for content processing
- **Bot Service**: Telegram gateway with webhook handling
- **Formatting Service**: Content transformation and templating
- **User Service**: Profile and subscription management
- **Payment Service**: Stripe integration for subscriptions
- **Channel Manager**: RSS feed monitoring and distribution

## 🔧 Service Configuration

```bash
# Configure individual services
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
     -H "Content-Type: application/json" \
     -d '{"connection_method": "router"}'

# Available methods: router, rest, hybrid, disabled
```

## 📚 Documentation

Complete documentation is available in our [Wiki](wiki/):

### English Documentation
- [Getting Started](wiki/en/Quick-Start.md)
- [Architecture Guide](wiki/en/Architecture.md)
- [API Reference](wiki/en/API.md)
- [Development Guide](wiki/en/Development.md)
- [Production Deployment](wiki/en/Production.md)

### Persian Documentation
- [راهنمای شروع](wiki/fa/راهنمای-شروع.md)
- [معماری سیستم](wiki/fa/معماری-سیستم.md)

## 🚀 Deployment

### Docker
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f infra/k8s/
```

### Multiple Entry Points
```bash
# Method 1: Core platform (recommended)
python -m rssbot

# Method 2: Controller wrapper
python services/controller_svc/main.py

# Method 3: Direct uvicorn
uvicorn rssbot.core.controller:create_platform_app
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../../wiki/CONTRIBUTING) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📄 License

Apache License 2.0 with attribution requirements for derivative services.
See [LICENSE](LICENSE) for details.

## 📞 Support

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)
- **Wiki**: [Documentation Wiki](../../wiki)
- **Security**: [Security Policy](SECURITY.md)

---

**Built with ❤️ for the RSS and Telegram community**