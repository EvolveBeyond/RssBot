"""
Hybrid Storage Adapter - Combined backend for Evox storage
"""
from typing import Any, Optional, List
from evox.core.storage import StorageBackend
from .memory import MemoryStorageBackend
from .redis import RedisStorageAdapter


class HybridStorageAdapter(StorageBackend):
    """Hybrid storage backend adapter combining multiple backends"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.memory_backend = MemoryStorageBackend()
        self.redis_backend = RedisStorageAdapter(redis_url)
        self.initialized = False
    
    async def initialize(self):
        """Initialize all backends"""
        try:
            await self.redis_backend.initialize()
            self.initialized = True
            print("✅ Hybrid storage adapter initialized successfully")
        except Exception as e:
            print(f"⚠️  Hybrid storage adapter initialization warning: {e}")
            # Fall back to memory only
            self.initialized = True
    
    async def close(self):
        """Close all backends"""
        try:
            await self.redis_backend.close()
        except Exception as e:
            print(f"Error closing Redis backend: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key from hybrid storage"""
        # Try memory first (fastest)
        value = await self.memory_backend.get(key)
        if value is not None:
            return value
        
        # Try Redis if available
        if self.initialized:
            try:
                value = await self.redis_backend.get(key)
                if value is not None:
                    # Cache in memory for future fast access
                    await self.memory_backend.set(key, value)
                    return value
            except Exception as e:
                print(f"Error getting key {key} from Redis: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set key-value pair in hybrid storage"""
        # Set in memory first
        await self.memory_backend.set(key, value, ttl)
        
        # Set in Redis if available
        if self.initialized:
            try:
                await self.redis_backend.set(key, value, ttl)
            except Exception as e:
                print(f"Error setting key {key} in Redis: {e}")
    
    async def delete(self, key: str) -> None:
        """Delete key from hybrid storage"""
        # Delete from memory
        await self.memory_backend.delete(key)
        
        # Delete from Redis if available
        if self.initialized:
            try:
                await self.redis_backend.delete(key)
            except Exception as e:
                print(f"Error deleting key {key} from Redis: {e}")
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern from hybrid storage"""
        # Get from memory first
        memory_keys = await self.memory_backend.keys(pattern)
        
        # Get from Redis if available
        redis_keys = []
        if self.initialized:
            try:
                redis_keys = await self.redis_backend.keys(pattern)
            except Exception as e:
                print(f"Error getting keys with pattern {pattern} from Redis: {e}")
        
        # Combine and deduplicate
        all_keys = list(set(memory_keys + redis_keys))
        return all_keys