# Evox Step-by-Step Tutorial

## Alpha Status Notice

> **⚠️ Alpha Status**: Evox is in early alpha (0.0.3-alpha) — expect changes. Feedback welcome!

Evox is a modern microservices framework for Python, designed exclusively for Rye package management. Evox leverages FastAPI's built-in capabilities for optimal performance and developer experience.

---

## Step 1: Installation and Setup

Evox is designed exclusively for Rye — the modern Python project manager. Let's start by installing Evox and setting up our environment.

### Prerequisites

- Python 3.11 or higher
- Rye package manager (installation instructions at [https://rye-up.com](https://rye-up.com))

### Installing Evox

To install Evox globally so you can use the CLI:

```bash
# Install Evox globally using Rye
rye install evox
```

This installs the `evox` command-line tool that you'll use throughout this tutorial.

---

## Step 2: Creating Your First Project

Evox provides built-in commands to scaffold new projects. Let's create our first Evox project.

### Creating a New Project

```bash
# Create a new Evox project named "my_first_project"
evox new pj my_first_project

# Navigate to your new project directory
cd my_first_project
```

### Understanding the Project Structure

After running `evox new pj my_first_project`, you'll see this structure:

```
my_first_project/
├── config.toml          # Project configuration
├── .env.example         # Environment variables template
├── pyproject.toml       # Rye/Hatch configuration
├── README.md            # Project README
└── services/            # Directory for your services
```

Let's examine the key files:

#### pyproject.toml

This file configures your project for Rye and Hatch:

```toml
[project]
name = "my_first_project"
version = "0.1.0"
description = "Evox microservices project - Rye-Native"
# ... other configuration

[tool.rye]
managed = true
dev-dependencies = [
    "pytest>=7.0.0,<8.0.0",
    "httpx>=0.25.0,<0.26.0",
    "black>=23.0.0,<24.0.0",
    "isort>=5.12.0,<6.0.0",
]

[tool.rye.scripts]
dev = "evox run --dev"
health = "evox health"
test = "evox test"
```

Notice the Rye scripts that make development easier:
- `rye run dev` - Run in development mode with auto-reload
- `rye run health` - Check service health
- `rye run test` - Run tests

---

## Step 3: Creating Your First Service

Now let's create a service within our project.

```bash
# Make sure you're in your project directory
cd my_first_project

# Create a new service named "user_service"
evox new sv user_service
```

### Understanding the Service Structure

After running `evox new sv user_service`, you'll see this structure in the `services/` directory:

```
services/
└── user_service/
    ├── config.toml      # Service configuration
    └── main.py          # Service implementation
```

Let's examine the generated service template:

#### services/user_service/main.py

The template shows both function-based and class-based syntax options:

```python
# Function-based syntax (default, minimal, FastAPI-familiar)
# Uncomment this section to use function-based syntax
"""
from evox import service, get, post, delete, Param, Query, Body, Intent, auth, data_io

svc = service("user_service") \
    .port(8000) \
    .build()

@get("/users/{user_id:int}", cache=3600)
@post("/users")
@delete("/users/{user_id:int}", auth_role="admin")
async def user_operations(user_id: Param[int] | None = None, data: Body[dict] | None = None):
    # Implementation here...
"""

# Class-based syntax (opt-in, grouped, NestJS-inspired)
# Uncomment this section to use class-based syntax
from evox import service, Controller, GET, POST, DELETE, Param, Query, Body, Intent, auth, data_io

svc = service("user_service") \
    .port(8000) \
    .build()

@Controller("/users", cache=300, auth=True, tags=["users"])
class UserController:

    @GET("/{user_id:int}", cache=3600, priority="high")
    @Intent.cacheable(ttl=3600)
    async def get_user(self, user_id: Param[int]):
        """Get user by ID"""
        # Implementation here...

    @POST("/")
    async def create_user(self, data: Body[dict]):
        """Create new user"""
        # Implementation here...

    @DELETE("/{user_id:int}", auth_role="admin")
    async def delete_user(self, user_id: Param[int]):
        """Delete user (admin only)"""
        # Implementation here...

    @GET("/search", priority="medium")
    async def search_users(self, q: Query[str] = None):
        """Search users"""
        # Implementation here...

# Example background task
@svc.background_task(interval=60)
async def cleanup_expired_data():
    # Cleanup expired data periodically
    print("Cleaning up expired data...")

# Example startup handler
@svc.on_startup
async def startup():
    print("user_service service started")

# Example shutdown handler
@svc.on_shutdown
async def shutdown():
    print("user_service service stopped")

if __name__ == "__main__":
    svc.run(dev=True)
```

---

## Step 4: Implementing a Simple Service

Let's implement a simple user service using the function-based syntax. Replace the contents of `services/user_service/main.py` with:

```python
"""
User Service - Simple implementation
"""
from evox import service, get, post, put, delete, Param, Body, Intent
from pydantic import BaseModel

# Define data models
class UserCreate(BaseModel):
    name: str
    email: str

class UserUpdate(BaseModel):
    name: str = None
    email: str = None

# Create service
svc = service("user_service") \
    .port(8000) \
    .build()

# In-memory storage for demo purposes
users_db = {}

# GET endpoint to retrieve a user
@get("/users/{user_id}")
@Intent.cacheable(ttl=3600)  # Cache for 1 hour
async def get_user(user_id: str = Param()):
    """Get user by ID"""
    if user_id in users_db:
        return users_db[user_id]
    else:
        return {"error": "User not found"}, 404

# POST endpoint to create a user
@post("/users")
@Intent(consistency="strong")  # Strong consistency for creation
async def create_user(user_data: UserCreate = Body()):
    """Create a new user"""
    user_id = str(len(users_db) + 1)
    users_db[user_id] = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email
    }
    return {"message": "User created", "user": users_db[user_id]}, 201

# PUT endpoint to update a user
@put("/users/{user_id}")
@Intent(consistency="strong")  # Strong consistency for updates
async def update_user(user_id: str = Param(), update_data: UserUpdate = Body()):
    """Update an existing user"""
    if user_id in users_db:
        if update_data.name is not None:
            users_db[user_id]["name"] = update_data.name
        if update_data.email is not None:
            users_db[user_id]["email"] = update_data.email
        return {"message": "User updated", "user": users_db[user_id]}
    else:
        return {"error": "User not found"}, 404

# DELETE endpoint to remove a user
@delete("/users/{user_id}")
@Intent(consistency="strong")  # Strong consistency for deletion
async def delete_user(user_id: str = Param()):
    """Delete a user"""
    if user_id in users_db:
        del users_db[user_id]
        return {"message": "User deleted"}
    else:
        return {"error": "User not found"}, 404

# GET endpoint to list all users
@get("/users")
@Intent.cacheable(ttl=300)  # Cache for 5 minutes
async def list_users():
    """List all users"""
    return {"users": list(users_db.values())}

if __name__ == "__main__":
    svc.run()
```

---

## Step 5: Running Your Service

Now let's run our service to see it in action.

### Development Mode

For development with auto-reload:

```bash
# Using the Rye script
rye run dev

# Or directly using the evox command
evox run --dev
```

### Production Mode

For production:

```bash
# Using the evox command
evox run
```

Visit `http://localhost:8000` to see your service running. You can also visit `http://localhost:8000/docs` to see the automatically generated API documentation.

---

## Step 6: Using Other Evox Commands

Evox provides several useful commands for managing your project:

### Sync Commands

```bash
# Sync database (runs migrations if needed)
evox sync db

# Sync services (validates service prerequisites)
evox sync sv
```

### Status and Health

```bash
# Check platform status
evox status

# Check health using FastAPI docs
evox health

# Run specific health tests
evox health --test connection
evox health --test framework
evox health --test services
evox health --test all
```

### Cache Management

```bash
# Invalidate specific cache key
evox cache invalidate user:123

# Invalidate all cache
evox cache invalidate
```

### Testing

```bash
# Run tests
evox test
```

---

## Step 7: Creating Additional Services

Let's create another service to demonstrate inter-service communication:

```bash
# Create an items service
evox new sv items_service
```

Replace the contents of `services/items_service/main.py` with:

```python
"""
Items Service - Simple implementation
"""
from evox import service, get, post, Controller, GET, POST, Body, Intent
from pydantic import BaseModel

# Define data model
class ItemCreate(BaseModel):
    name: str
    price: float

# Create service
svc = service("items_service") \
    .port(8001) \
    .build()

# In-memory storage for demo purposes
items_db = {}

@Controller("/items", tags=["items"])
class ItemsController:
    
    @GET("/")
    @Intent.cacheable(ttl=300)
    async def list_items(self):
        """List all items"""
        return {"items": list(items_db.values())}
    
    @POST("/")
    @Intent(consistency="strong")
    async def create_item(self, item_data: ItemCreate = Body()):
        """Create a new item"""
        item_id = str(len(items_db) + 1)
        items_db[item_id] = {
            "id": item_id,
            "name": item_data.name,
            "price": item_data.price
        }
        return {"message": "Item created", "item": items_db[item_id]}, 201

if __name__ == "__main__":
    svc.run()
```

---

## Step 8: Understanding Evox's Unique Features

### Dual Syntax Support

Evox supports both function-based and class-based syntax:

1. **Function-based** (default): Similar to FastAPI, good for simple services
2. **Class-based** (opt-in): Grouped endpoints like NestJS, good for complex services

Both syntaxes are equally powerful and performant.

### Data Intent Awareness

Evox uses data intents to automatically determine behavior:

```python
@Intent.cacheable(ttl=3600)  # Cache for 1 hour
@Intent(consistency="strong")  # Require strong consistency
```

### Context-Aware Proxy

Evox automatically handles internal vs external service calls:

```python
# Internal calls are efficient
user_data = await proxy.user_service.get.get_user(123)

# External calls are automatically secured
# (handled transparently by the framework)
```

### Priority-Aware Concurrency

Control request priority:

```python
@GET("/users/{user_id}", priority="high")
@GET("/reports", priority="low")
```

---

## Step 9: Testing Your Services

Evox provides built-in testing capabilities:

```bash
# Run health checks
evox health --test all

# Run your own tests
evox test
```

You can also use the health system to verify your services are working correctly:

```bash
# Test framework components
evox health --test framework

# Test service connectivity
evox health --test connection
```

---

## What's Next?

You've now learned the basics of Evox:

1. **Installation**: Using Rye to install Evox
2. **Project Creation**: Using `evox new pj` to create projects
3. **Service Creation**: Using `evox new sv` to create services
4. **Running Services**: Using `evox run` and `evox run --dev`
5. **Management Commands**: Using `evox sync`, `evox status`, `evox health`
6. **Unique Features**: Dual syntax, data intents, context-aware proxy

Continue exploring Evox's advanced features:
- Authentication and security
- Advanced data storage with pluggable backends
- Priority queues and concurrency control
- Service-to-service communication patterns
- Deployment strategies

Check out the full documentation and examples in the Evox repository!