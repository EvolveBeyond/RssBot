# Evox Framework Design Document

## Overview

Evox is a modern, lightweight, plugin-first microservices framework built on FastAPI. It provides a simpler, more intuitive way to build distributed systems while retaining the full power of FastAPI through escape hatches.

## Architecture

### Core Components

1. **Service Builder**: Fluent API for creating services with minimal configuration
2. **Service Proxy**: Intelligent inter-service communication with automatic routing
3. **Unified Storage**: Key-value interface with pluggable backends
4. **Orchestrator**: Auto-discovers and manages services
5. **CLI**: Command-line interface for project and service management

### Design Principles

1. **Simplicity First**: APIs should be simple and intuitive
2. **Plugin Architecture**: All components should be replaceable/pluggable
3. **Zero Configuration**: Work out of the box with sensible defaults
4. **Escape Hatches**: Provide access to underlying FastAPI when needed
5. **Performance**: Optimize for modern microservices patterns

## Service Builder

The Service Builder provides a fluent API for creating services:

```python
from evox.core import ServiceBuilder

service = ServiceBuilder("my_service") \
    .with_port(8001) \
    .with_health("/health") \
    .enable_caching(ttl=300)
```

### Features

- Method chaining for configuration
- Built-in health check endpoint
- Optional caching support
- Startup/shutdown handlers
- Background tasks
- Grouped routes

## Service Proxy

The Service Proxy enables intelligent service-to-service communication:

```python
from evox.core import proxy

result = await proxy.other_service.method(
    cache_ttl=300, stale_if_error=True, max_stale=60
)
```

### Features

- Automatic routing decisions
- Caching with stale-while-revalidate
- Fallback mechanisms
- Health-based routing

## Unified Storage

The Unified Storage provides a consistent interface for data persistence:

```python
from evox.core import storage

await storage.set("cache:temp", data, ttl=300)
data = await storage.get("cache:temp")
```

### Features

- Namespace support (`system:`, `cache:`, `app:`, custom)
- Pluggable backends (memory, Redis, PostgreSQL, hybrid)
- TTL-aware operations
- Pattern-based key listing

## Orchestrator

The Orchestrator manages service discovery and lifecycle:

### Features

- Auto-discovery of services in `services/` directory
- Dynamic service loading
- Health monitoring
- Service registry management

## CLI Commands

The CLI provides project and service management:

```bash
# Create project
evox new pj my_project

# Create service
evox new sv my_service

# Run platform
evox run --dev

# Sync services
evox sync sv

# Show status
evox status
```

## Configuration

Evox uses TOML configuration files for simplicity:

```toml
# services/my_service/config.toml
name = "my_service"
port = 8001

[storage]
backend = "redis"
redis_url = "redis://localhost:6379/0"
```

## Migration from RssBot

Evox evolved from the RssBot framework but with significant improvements:

### Key Improvements

1. **Generic Framework**: Not domain-specific like RssBot
2. **Simplified APIs**: Much easier to use than RssBot's complex hybrid system
3. **Pluggable Architecture**: All components can be replaced
4. **Better Tooling**: Modern CLI and development tools
5. **Documentation**: Comprehensive guides and examples

### Migration Path

See `MIGRATION_GUIDE.md` for detailed migration instructions.

## Future Enhancements

Planned features for future releases:

1. **Advanced Caching**: Distributed caching with consensus
2. **Service Mesh**: Integration with Istio/Linkerd
3. **Observability**: Built-in metrics, tracing, and logging
4. **Security**: OAuth2, JWT, and RBAC support
5. **Deployment**: Kubernetes operators and Helm charts

## Conclusion

Evox represents the next generation of Python microservices frameworks, combining the performance of FastAPI with the simplicity of modern design patterns. It fills the gap for truly modern Python backends: hybrid microservices orchestration, self-healing, dynamic discovery, intelligent caching with fallback, pluggable storage, and CLI-driven development.