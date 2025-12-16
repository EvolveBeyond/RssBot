# Evox - Modern Python Microservices Framework (Data-Intent-Aware)

Evox is a modern, lightweight, plugin-first microservices framework built on FastAPI. It provides a simpler, more intuitive way to build distributed systems while retaining the full power of FastAPI through escape hatches.

> **⚠️ Alpha Status**: Evox is in early alpha (v0.0.1-alpha) - not yet beta. Expect breaking changes. Ideas and implementation are experimental and evolving.

## Key Features (Data-Intent-Aware Evolution)

### 🎯 Data-Intent-Aware Architecture
- **Shift from "Storage-aware" to Data-Intent-aware**: System infers storage/cache/consistency behavior from explicit data intents
- **No mandatory DB/ORM/Redis**: Defaults to in-memory (ephemeral, TTL-aware) for everything
- **Unified `data_io` API**: `data_io.read(intent, key)` and `data_io.write(intent, obj/data)`
- **Intent declarations**: Via annotations or config (e.g., `@data_intent.cacheable(ttl="1h", consistency="strong")`)

### 🧼 Clean, Minimal Framework
- **Zero external dependencies by default**: Perfect for dev/test/prototyping
- **SQLite optional lightweight fallback**: For persistent storage when needed
- **ORM completely optional**: Signal producer only - domain models remain pure
- **Heavy consistency/cache handled transparently**: Based on declared intents

### ⚡ Modern Developer Experience
- **Fluent API**: Method chaining on `service = service("name")` + minimal decorators
- **Familiar syntax**: Decorator endpoints like FastAPI, but zero boilerplate
- **Escape hatches**: `service.app` for raw FastAPI access when needed
- **Rye-optimized**: Native support for modern Python package management

### 🔥 Advanced Features (v0.0.1-alpha)
- **Priority-Aware Request Queue**: High/Medium/Low priority levels with concurrency caps
- **Aggressive Cache Fallback**: Serve stale data beyond TTL during downtime
- **System Health Dashboard**: Rich HTML report with service statuses and metrics
- **Self-Healing Proxy**: Automatic retry and fallback mechanisms

## Installation

```bash
pip install evox
```

Or with Rye:

```bash
rye add evox
```

## Quick Start

Create a new Evox project:

```bash
evox new pj my_project
cd my_project
```

Create a service:

```bash
evox new sv my_service
```

Run in development mode:

```bash
evox run --dev
```

## Data-Intent-Aware Service Syntax

Evox services use a clean, intent-driven syntax:

```python
from evox.core import service, get, post, data_io, data_intent

# Create service
svc = service("my_service") \
    .port(8001) \
    .health("/health") \
    .build()

# Declare data intent
@data_intent.cacheable(ttl="1h", consistency="eventual")
class UserProfile:
    def __init__(self, user_id: int, name: str):
        self.user_id = user_id
        self.name = name

# Endpoint with intent-aware data IO
@get("/users/{user_id}")
async def get_user(user_id: int):
    # Read with automatic intent-based behavior
    user = await data_io.read(f"user:{user_id}")
    if not user:
        user = {"id": user_id, "name": f"User {user_id}"}
        # Write with intent (auto-cache for 1 hour)
        await data_io.write(f"user:{user_id}", user, ttl=3600)
    return user

# Background task
@svc.background_task(interval=60)
async def cleanup():
    print("Cleaning expired data...")

# Startup/shutdown
@svc.on_startup
async def startup():
    print("Service started")

@svc.on_shutdown
async def shutdown():
    print("Service stopped")
```

## CLI Commands

- `evox new pj <name>`: Scaffold minimal project (Rye-optimized structure)
- `evox new sv <name>`: Create service with data-intent template
- `evox sync db`: Run optional migrations
- `evox sync sv`: Re-scan services, validate prerequisites
- `evox run --dev`: Uvicorn reload + verbose
- `evox run`: Production mode
- `evox status`: Show platform status
- `evox cache invalidate <key>`: Invalidate cache
- `evox test`: Run tests
- `evox dashboard`: Open admin dashboard
- `evox health`: Generate system health report (NEW!)

## Priority Queue Integration

Evox now supports priority-aware request queuing:

```python
# Per-endpoint priority
@get("/critical", priority="high")
async def critical_endpoint():
    return {"status": "urgent"}

# Per-gather with concurrency control
results = await proxy.gather(
    service1.call(), 
    service2.call(),
    priority="medium",
    concurrency=5
)
```

## Aggressive Cache Fallback

Serve stale data gracefully during outages:

```python
# Endpoint with aggressive fallback
@get("/data", cache=3600, fallback="aggressive", max_stale="24h")
async def get_data():
    # Will serve stale data for up to 24h if source is unavailable
    return await fetch_from_source()
```

## System Health Dashboard

The new `evox health` command generates a comprehensive HTML report:

```bash
evox health
```

Features:
- Overall system health (green/yellow/red)
- Per-service status with health endpoint results
- Registry contents visualization
- Cache statistics (hits/misses/stale data)
- Active data intents and backends in use
- Priority queue lengths and admission stats
- Recent errors/warnings with detailed reasons
- Dependency validation results

The report automatically opens in your default browser, with terminal fallback.

## Architecture

Evox follows a modern microservices architecture with:

1. **Service Builder**: Fluent API for creating services
2. **Data IO**: Intent-aware unified data interface
3. **Service Proxy**: Intelligent inter-service communication
4. **Orchestrator**: Auto-discovers and manages services
5. **CLI**: Project and service management

## Core Concept: Data Intents vs CIA

### Data Intents (Operational Behavior)
Focus on operational behavior:
- `@data_intent.cacheable(ttl="1h", consistency="eventual")`
- `@data_intent.strong_consistency()`
- `@data_intent.eventual_ok()`

### CIA (Future Security Layer - Optional)
Separate opt-in layer for security classification (not implemented in V3.0):
- Confidentiality levels
- Integrity requirements
- Availability priorities

## Zero-Dependency Philosophy

Evox runs with zero external dependencies by default:
- **Development/Testing**: Pure in-memory ephemeral storage
- **Production**: Optional SQLite fallback or opt-in PostgreSQL/Redis
- **No ORM Required**: Domain models stay pure - no `.save()`/`.get()` pollution
- **Automatic Behavior**: System handles caching, invalidation, consistency based on intents

## Examples

The framework includes example services in `evox/examples/rssbot/`:
- `user_svc`: User management with data intents
- `storage_demo_svc`: Data IO demonstrations

## Community & Contributing

We welcome contributions from the community! Evox is in active development and we're looking for contributors to help shape its future.

### How to Contribute
1. Check out our [CONTRIBUTING.md](CONTRIBUTING.md) guide
2. Look for "good first issue" labels for beginner-friendly tasks
3. Join discussions on GitHub for architectural proposals

## License

Evox is fully open source and released under the Apache License 2.0. This permissive license allows for commercial use, modification, distribution, and patent use without any restrictions. It also provides an express grant of patent rights from contributors to users.

### Supporting Our Work

While the Apache License 2.0 imposes no financial obligations, we kindly encourage organizations and individuals who derive significant commercial value from Evox to consider contributing to its sustainability.

Voluntary financial contributions help us to:
- Continuously improve the project
- Fix bugs and address security vulnerabilities promptly
- Ensure the project remains healthy and accessible for everyone

If your company uses Evox and benefits from it, please consider supporting us through:
- [GitHub Sponsors](https://github.com/sponsors) (coming soon)
- [Open Collective](https://opencollective.com) (coming soon)

This is a voluntary, non-binding request, not a licensing condition. We are grateful for any form of support, whether it's a financial contribution, a code contribution, or simply spreading the word.

See [LICENSE](LICENSE) for the full license text and [LICENSE.md](LICENSE.md) for more information about supporting the project.

## Acknowledgments

Evox is built on top of excellent open-source foundations. We're grateful to the creators and maintainers of:

### Core Dependencies
- FastAPI by Sebastián Ramírez (@tiangolo)
- Typer by Sebastián Ramírez (@tiangolo)
- Pydantic by Samuel Colvin and contributors
- Uvicorn by Tom Christie and contributors
- HTTPX by Encode OSS Ltd and contributors

### Additional Dependencies
- Jinja2 by Armin Ronacher and contributors
- Tomli/TOML by Taneli Hukkinen and contributors
- Aiosqlite by Amethyst Reese and contributors
- Webbrowser (Python Standard Library)

*Evox is in early alpha - not yet beta. Expect breaking changes. Ideas and implementation are experimental and evolving.*
