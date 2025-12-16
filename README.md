# Evox - Modern Python Microservices Framework (v0.0.2-alpha - Optimized & Rye-Native)

Evox is a modern microservices framework for Python, designed exclusively for Rye package management. Evox leverages FastAPI's built-in capabilities for optimal performance and developer experience.

This is not an application or bot framework — it is a pure framework aimed at changing how we think about building scalable Python backends in the modern era.

> **⚠️ Rye Exclusive**: Evox is designed exclusively for Rye — use `rye sync`, `rye run`, `rye add` for all operations. No support for pip requirements.txt or other tools.

> **⚠️ Alpha Status**: Evox is in very early alpha (v0.0.2-alpha) - not yet beta. Expect breaking changes. Features are experimental and evolving.

## Key Features (v0.0.2-alpha - Optimized & Rye-Native)

### 🔄 Revolutionary Dual Syntax Support
- **Function-based syntax** (default, minimal, FastAPI-familiar) for quick projects
- **Class-based syntax** (opt-in, grouped, NestJS-inspired) for larger/team projects
- **Both syntaxes equally supported** - no preference, both fully featured and performant
- **Orchestrator auto-detection** of either syntax style
>>>>>>> 8b4dd62 (Everything is being finalized and moving towards a stable version.)

### 🎯 Data-Intent-Aware Architecture
- **Shift from "Storage-aware" to Data-Intent-aware**: System infers storage/cache/consistency behavior from explicit data intents
- **No mandatory DB/ORM/Redis**: Defaults to in-memory (ephemeral, TTL-aware) for everything
- **Unified `data_io` API**: `data_io.read(intent, key)` and `data_io.write(intent, obj/data)`
- **Intent declarations**: Via annotations or config (e.g., `@data_intent.cacheable(ttl="1h", consistency="strong")`)

### 🔐 Robust Authentication System
- **JWT + Role-Based Access Control**: Secure authentication with flexible role management
- **Context-Aware Proxy**: Automatic detection of internal vs external calls
- **Multi-Method Endpoints**: Same path with different handlers per HTTP method
- **Intent-Integrated Security**: Data intents can enforce authentication requirements

### ⚡ Priority-Aware Concurrency
- **Strict Priority Enforcement**: Heap-based queue ensures HIGH > MEDIUM > LOW execution
- **Concurrency Caps**: Per-priority level limits prevent resource exhaustion
- **Fair Scheduling**: FIFO within same priority levels

### 🕵️ Observer-Only Management
- **Self-Introspective Services**: Each service exposes READ-ONLY monitoring endpoints
- **Optional Management Plane**: Separate coordinator service (observer pattern)
- **Autonomous Operation**: Services operate independently without management dependency

### ⚡ Priority-Aware Concurrency
- **Strict Priority Enforcement**: Heap-based queue ensures HIGH > MEDIUM > LOW execution
- **Concurrency Caps**: Per-priority level limits prevent resource exhaustion
- **Fair Scheduling**: FIFO within same priority levels

### 🕵️ Observer-Only Management
- **Self-Introspective Services**: Each service exposes READ-ONLY monitoring endpoints
- **Optional Management Plane**: Separate coordinator service (observer pattern)
- **Autonomous Operation**: Services operate independently without management dependency

### 🔐 Robust Authentication System
- **JWT + Role-Based Access Control**: Secure authentication with flexible role management
- **Context-Aware Proxy**: Automatic detection of internal vs external calls
- **Multi-Method Endpoints**: Same path with different handlers per HTTP method
- **Intent-Integrated Security**: Data intents can enforce authentication requirements

### ⚡ Priority-Aware Concurrency
- **Strict Priority Enforcement**: Heap-based queue ensures HIGH > MEDIUM > LOW execution
- **Concurrency Caps**: Per-priority level limits prevent resource exhaustion
- **Fair Scheduling**: FIFO within same priority levels

### 🕵️ Observer-Only Management
- **Self-Introspective Services**: Each service exposes READ-ONLY monitoring endpoints
- **Optional Management Plane**: Separate coordinator service (observer pattern)
- **Autonomous Operation**: Services operate independently without management dependency

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

## Quick Start: Function-based Syntax

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

Example function-based service (`basic_user_svc`):

```python
from evox import ServiceBuilder, Param, Body, Intent, inject
from pydantic import BaseModel

# Define data models
class UserCreate(BaseModel):
    name: str
    email: str
    age: int

# Create service
service = ServiceBuilder("basic-user-service")

# In-memory storage for demo purposes
users_db = {}

# Multi-method endpoint demonstrating different HTTP verbs
@service.endpoint("/{user_id}", methods=["GET", "PUT", "DELETE"])
@Intent(cacheable=True)  # This operation can be cached
async def user_operations(user_id: str = Param(), update_data: UserUpdate = Body(None)):
    """Handle user operations: GET, PUT, DELETE"""
    if update_data:  # PUT request
        if user_id in users_db:
            # Update existing user
            if update_data.name is not None:
                users_db[user_id]["name"] = update_data.name
            # ... update other fields
            return {"message": "User updated", "user": users_db[user_id]}
        else:
            return {"error": "User not found"}, 404
    
    # Check if this is a DELETE request
    import inspect
    frame = inspect.currentframe()
    request = frame.f_back.f_locals.get('request')
    if request and request.method == "DELETE":
        if user_id in users_db:
            del users_db[user_id]
            return {"message": "User deleted"}
        else:
            return {"error": "User not found"}, 404
    
    # GET request - retrieve user
    if user_id in users_db:
        return users_db[user_id]
    else:
        return {"error": "User not found"}, 404
```

## Advanced: Class-based Syntax

Example class-based service (`advanced_items_svc`):

```python
from evox import ServiceBuilder, Controller, GET, POST, PUT, DELETE, Param, Query, Body, Intent
from pydantic import BaseModel

# Define data models
class ItemCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str

class ItemUpdate(BaseModel):
    name: str = None
    description: str = None
    price: float = None
    category: str = None

# Controller with common settings applied to all methods
@Controller("/items", tags=["items"], version="v1")
@Intent(cacheable=True)  # Default intent for all methods in this controller
class ItemsController:
    
    # In-memory storage for demo purposes
    items_db = {}
    
    # GET method with specific overrides
    @GET("/{item_id}")
    @Intent(cacheable=True, ttl=600)  # Override default with longer TTL
    async def get_item(self, item_id: str = Param()):
        """Retrieve a specific item by ID"""
        if item_id in self.items_db:
            return self.items_db[item_id]
        else:
            return {"error": "Item not found"}, 404
    
    # GET method for listing items with query parameters
    @GET("/")
    @Intent(cacheable=True, ttl=300)  # Cacheable list with 5-minute TTL
    async def list_items(
        self, 
        category: str = Query(None),
        min_price: float = Query(None),
        max_price: float = Query(None)
    ):
        """List items with optional filtering"""
        filtered_items = list(self.items_db.values())
        
        if category:
            filtered_items = [item for item in filtered_items if item.get("category") == category]
        
        if min_price is not None:
            filtered_items = [item for item in filtered_items if item.get("price", 0) >= min_price]
        
        return {"items": filtered_items}
    
    # POST method with strong consistency requirement
    @POST("/")
    @Intent(consistency="strong")  # Strong consistency for creation
    async def create_item(self, item_data: ItemCreate = Body()):
        """Create a new item"""
        item_id = str(len(self.items_db) + 1)
        self.items_db[item_id] = {
            "id": item_id,
            "name": item_data.name,
            "description": item_data.description,
            "price": item_data.price,
            "category": item_data.category
        }
        return {"message": "Item created", "item": self.items_db[item_id]}, 201

# Create service and register controller
service = ServiceBuilder("advanced-items-service")
service.register_controller(ItemsController)
```

## Data-Intent-Aware Service Syntax

Evox services use a clean, intent-driven syntax:

```python
from evox.core import service, get, post, put, delete, data_io, data_intent, auth, inject

# Create service
svc = service("my_service") \
    .port(8001) \
    .health("/health") \
    .build()

# Declare data intent with security
@data_intent.cacheable(ttl="1h", consistency="eventual")
@auth.require_intent(intent_type="profile", required_roles=["user", "admin"])
class UserProfile:
    def __init__(self, user_id: int, name: str):
        self.user_id = user_id
        self.name = name

# Multi-method endpoint with priority and auth
@get("/users/{user_id}", priority="high")
@auth.require_intent(intent_type="user_read", required_roles=["user", "admin"])
async def get_user(user_id: int):
    # Read with automatic intent-based behavior
    user = await data_io.read(f"user:{user_id}")
    if not user:
        user = {"id": user_id, "name": f"User {user_id}"}
        # Write with intent (auto-cache for 1 hour)
        await data_io.write(f"user:{user_id}", user, ttl=3600)
    return user

@put("/users/{user_id}", priority="high")
@auth.require_intent(intent_type="user_write", required_roles=["user", "admin"])
async def update_user(user_id: int, user_data: dict):
    # Update user with injected dependencies
    db = inject.db()
    config = inject.config("user")
    # ... update logic
    return {"status": "updated"}

@delete("/users/{user_id}", priority="low")
@auth.require_intent(intent_type="user_delete", required_roles=["admin"])
async def delete_user(user_id: int):
    await data_io.delete(f"user:{user_id}")
    return {"status": "deleted"}

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
- `evox new sv <name>`: Create service with dual-syntax template
- `evox sync db`: Run optional migrations (triggers `rye sync` if dependencies changed)
- `evox sync sv`: Re-scan services, validate prerequisites (respects Rye lock file)
- `evox run --dev`: Uvicorn reload + verbose (Rye-aware)
- `evox run`: Production mode (Rye-aware)
- `evox status`: Show platform status
- `evox cache invalidate <key>`: Invalidate cache
- `evox test`: Run tests
- `evox dashboard`: Open admin dashboard
- `evox health`: Generate system health report (uses FastAPI native docs)
- `evox health --test connection`: Test storage and proxy connectivity
- `evox health --test framework`: Test DI, priority queue enforcement, dual syntax, inject override, and proxy multi-method
- `evox health --test services`: Test auth and cache fallback
- `evox health --test all`: Run all self-tests

## Context-Aware Service Proxy

Evox provides intelligent service-to-service communication with automatic context detection:

```python
# Internal calls (fast, direct routing with internal tokens)
user_data = await proxy.user_svc.get_user(123)

# External calls (secure, HTTPS + full authentication)
# Automatically enforced by the proxy

# Multi-method endpoints on same path
user = await proxy.user_svc.get_user(123)  # GET
result = await proxy.user_svc.update_user(123, data)  # PUT
status = await proxy.user_svc.delete_user(123)  # DELETE
```

## Priority Queue Integration

Evox now supports priority-aware request queuing with strict enforcement:

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

## Enhanced System Health Dashboard

The new `evox health` command generates a comprehensive HTML report with security insights:

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
- Authentication status and security warnings
- Proxy communication statistics (internal vs external)
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

The framework includes modern, educational example services in `evox/examples/` that showcase Evox's revolutionary features:

### `basic_user_svc` - Function-based syntax
Simple CRUD service demonstrating:
- Function-based syntax (default, minimal)
- Multi-method endpoints
- Data-intent annotations
- Lazy inject.service for inter-service calls
- Param/Body usage

### `advanced_items_svc` - Class-based syntax
Professional service showcasing:
- Class-based syntax (opt-in, grouped)
- @Controller with common settings
- Multi-method with per-method override
- Query/Param/Body type-safety
- Intent integration

### `storage_demo_svc` - Data-intent-aware storage
Focused on storage capabilities:
- Different intents (cacheable, strong consistency, eventual)
- Unified storage API
- Aggressive cache fallback

### `health_demo_svc` - Self-introspection
Observer-only management pattern:
- Exposes /capabilities, /health endpoints
- Optional management endpoints
- Self-monitoring capabilities

> Note: All examples use memory backend by default and are domain-agnostic, showcasing how modern backends should be written with Evox.

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
