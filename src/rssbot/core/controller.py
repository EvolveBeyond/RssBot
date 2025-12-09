"""
Core Controller - The heart of the per-service hybrid microservices platform

This module contains the main orchestration logic that was previously 
scattered in services/controller_svc/. Now it's part of the core platform.
"""
import asyncio
import importlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import get_config, Config
from .security import get_service_headers
from ..discovery.cached_registry import get_cached_registry, CachedServiceRegistry
from ..models.service_registry import ConnectionMethod, RegisteredService

logger = logging.getLogger(__name__)


class ControllerCore:
    """
    Core controller logic - the brain of the hybrid microservices platform.
    
    This class handles:
    - Service discovery and registration
    - Dynamic router mounting based on per-service decisions
    - Health monitoring and cache management
    - Admin operations and migrations
    
    Attributes:
        config: Platform configuration instance
        cached_registry: Redis-backed service registry
        mounted_services: Dictionary of mounted service information
        app: FastAPI application instance
    """
    
    def __init__(self) -> None:
        """Initialize the controller core with default configuration."""
        self.config: Config = get_config()
        self.cached_registry: Optional[CachedServiceRegistry] = None
        self.mounted_services: Dict[str, Dict[str, Any]] = {}
        self.app: Optional[FastAPI] = None
    
    async def initialize(self) -> FastAPI:
        """
        Initialize the controller and create FastAPI app.
        
        Returns:
            Configured FastAPI application instance
            
        Raises:
            RuntimeError: If initialization fails
        """
        logger.info("🚀 Initializing Core Controller...")
        
        try:
            # Initialize cached registry
            self.cached_registry = await get_cached_registry()
            logger.info(f"📋 Service registry initialized (Cache: {self.cached_registry._redis_available})")
            
            # Create FastAPI app
            self.app = self._create_app()
            
            # Discover and mount services
            await self._discover_and_mount_services()
            
            # Start background health monitoring
            asyncio.create_task(self._health_monitor_loop())
            
            logger.info("✅ Core Controller ready")
            logger.info(f"🔧 Cache available: {self.cached_registry._redis_available}")
            logger.info(f"📊 Mounted services: {list(self.mounted_services.keys())}")
            
            return self.app
            
        except Exception as e:
            logger.error(f"❌ Controller initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize controller: {e}") from e
    
    def _create_app(self) -> FastAPI:
        """
        Create and configure the FastAPI application.
        
        Returns:
            Configured FastAPI application with middleware and routes
        """
        app = FastAPI(
            title="RssBot Core Controller",
            description="Per-service hybrid microservices orchestration platform",
            version="2.0.0",
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register core routes
        self._register_core_routes(app)
        
        return app
    
    def _register_core_routes(self, app: FastAPI) -> None:
        """
        Register core controller API routes.
        
        Args:
            app: FastAPI application instance to register routes on
        """
        
        @app.get("/health")
        async def health_check() -> Dict[str, Any]:
            """
            Core platform health check endpoint.
            
            Returns:
                Dictionary containing platform health information
            """
            cache_stats: Dict[str, Any] = {}
            if self.cached_registry:
                cache_stats = await self.cached_registry.get_cache_stats()
            
            return {
                "status": "healthy",
                "platform": "rssbot_hybrid_microservices",
                "architecture": "per_service_core_controller",
                "version": "2.0.0",
                "cache_stats": cache_stats,
                "mounted_services": len(self.mounted_services),
                "core_location": "src/rssbot/core/controller.py"
            }
        
        @app.get("/services")
        async def list_all_services():
            """List all services with their connection methods and status"""
            if not self.cached_registry:
                raise HTTPException(status_code=500, detail="Registry not initialized")
            
            services = await self.cached_registry.registry_manager.get_active_services()
            result = []
            
            for service in services:
                connection_method = await self.cached_registry.get_effective_connection_method(service.name)
                is_mounted = service.name in self.mounted_services
                
                result.append({
                    "name": service.name,
                    "display_name": service.display_name,
                    "connection_method": connection_method.value,
                    "health_status": service.health_status,
                    "is_mounted": is_mounted,
                    "has_router": service.has_router,
                    "last_health_check": service.last_health_check.isoformat() if service.last_health_check else None
                })
            
            return {
                "services": result,
                "total_services": len(result),
                "mounted_count": len(self.mounted_services)
            }
        
        @app.post("/services/{service_name}/connection-method")
        async def update_connection_method(
            service_name: str,
            update: Dict[str, str]
        ):
            """Update service connection method"""
            if not self.cached_registry:
                raise HTTPException(status_code=500, detail="Registry not initialized")
            
            try:
                method = ConnectionMethod(update["connection_method"])
            except (KeyError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid connection_method. Must be one of: {[m.value for m in ConnectionMethod]}"
                )
            
            success = await self.cached_registry.update_service_connection_method(service_name, method)
            if not success:
                raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
            
            return {
                "success": True,
                "service": service_name,
                "new_method": method.value,
                "message": "Connection method updated. Restart to apply mounting changes."
            }
        
        @app.post("/admin/remount-services")
        async def remount_services():
            """Re-discover and remount services based on current configuration"""
            await self._discover_and_mount_services()
            return {
                "success": True,
                "mounted_services": list(self.mounted_services.keys()),
                "message": "Services remounted successfully"
            }
        
        @app.post("/admin/migrate-from-legacy")
        async def migrate_from_legacy():
            """Migrate from legacy LOCAL_ROUTER_MODE configuration"""
            if not self.cached_registry:
                raise HTTPException(status_code=500, detail="Registry not initialized")
            
            migration_plan = await self.cached_registry.migrate_from_global_router_mode()
            return {
                "success": True,
                "migration_plan": migration_plan,
                "message": "Migration completed"
            }
        
        @app.delete("/admin/cache")
        async def clear_cache():
            """Clear all service caches"""
            if not self.cached_registry:
                raise HTTPException(status_code=500, detail="Registry not initialized")
            
            await self.cached_registry.invalidate_all_cache()
            return {"success": True, "message": "All caches cleared"}
    
    async def _discover_and_mount_services(self) -> None:
        """
        Discover services and mount those configured for router mode.
        
        This method syncs with the service registry, determines which services
        should be mounted as routers, and performs the mounting operation.
        
        Raises:
            RuntimeError: If registry is not initialized
        """
        if not self.cached_registry:
            logger.error("❌ Registry not initialized")
            raise RuntimeError("Cached registry not initialized")
        
        logger.info("🔍 Discovering and mounting services...")
        
        try:
            # Clear existing mounts
            self.mounted_services.clear()
            
            # Sync services with database
            await self.cached_registry.registry_manager.sync_discovered_services()
            
            # Get services that should be mounted as routers
            router_services: Dict[str, str] = await self.cached_registry.get_services_for_router_mounting()
            
            if not router_services:
                logger.info("ℹ️  No services configured for router mounting")
                return
            
            # Mount each service
            mounted_count = 0
            for service_name, router_path in router_services.items():
                try:
                    await self._mount_service(service_name, router_path)
                    mounted_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to mount {service_name}: {e}")
                    # Update health status
                    if self.cached_registry:
                        await self.cached_registry.update_service_health_cached(
                            service_name, "degraded", datetime.utcnow()
                        )
            
            logger.info(f"🎉 Mounted {mounted_count} services as routers")
            
            # Run migration if legacy config detected
            if self.config.local_router_mode is not None:
                logger.info("🔄 Running legacy migration...")
                await self.cached_registry.migrate_from_global_router_mode()
                
        except Exception as e:
            logger.error(f"❌ Service discovery and mounting failed: {e}")
            raise
    
    async def _mount_service(self, service_name: str, router_path: str) -> None:
        """
        Mount a single service as a router.
        
        Args:
            service_name: Name of the service to mount (e.g., 'ai_svc')
            router_path: Python import path to the router module
            
        Raises:
            ImportError: If the router module cannot be imported
            AttributeError: If the router module has no 'router' export
            RuntimeError: If the FastAPI app is not initialized
        """
        if not self.app:
            raise RuntimeError("FastAPI app not initialized")
            
        logger.info(f"🔧 Mounting {service_name} (path: {router_path})")
        
        try:
            # Import the service router module
            service_module = importlib.import_module(router_path)
            
            if not hasattr(service_module, 'router'):
                raise AttributeError(f"Module {router_path} has no 'router' export")
            
            # Mount the router
            router = service_module.router
            prefix = f"/{service_name.replace('_svc', '')}"
            
            self.app.include_router(router, prefix=prefix, tags=[service_name])
            
            # Initialize service if needed
            if hasattr(service_module, 'initialize_service'):
                initialize_func = getattr(service_module, 'initialize_service')
                if asyncio.iscoroutinefunction(initialize_func):
                    await initialize_func()
                else:
                    initialize_func()
            
            # Track mounted service
            self.mounted_services[service_name] = {
                'module': service_module,
                'prefix': prefix,
                'router': router,
                'mounted_at': datetime.utcnow()
            }
            
            logger.info(f"  ✅ {service_name} mounted at {prefix}")
            
        except Exception as e:
            logger.error(f"  ❌ {service_name} mount failed: {e}")
            raise
    
    async def _health_monitor_loop(self) -> None:
        """
        Background health monitoring for mounted services.
        
        This method runs continuously to monitor the health of all mounted
        services and update their status in the cache.
        """
        while True:
            try:
                await self._check_mounted_services_health()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _check_mounted_services_health(self) -> None:
        """
        Check health of all mounted services.
        
        For each mounted service, this method:
        1. Checks if the module is still accessible
        2. Calls service-specific health check if available
        3. Updates the health status in the cache
        """
        for service_name, service_info in self.mounted_services.items():
            try:
                # Basic health check - ensure module is still importable
                module = service_info['module']
                status = 'unknown'
                
                if hasattr(module, 'health_check'):
                    # Call service-specific health check
                    health_func = getattr(module, 'health_check')
                    
                    if asyncio.iscoroutinefunction(health_func):
                        health_result = await health_func()
                    else:
                        health_result = health_func()
                    
                    if isinstance(health_result, dict):
                        status = health_result.get('status', 'unknown')
                    else:
                        status = 'healthy'  # Assume healthy if function returns non-dict
                else:
                    # Basic check - module exists and is accessible
                    status = 'healthy'
                
                # Update cache
                if self.cached_registry:
                    await self.cached_registry.update_service_health_cached(
                        service_name, status, datetime.utcnow()
                    )
                
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                if self.cached_registry:
                    await self.cached_registry.update_service_health_cached(
                        service_name, 'degraded', datetime.utcnow()
                    )


# Global controller instance
_controller_core: Optional[ControllerCore] = None


async def get_controller_core() -> ControllerCore:
    """
    Get the global controller core instance.
    
    Returns:
        The global ControllerCore singleton instance
    """
    global _controller_core
    if _controller_core is None:
        _controller_core = ControllerCore()
    return _controller_core


async def create_platform_app() -> FastAPI:
    """
    Create the complete platform FastAPI application.
    
    This is the main entry point for the RssBot platform.
    Call this from your main service runner.
    
    Returns:
        Configured FastAPI application ready to serve
        
    Raises:
        RuntimeError: If platform initialization fails
    """
    try:
        controller = await get_controller_core()
        return await controller.initialize()
    except Exception as e:
        logger.error(f"❌ Platform app creation failed: {e}")
        raise RuntimeError(f"Failed to create platform app: {e}") from e