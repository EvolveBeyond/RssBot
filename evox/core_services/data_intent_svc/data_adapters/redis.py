"""
Redis Storage Adapter - Redis backend for Evox storage
"""
import redis.asyncio as redis
from typing import Any, Optional, List
from evox.core.storage import StorageBackend


class RedisStorageAdapter(StorageBackend):
    """Redis storage backend adapter"""
    
    def __init__(self, url: str = "redis://localhost:6379/0"):
        self.url = url
        self.client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        self.client = redis.from_url(self.url)
        try:
            await self.client.ping()
            print("✅ Redis storage adapter connected successfully")
        except Exception as e:
            print(f"❌ Redis storage adapter connection failed: {e}")
            self.client = None
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key from Redis"""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        
        try:
            value = await self.client.get(key)
            if value:
                # In a real implementation, we would deserialize the value
                return value.decode() if isinstance(value, bytes) else value
            return None
        except Exception as e:
            print(f"Error getting key {key} from Redis: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set key-value pair in Redis with optional TTL"""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        
        try:
            # In a real implementation, we would serialize the value
            serialized_value = str(value) if not isinstance(value, str) else value
            if ttl:
                await self.client.setex(key, ttl, serialized_value)
            else:
                await self.client.set(key, serialized_value)
        except Exception as e:
            print(f"Error setting key {key} in Redis: {e}")
    
    async def delete(self, key: str) -> None:
        """Delete key from Redis"""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        
        try:
            await self.client.delete(key)
        except Exception as e:
            print(f"Error deleting key {key} from Redis: {e}")
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern from Redis"""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        
        try:
            keys = await self.client.keys(pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            print(f"Error getting keys with pattern {pattern} from Redis: {e}")
            return []