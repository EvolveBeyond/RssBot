"""
Data Intent Service - Unified data IO with intent-aware behavior
"""
import tomli
from evox.core import service, get, post, delete
from evox.core_services.data_intent_svc.adapters.memory import MemoryDataAdapter
from evox.core_services.data_intent_svc.adapters.sqlite import SqliteDataAdapter

# Load configuration
try:
    with open("config.toml", "rb") as f:
        config = tomli.load(f)
except FileNotFoundError:
    config = {"storage": {"backend": "memory"}}

# Set up data adapter based on configuration
data_backend = config.get("storage", {}).get("backend", "memory")
backend_config = config.get("storage", {})

if data_backend == "memory":
    data_adapter = MemoryDataAdapter()
elif data_backend == "sqlite":
    sqlite_url = backend_config.get("sqlite_url", "sqlite:///data_intent.db")
    data_adapter = SqliteDataAdapter(sqlite_url)
else:
    # Default to memory adapter
    data_adapter = MemoryDataAdapter()

# Create service
svc = service("data_intent_svc") \
    .port(config.get("port", 8001)) \
    .health("/health") \
    .build()

# Data IO instance
data_io = data_adapter

# Initialize data adapter on startup
@svc.on_startup
async def initialize_data():
    await data_io.initialize()

# Clean up data adapter on shutdown
@svc.on_shutdown
async def cleanup_data():
    await data_io.close()

# Endpoint to read data
@get("/read/{key}")
async def read_data(key: str):
    value = await data_io.read(key)
    return {"key": key, "value": value}

# Endpoint to write data
@post("/write/{key}")
async def write_data(key: str, value: dict):
    await data_io.write(key, value.get("value"), value.get("ttl"))
    return {"key": key, "status": "written"}

# Endpoint to delete data
@delete("/delete/{key}")
async def delete_data(key: str):
    await data_io.delete(key)
    return {"key": key, "status": "deleted"}

# Endpoint to list keys
@get("/keys/{pattern}")
async def list_keys(pattern: str = "*"):
    keys = await data_io.keys(pattern)
    return {"pattern": pattern, "keys": keys}

if __name__ == "__main__":
    svc.run(dev=True)