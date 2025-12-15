"""
Data IO Interface - Unified data input/output with intent-aware behavior

This module provides the core data IO interface for Evox, implementing intent-aware
data operations with support for caching, TTL, and aggressive fallback mechanisms.

The system automatically infers operational behavior (caching, consistency, storage)
based on declared data intents rather than hardcoded backends.
"""

import time
from typing import Any, Optional, Dict, List, Callable
from datetime import datetime, timedelta
import asyncio

from .config import get_config


class DataIOInterface:
    """Unified data IO interface with intent support and aggressive fallback
    
    This interface provides intent-aware data operations with support for:
    1. Time-to-live (TTL) based caching
    2. Aggressive fallback to serve stale data during outages
    3. Namespace isolation for different data contexts
    
    Design Notes:
    - Defaults to in-memory ephemeral storage for zero-dependency operation
    - Automatically handles intent-based behavior without explicit configuration
    - Supports graceful degradation with stale data serving
    
    Good first issue: Add support for custom serialization formats
    """
    
    def __init__(self):
        # In-memory storage for zero-dependency operation
        self._store: Dict[str, Dict[str, Any]] = {}
        self._namespace = ""
        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._stale_served = 0
    
    async def initialize(self):
        """Initialize the data IO backend"""
        # In a real implementation, this would connect to actual backends
        pass
    
    async def close(self):
        """Close the data IO backend"""
        # In a real implementation, this would close backend connections
        pass
    
    def namespace(self, ns: str):
        """Set the namespace for subsequent operations"""
        self._namespace = ns
        return self
    
    async def read(self, key: str, fallback: str = "normal", max_stale: str = None) -> Optional[Any]:
        """
        Read value by key with optional aggressive fallback.
        
        Args:
            key: The key to read
            fallback: Fallback strategy ("normal" or "aggressive")
            max_stale: Maximum time to serve stale data (e.g., "1h", "24h")
                      If None, uses configuration default
            
        Returns:
            The value if found, None otherwise
            
        Example:
            # Normal read
            user = await data_io.read("user:123")
            
            # Aggressive fallback allowing up to 24h stale data
            user = await data_io.read("user:123", fallback="aggressive", max_stale="24h")
        """
        # Use configuration default if max_stale not specified
        if max_stale is None:
            max_stale = get_config("caching.aggressive_fallback.max_stale_duration", "24h")
        
        full_key = f"{self._namespace}:{key}" if self._namespace else key
        
        # Check if key exists in store
        if full_key in self._store:
            entry = self._store[full_key]
            now = time.time()
            
            # Check if entry is still fresh
            if entry.get("expires", 0) > now:
                self._cache_hits += 1
                return entry["value"]
            
            # Entry is expired, check fallback strategy
            if fallback == "aggressive":
                # Parse max_stale duration
                max_stale_seconds = self._parse_duration(max_stale)
                # Check if entry is within max_stale window
                if entry.get("created", 0) + max_stale_seconds > now:
                    self._stale_served += 1
                    return entry["value"]
            
            # Either normal fallback or stale data beyond max_stale
            self._cache_misses += 1
            return None
        
        # Key not found
        self._cache_misses += 1
        return None
    
    async def write(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Write key-value pair with optional TTL.
        
        Args:
            key: The key to write
            value: The value to store
            ttl: Time-to-live in seconds (None for no expiration)
                 If None, uses configuration default
        """
        # Use configuration default if ttl not specified
        if ttl is None:
            ttl = get_config("caching.default_ttl", 300)
        
        full_key = f"{self._namespace}:{key}" if self._namespace else key
        now = time.time()
        
        entry = {
            "value": value,
            "created": now,
            "expires": now + ttl if ttl is not None else float('inf')
        }
        
        self._store[full_key] = entry
    
    async def delete(self, key: str) -> None:
        """Delete key"""
        full_key = f"{self._namespace}:{key}" if self._namespace else key
        if full_key in self._store:
            del self._store[full_key]
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        full_pattern = f"{self._namespace}:{pattern}" if self._namespace else pattern
        # Simple prefix matching for demonstration
        if "*" in pattern:
            prefix = pattern.replace("*", "")
            return [k for k in self._store.keys() if k.startswith(prefix)]
        return [k for k in self._store.keys() if pattern in k]
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "stale_served": self._stale_served,
            "hit_rate": self._cache_hits / max(1, self._cache_hits + self._cache_misses)
        }
    
    def _parse_duration(self, duration: str) -> int:
        """
        Parse duration string to seconds.
        
        Args:
            duration: Duration string (e.g., "1h", "30m", "24h")
            
        Returns:
            Duration in seconds
        """
        if not duration:
            return get_config("caching.default_ttl", 300)  # Default to 5 minutes
            
        duration = duration.lower()
        if duration.endswith('s'):
            return int(duration[:-1])
        elif duration.endswith('m'):
            return int(duration[:-1]) * 60
        elif duration.endswith('h'):
            return int(duration[:-1]) * 3600
        elif duration.endswith('d'):
            return int(duration[:-1]) * 86400
        else:
            # Assume seconds if no unit specified
            return int(duration)


# Global data IO instance
data_io = DataIOInterface()


# Data IO accessor for different namespaces
class DataIOAccessor:
    """Dynamic data IO accessor for different namespaces
    
    Allows accessing data IO with different namespaces using attribute access.
    
    Example:
        # Access user namespace
        user_data = await data_io.user.read("profile:123")
        
        # Access cache namespace
        cached_result = await data_io.cache.read("expensive_calculation")
    """
    
    def __getattr__(self, namespace: str) -> DataIOInterface:
        data_io_instance = DataIOInterface()
        data_io_instance.namespace(namespace)
        return data_io_instance


# Global data IO accessor
data_io = DataIOAccessor()


# Data Intent decorator for declaring intent
class DataIntent:
    """Data intent decorator for declaring operational behavior
    
    This decorator allows declaring operational behavior intentions for data,
    which the system automatically interprets to provide appropriate caching,
    consistency, and storage behaviors.
    
    Design Notes:
    - Intent declarations are explicit and declarative
    - System behavior is inferred from intents rather than hardcoded
    - Separates domain concerns from infrastructure concerns
    
    Good first issue: Add support for custom intent handlers
    """
    
    def __init__(self, **kwargs):
        self.intent_config = kwargs
    
    def __call__(self, cls):
        """Apply intent to a class"""
        cls._data_intent = self.intent_config
        return cls
    
    @staticmethod
    def cacheable(ttl: str = "1h", consistency: str = "eventual", fallback: str = "normal", max_stale: str = "24h", **kwargs):
        """Declare that data is cacheable
        
        Args:
            ttl: Time-to-live for cached data (e.g., "1h", "30m")
            consistency: Consistency level ("eventual", "strong")
            fallback: Fallback strategy ("normal", "aggressive")
            max_stale: Maximum stale duration for aggressive fallback
            **kwargs: Additional intent configuration
            
        Example:
            @data_intent.cacheable(ttl="1h", consistency="eventual", fallback="aggressive", max_stale="24h")
            class UserProfile:
                def __init__(self, user_id: int, name: str):
                    self.user_id = user_id
                    self.name = name
        """
        intent_config = {
            "cacheable": True,
            "ttl": ttl,
            "consistency": consistency,
            "fallback": fallback,
            "max_stale": max_stale,
            **kwargs
        }
        return DataIntent(**intent_config)
    
    @staticmethod
    def strong_consistency(**kwargs):
        """Declare that data requires strong consistency
        
        Args:
            **kwargs: Additional intent configuration
        """
        intent_config = {
            "consistency": "strong",
            **kwargs
        }
        return DataIntent(**intent_config)
    
    @staticmethod
    def eventual_ok(**kwargs):
        """Declare that eventual consistency is acceptable
        
        Args:
            **kwargs: Additional intent configuration
        """
        intent_config = {
            "eventual_ok": True,
            **kwargs
        }
        return DataIntent(**intent_config)


# Global data intent decorator
data_intent = DataIntent