"""
PostgreSQL Storage Adapter - PostgreSQL backend for Evox storage
"""
import asyncpg
from typing import Any, Optional, List
from evox.core.storage import StorageBackend


class PostgresqlStorageAdapter(StorageBackend):
    """PostgreSQL storage backend adapter"""
    
    def __init__(self, url: str = "postgresql://user:password@localhost/db"):
        self.url = url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self.pool = await asyncpg.create_pool(self.url)
            # Create tables if they don't exist
            await self._create_tables()
            print("✅ PostgreSQL storage adapter connected successfully")
        except Exception as e:
            print(f"❌ PostgreSQL storage adapter connection failed: {e}")
            self.pool = None
    
    async def close(self):
        """Close PostgreSQL connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def _create_tables(self):
        """Create required tables"""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS evox_storage (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    ttl INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key from PostgreSQL"""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT value FROM evox_storage WHERE key = $1",
                    key
                )
                if row:
                    return row['value']
                return None
        except Exception as e:
            print(f"Error getting key {key} from PostgreSQL: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set key-value pair in PostgreSQL with optional TTL"""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        try:
            # In a real implementation, we would serialize the value
            serialized_value = str(value) if not isinstance(value, str) else value
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO evox_storage (key, value, ttl)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (key) DO UPDATE
                    SET value = $2, ttl = $3
                """, key, serialized_value, ttl)
        except Exception as e:
            print(f"Error setting key {key} in PostgreSQL: {e}")
    
    async def delete(self, key: str) -> None:
        """Delete key from PostgreSQL"""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM evox_storage WHERE key = $1",
                    key
                )
        except Exception as e:
            print(f"Error deleting key {key} from PostgreSQL: {e}")
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern from PostgreSQL"""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        try:
            # Simple pattern matching (just prefix for now)
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                query = "SELECT key FROM evox_storage WHERE key LIKE $1"
                params = [f"{prefix}%"]
            else:
                query = "SELECT key FROM evox_storage WHERE key = $1"
                params = [pattern]
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [row['key'] for row in rows]
        except Exception as e:
            print(f"Error getting keys with pattern {pattern} from PostgreSQL: {e}")
            return []