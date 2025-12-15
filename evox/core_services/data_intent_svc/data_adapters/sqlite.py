"""
SQLite Data Adapter - SQLite data adapter for Evox data IO
"""
from typing import Any, Optional, List
import sqlite3
import time
import aiosqlite


class SqliteDataAdapter:
    """SQLite data adapter"""
    
    def __init__(self, url: str = "sqlite:///data_intent.db"):
        self.url = url
        self.db: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """Initialize SQLite connection"""
        try:
            self.db = await aiosqlite.connect(self.url)
            # Create tables if they don't exist
            await self._create_tables()
            print("✅ SQLite data adapter connected successfully")
        except Exception as e:
            print(f"❌ SQLite data adapter connection failed: {e}")
            self.db = None
    
    async def close(self):
        """Close SQLite connection"""
        if self.db:
            await self.db.close()
    
    async def _create_tables(self):
        """Create required tables"""
        if not self.db:
            raise RuntimeError("SQLite database not initialized")
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS evox_data (
                key TEXT PRIMARY KEY,
                value TEXT,
                ttl INTEGER,
                created_at REAL DEFAULT (julianday('now')),
                expires_at REAL
            )
        """)
        await self.db.commit()
    
    async def read(self, key: str) -> Optional[Any]:
        """Read value by key from SQLite"""
        if not self.db:
            raise RuntimeError("SQLite database not initialized")
        
        try:
            cursor = await self.db.execute(
                "SELECT value, expires_at FROM evox_data WHERE key = ?",
                (key,)
            )
            row = await cursor.fetchone()
            if row:
                value, expires_at = row
                # Check TTL
                if expires_at and time.time() > expires_at:
                    await self.db.execute(
                        "DELETE FROM evox_data WHERE key = ?",
                        (key,)
                    )
                    await self.db.commit()
                    return None
                return value
            return None
        except Exception as e:
            print(f"Error reading key {key} from SQLite: {e}")
            return None
    
    async def write(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Write key-value pair in SQLite"""
        if not self.db:
            raise RuntimeError("SQLite database not initialized")
        
        try:
            # Serialize the value
            serialized_value = str(value) if not isinstance(value, str) else value
            
            # Calculate expiration time
            expires_at = None
            if ttl:
                expires_at = time.time() + ttl
            
            await self.db.execute("""
                INSERT OR REPLACE INTO evox_data (key, value, ttl, expires_at)
                VALUES (?, ?, ?, ?)
            """, (key, serialized_value, ttl, expires_at))
            await self.db.commit()
        except Exception as e:
            print(f"Error writing key {key} to SQLite: {e}")
    
    async def delete(self, key: str) -> None:
        """Delete key from SQLite"""
        if not self.db:
            raise RuntimeError("SQLite database not initialized")
        
        try:
            await self.db.execute(
                "DELETE FROM evox_data WHERE key = ?",
                (key,)
            )
            await self.db.commit()
        except Exception as e:
            print(f"Error deleting key {key} from SQLite: {e}")
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern from SQLite"""
        if not self.db:
            raise RuntimeError("SQLite database not initialized")
        
        try:
            # Simple pattern matching (just prefix for now)
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                cursor = await self.db.execute(
                    "SELECT key FROM evox_data WHERE key LIKE ?",
                    (f"{prefix}%",)
                )
            else:
                cursor = await self.db.execute(
                    "SELECT key FROM evox_data WHERE key = ?",
                    (pattern,)
                )
            
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            print(f"Error getting keys with pattern {pattern} from SQLite: {e}")
            return []