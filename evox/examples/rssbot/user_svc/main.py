"""
User Service - Example service demonstrating Evox data intent features
"""
from evox.core import service, get, post, data_io, data_intent

# Create service
svc = service("user_svc") \
    .port(8003) \
    .health("/health") \
    .build()

# Declare a data intent for user profiles
@data_intent.cacheable(ttl="1h", consistency="eventual")
class UserProfile:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

# Example GET endpoint
@get("/users/{user_id}")
async def get_user(user_id: int):
    # Read user data with intent-aware behavior
    user = await data_io.read(f"user:{user_id}")
    if user:
        return user
    
    # Mock user data
    user = {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }
    
    # Write with intent (cacheable for 1 hour)
    await data_io.write(f"user:{user_id}", user, ttl=3600)
    return user

# Example POST endpoint with data intent
@post("/users")
async def create_user(user_data: dict):
    user_id = user_data.get("id", 1)
    user = {
        "id": user_id,
        "name": user_data.get("name", "Unknown"),
        "email": user_data.get("email", "unknown@example.com")
    }
    
    # Write user data with intent
    await data_io.write(f"user:{user_id}", user, ttl=3600)
    return {"status": "created", "user": user}

if __name__ == "__main__":
    svc.run(dev=True)