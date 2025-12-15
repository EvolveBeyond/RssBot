"""
Storage Demo Service - Example service demonstrating Evox data IO features
"""
from evox.core import service, get, post, data_io, data_intent

# Create service
svc = service("storage_demo_svc") \
    .port(8004) \
    .health("/health") \
    .build()

# Example data model with intent
@data_intent.cacheable(ttl="30m", consistency="eventual")
class Article:
    def __init__(self, id: int, title: str, content: str):
        self.id = id
        self.title = title
        self.content = content

# Read data endpoint
@get("/data/{key}")
async def read_data(key: str):
    # Read data with intent-aware behavior
    value = await data_io.read(key)
    return {"key": key, "value": value}

# Write data endpoint
@post("/data/{key}")
async def write_data(key: str, data: dict):
    # Write data with intent
    ttl = data.get("ttl", 300)  # Default 5 minutes
    await data_io.write(key, data.get("value"), ttl=ttl)
    return {"key": key, "status": "written"}

# List keys endpoint
@get("/keys/{pattern}")
async def list_keys(pattern: str = "*"):
    keys = await data_io.keys(pattern)
    return {"pattern": pattern, "keys": keys}

if __name__ == "__main__":
    svc.run(dev=True)