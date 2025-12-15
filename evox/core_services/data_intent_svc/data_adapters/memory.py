"""
Memory Data Adapter - In-memory data adapter for Evox data IO
"""
from typing import Any, Optional, List, Dict
import time


class MemoryDataAdapter:
    """In-memory data adapter"""
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """Initialize memory data adapter (no-op)"""
        pass
    
    async def close(self):
        """Close memory data adapter (no-op)"""
        pass
    
    async def read(self, key: str) -> Optional[Any]:
        """Read value by key from memory"""
        if key in self._store:
            item = self._store[key]
            # Check TTL
            if item.get('expires_at') and time.time() > item['expires_at']:
                del self._store[key]
                return None
            return item.get('value')
        return None
    
    async def write(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Write key-value pair in memory"""
        expires_at = None
        if ttl:
            expires_at = time.time() + ttl
        self._store[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': time.time()
        }
    
    async def delete(self, key: str) -> None:
        """Delete key from memory"""
        self._store.pop(key, None)
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern from memory"""
        # Simple pattern matching (just prefix for now)
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self._store.keys() if k.startswith(prefix)]
        return [k for k in self._store.keys() if k == pattern]