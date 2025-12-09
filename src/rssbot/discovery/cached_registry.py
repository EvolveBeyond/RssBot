"""
Cached Service Registry - Redis-backed per-service connection management

This module replaces the global LOCAL_ROUTER_MODE with per-service connection
decisions cached in Redis for ultra-fast lookup with database fallback.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import logging

import redis.asyncio as redis
from sqlmodel import Session, select

from ..models.service_registry import RegisteredService, ConnectionMethod
from ..core.config import get_config
from ..core.exceptions import DiscoveryError
from .registry import ServiceRegistryManager

logger = logging.getLogger(__name__)


class CachedServiceRegistry:
    """
    High-performance service registry with Redis caching.
    
    Architecture:
    - Redis as primary cache (sub-millisecond lookups)
    - Database as persistent source of truth
    - Per-service connection method decisions
    - Automatic fallback and self-healing
    """
    
    CACHE_PREFIX = "rssbot:service:"
    CACHE_TTL = 300  # 5 minutes
    HEALTH_CACHE_TTL = 60  # 1 minute for health status
    
    def __init__(self, db_session_factory: Optional[callable] = None) -> None:
        """
        Initialize the cached service registry.
        
        Args:
            db_session_factory: Optional database session factory function
        """
        self.config: Config = get_config()
        self.registry_manager: ServiceRegistryManager = ServiceRegistryManager(db_session_factory)
        self._redis: Optional[redis.Redis] = None
        self._redis_available: bool = False
        
    async def initialize(self) -> None:
        """
        Initialize Redis connection.
        
        Attempts to connect to Redis and sets availability flag.
        Falls back gracefully to database-only mode if Redis is unavailable.
        """
        try:
            self._redis = redis.from_url(self.config.redis_url)
            await self._redis.ping()
            self._redis_available = True
            logger.info("✅ Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable, falling back to database: {e}")
            self._redis_available = False
    
    async def close(self) -> None:
        """
        Close Redis connection and cleanup resources.
        
        Should be called during application shutdown.
        """
        if self._redis:
            await self._redis.close()
    
    def set_db_session_factory(self, session_factory: callable) -> None:
        """
        Set database session factory (injected by controller).
        
        Args:
            session_factory: Function that returns database session instances
        """
        self.registry_manager.set_db_session_factory(session_factory)
    
    # === Core Service Decision Logic ===
    
    async def should_use_router(self, service_name: str) -> bool:
        """
        PRIMARY METHOD: Decide if service should use router mode.
        
        This replaces all usage of LOCAL_ROUTER_MODE throughout the codebase.
        Each service makes independent decisions based on:
        1. Service-specific connection_method preference
        2. Current health status  
        3. Router availability
        
        Args:
            service_name: Name of the service (e.g., 'ai_svc')
            
        Returns:
            True if service should be mounted as router, False for REST
            
        Raises:
            ValueError: If service_name is empty or invalid
        """
        if not service_name or not isinstance(service_name, str):
            raise ValueError("service_name must be a non-empty string")
            
        connection_method = await self.get_effective_connection_method(service_name)
        return connection_method == ConnectionMethod.ROUTER
    
    async def get_effective_connection_method(self, service_name: str) -> ConnectionMethod:
        """
        Get the effective connection method for a service after health checks.
        
        Logic:
        - DISABLED -> always disabled
        - ROUTER -> router if available and healthy, otherwise REST
        - REST -> always REST
        - HYBRID -> router preferred, fallback to REST
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            Effective connection method for the service
            
        Raises:
            ValueError: If service_name is invalid
        """
        if not service_name or not isinstance(service_name, str):
            raise ValueError("service_name must be a non-empty string")
            
        # Try Redis cache first
        if self._redis_available:
            try:
                cached = await self._get_cached_connection_method(service_name)
                if cached is not None:
                    return cached
            except Exception as e:
                logger.warning(f"Redis cache error for {service_name}: {e}")
        
        # Fallback to database
        service = await self.registry_manager.get_service_by_name(service_name)
        if not service:
            logger.warning(f"Service {service_name} not found in registry, defaulting to REST")
            return ConnectionMethod.REST
        
        effective_method = service.get_effective_connection_method()
        
        # Cache the result
        if self._redis_available:
            try:
                await self._cache_connection_method(service_name, effective_method)
            except Exception as e:
                logger.warning(f"Failed to cache connection method for {service_name}: {e}")
        
        return effective_method
    
    async def get_services_for_router_mounting(self) -> Dict[str, str]:
        """
        Get all services that should be mounted as routers in controller.
        
        Returns:
            Dict mapping service names to their router import paths
        """
        services = await self.registry_manager.get_active_services()
        router_services = {}
        
        for service in services:
            if await self.should_use_router(service.name):
                if service.router_path:
                    router_services[service.name] = service.router_path
                else:
                    logger.warning(f"Service {service.name} should use router but no router_path found")
        
        logger.info(f"🔧 Services for router mounting: {list(router_services.keys())}")
        return router_services
    
    # === Cache Management ===
    
    async def _get_cached_connection_method(self, service_name: str) -> Optional[ConnectionMethod]:
        """
        Get cached connection method from Redis.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Cached connection method or None if not found/invalid
        """
        if not self._redis:
            return None
            
        key = f"{self.CACHE_PREFIX}{service_name}:method"
        cached_value = await self._redis.get(key)
        
        if cached_value:
            try:
                return ConnectionMethod(cached_value.decode())
            except ValueError:
                # Invalid cached value, remove it
                await self._redis.delete(key)
                return None
        
        return None
    
    async def _cache_connection_method(self, service_name: str, method: ConnectionMethod) -> None:
        """
        Cache connection method in Redis.
        
        Args:
            service_name: Name of the service
            method: Connection method to cache
        """
        if not self._redis:
            return
            
        key = f"{self.CACHE_PREFIX}{service_name}:method"
        await self._redis.setex(key, self.CACHE_TTL, method.value)
    
    async def invalidate_service_cache(self, service_name: str):
        """Invalidate all cached data for a service"""
        if not self._redis:
            return
            
        pattern = f"{self.CACHE_PREFIX}{service_name}:*"
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)
            logger.info(f"🗑️ Invalidated cache for service: {service_name}")
    
    async def invalidate_all_cache(self):
        """Invalidate all service caches"""
        if not self._redis:
            return
            
        pattern = f"{self.CACHE_PREFIX}*"
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)
            logger.info("🗑️ Invalidated all service caches")
    
    # === Health Status Caching ===
    
    async def update_service_health_cached(self, service_name: str, status: str, timestamp: datetime = None):
        """Update service health in both cache and database"""
        timestamp = timestamp or datetime.utcnow()
        
        # Update database
        await self.registry_manager.update_health_status(service_name, status, timestamp)
        
        # Update cache
        if self._redis_available:
            try:
                health_key = f"{self.CACHE_PREFIX}{service_name}:health"
                health_data = {
                    "status": status,
                    "timestamp": timestamp.isoformat()
                }
                await self._redis.setex(
                    health_key, 
                    self.HEALTH_CACHE_TTL, 
                    json.dumps(health_data)
                )
                
                # Invalidate connection method cache to trigger recalculation
                method_key = f"{self.CACHE_PREFIX}{service_name}:method"
                await self._redis.delete(method_key)
                
            except Exception as e:
                logger.warning(f"Failed to cache health for {service_name}: {e}")
    
    # === Service Management ===
    
    async def update_service_connection_method(self, service_name: str, method: ConnectionMethod) -> bool:
        """Update a service's connection method preference"""
        success = await self.registry_manager.update_service_config(
            service_name,
            connection_method=method
        )
        
        if success:
            await self.invalidate_service_cache(service_name)
            logger.info(f"🔄 Updated {service_name} connection method to {method.value}")
        
        return success
    
    async def bulk_set_connection_methods(self, service_methods: Dict[str, ConnectionMethod]):
        """Bulk update connection methods for multiple services"""
        results = {}
        for service_name, method in service_methods.items():
            results[service_name] = await self.update_service_connection_method(service_name, method)
        
        logger.info(f"📋 Bulk updated connection methods: {results}")
        return results
    
    # === Migration Helpers ===
    
    async def migrate_from_global_router_mode(self) -> Dict[str, str]:
        """
        Migrate from global LOCAL_ROUTER_MODE to per-service decisions.
        
        This method helps transition existing deployments:
        - If LOCAL_ROUTER_MODE=true, set all services with routers to ROUTER
        - If LOCAL_ROUTER_MODE=false, set all services to REST
        - Services without routers always use REST
        """
        global_router_mode = self.config.local_router_mode
        services = await self.registry_manager.get_active_services()
        
        migration_plan = {}
        updates = {}
        
        for service in services:
            if global_router_mode and service.has_router:
                # Global router mode + service has router -> use router
                new_method = ConnectionMethod.ROUTER
                updates[service.name] = new_method
                migration_plan[service.name] = f"ROUTER (global=true, has_router=true)"
            else:
                # No global router mode OR service has no router -> use REST
                new_method = ConnectionMethod.REST
                updates[service.name] = new_method
                migration_plan[service.name] = f"REST (global={global_router_mode}, has_router={service.has_router})"
        
        # Apply updates
        if updates:
            await self.bulk_set_connection_methods(updates)
        
        logger.info(f"🔄 Migration completed: {len(updates)} services updated")
        return migration_plan
    
    # === Cache Statistics ===
    
    async def get_cache_stats(self) -> Dict[str, any]:
        """Get cache performance statistics"""
        if not self._redis_available:
            return {"cache_available": False}
        
        try:
            info = await self._redis.info("stats")
            pattern_keys = await self._redis.keys(f"{self.CACHE_PREFIX}*")
            
            return {
                "cache_available": True,
                "redis_info": {
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown")
                },
                "service_cache_keys": len(pattern_keys),
                "sample_keys": [key.decode() for key in pattern_keys[:10]]
            }
        except Exception as e:
            return {"cache_available": False, "error": str(e)}


# === Global Cache Instance ===

_cached_registry: Optional[CachedServiceRegistry] = None


async def get_cached_registry() -> CachedServiceRegistry:
    """Get global cached registry instance"""
    global _cached_registry
    if _cached_registry is None:
        _cached_registry = CachedServiceRegistry()
        await _cached_registry.initialize()
    return _cached_registry


async def should_service_use_router(service_name: str) -> bool:
    """
    GLOBAL CONVENIENCE FUNCTION
    
    Use this anywhere in the codebase instead of checking LOCAL_ROUTER_MODE.
    
    Examples:
        # Old way (OBSOLETE):
        # if config.local_router_mode:
        
        # New way (RECOMMENDED):
        if await should_service_use_router("ai_svc"):
            # Mount as router
        else:
            # Use REST call
    """
    registry = await get_cached_registry()
    return await registry.should_use_router(service_name)