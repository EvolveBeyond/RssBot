"""
MiniApp Service - Admin dashboard for Evox platform
"""
import tomli
from evox.core import service, get, post
from evox.core.storage import storage

# Load configuration
try:
    with open("config.toml", "rb") as f:
        config = tomli.load(f)
except FileNotFoundError:
    config = {}

# Create service
svc = service("miniapp_svc") \
    .port(config.get("port", 8002)) \
    .health("/health") \
    .caching(ttl=300) \
    .build()

# Dashboard endpoint
@get("/")
async def dashboard():
    return {"message": "Evox Admin Dashboard", "version": "0.1.0"}

# Health endpoint
@get("/health")
async def health():
    return {"status": "healthy", "service": "miniapp_svc"}

# Config management
@get("/config")
async def get_config():
    # In a real implementation, this would return the current configuration
    return {"config": config}

@post("/config")
async def update_config(new_config: dict):
    # In a real implementation, this would update the configuration
    return {"status": "updated", "config": new_config}

# Cache management
@get("/cache/stats")
async def cache_stats():
    # In a real implementation, this would return cache statistics
    return {"cache_stats": "Not implemented"}

@post("/cache/invalidate")
async def invalidate_cache(keys: dict):
    # In a real implementation, this would invalidate cache entries
    return {"status": "invalidated", "keys": keys.get("keys", [])}

# Service registry management
@get("/registry")
async def list_services():
    # In a real implementation, this would list registered services
    return {"services": []}

@post("/registry/update")
async def update_registry(service_info: dict):
    # In a real implementation, this would update service registry
    return {"status": "updated", "service": service_info.get("name")}

if __name__ == "__main__":
    svc.run(dev=True)