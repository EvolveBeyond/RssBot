"""
Smart Hybrid Proxy - Automatically routes calls via cached per-service decisions
"""
import asyncio
import httpx
import importlib
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from ..core.config import get_config
from ..core.security import get_service_headers
from ..core.exceptions import ServiceUnavailableError, ServiceError
from ..models.service_registry import RegisteredService, ConnectionMethod


class ServiceProxy:
    """
    Smart proxy that automatically routes service calls using cached per-service decisions.
    
    NEW ARCHITECTURE: Uses cached registry for ultra-fast per-service routing decisions.
    
    Usage:
        ai = ServiceProxy("ai_svc")
        result = await ai.summarize(text="Hello world")
        
    The proxy will:
    1. Check cached registry for service's preferred connection method
    2. Route to router (in-process) if service is configured for router mode
    3. Route to REST if service is configured for REST mode
    4. Automatic fallback with health-based decisions
    5. Never crash the platform - graceful error handling
    """
    
    _router_cache: Dict[str, Any] = {}
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.config = get_config()
    
    async def _get_cached_registry(self):
        """Get the cached registry instance"""
        # Import here to avoid circular imports
        from .cached_registry import get_cached_registry
        return await get_cached_registry()
    
    def __getattr__(self, method_name: str) -> Callable:
        """
        Dynamic method proxy - intercepts all method calls and routes them.
        
        Args:
            method_name: Name of the method being called
            
        Returns:
            Async function that will execute the service call
        """
        if method_name.startswith('_'):
            # Don't proxy private methods
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{method_name}'")
        
        async def proxy_method(*args, **kwargs):
            return await self._execute_service_call(method_name, *args, **kwargs)
        
        return proxy_method
    
    async def _execute_service_call(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a service method call using cached per-service decisions.
        
        Args:
            method_name: Name of the method to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from the service call
            
        Raises:
            ServiceUnavailableError: If service is not available via any method
        """
        try:
            cached_registry = await self._get_cached_registry()
        except Exception as e:
            raise ServiceError(f"Cannot access cached registry: {e}", self.service_name)
        
        # Get service configuration
        service = await cached_registry.registry_manager.get_service_by_name(self.service_name)
        if not service or not service.is_active:
            raise ServiceUnavailableError(self.service_name, ["registry_lookup"])
        
        # Use cached decision for connection method
        should_use_router = await cached_registry.should_use_router(self.service_name)
        effective_method = await cached_registry.get_effective_connection_method(self.service_name)
        
        attempted_methods = []
        last_error = None
        
        # Try router method first (if cached decision says to use router)
        if should_use_router and service.has_router:
            try:
                return await self._call_via_router(service, method_name, *args, **kwargs)
            except Exception as e:
                attempted_methods.append("router")
                last_error = str(e)
                print(f"⚠️  Router call failed for {self.service_name}.{method_name}: {e}")
                
                # Update health status in cache
                await cached_registry.update_service_health_cached(
                    self.service_name, 
                    "degraded", 
                    datetime.utcnow()
                )
        
        # Try REST method (if not disabled and has URL)
        if service.rest_url and effective_method != ConnectionMethod.DISABLED:
            try:
                return await self._call_via_rest(service, method_name, *args, **kwargs)
            except Exception as e:
                attempted_methods.append("rest")
                last_error = str(e)
                print(f"⚠️  REST call failed for {self.service_name}.{method_name}: {e}")
                
                # Update health status in cache
                await cached_registry.update_service_health_cached(
                    self.service_name, 
                    "down", 
                    datetime.utcnow()
                )
        
        # All methods failed
        raise ServiceUnavailableError(self.service_name, attempted_methods)
    
    async def _call_via_router(self, service: RegisteredService, method_name: str, *args, **kwargs) -> Any:
        """
        Call service method via in-process router.
        
        Args:
            service: Service configuration
            method_name: Method to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from the router call
        """
        # Get or import the router module
        router_module = self._get_router_module(service)
        
        # Look for the method on the router module
        if hasattr(router_module, method_name):
            method = getattr(router_module, method_name)
            
            # Call the method
            if asyncio.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)
        
        # Method not found on router - this might be a REST-only method
        raise AttributeError(f"Method '{method_name}' not found on router for {service.name}")
    
    async def _call_via_rest(self, service: RegisteredService, method_name: str, *args, **kwargs) -> Any:
        """
        Call service method via REST API.
        
        Args:
            service: Service configuration
            method_name: Method to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from the REST call
        """
        # Convert method call to REST endpoint
        endpoint_url = f"{service.rest_url.rstrip('/')}/{method_name}"
        
        # Prepare request data
        request_data = {
            "args": args,
            "kwargs": kwargs
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint_url,
                json=request_data,
                headers=get_service_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise AttributeError(f"Method '{method_name}' not found on service {service.name}")
            else:
                response.raise_for_status()
    
    def _get_router_module(self, service: RegisteredService) -> Any:
        """
        Get the router module for a service, with caching.
        
        Args:
            service: Service configuration
            
        Returns:
            Router module object
        """
        # Check cache first
        if service.name in ServiceProxy._router_cache:
            return ServiceProxy._router_cache[service.name]
        
        if not service.router_path:
            raise ServiceError(f"No router path configured for service {service.name}")
        
        try:
            # Import the router module
            router_module = importlib.import_module(service.router_path)
            
            # Cache the module
            ServiceProxy._router_cache[service.name] = router_module
            
            return router_module
            
        except ImportError as e:
            raise ServiceError(f"Cannot import router for {service.name}: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the service.
        
        Returns:
            Health check results
        """
        if not ServiceProxy._registry:
            return {"status": "error", "message": "Registry not initialized"}
        
        service = await ServiceProxy._registry.get_service_by_name(self.service_name)
        if not service:
            return {"status": "error", "message": "Service not found in registry"}
        
        effective_method = service.get_effective_connection_method()
        
        if effective_method == ConnectionMethod.DISABLED:
            return {"status": "disabled", "message": "Service is disabled"}
        
        # Try health check via preferred method
        try:
            if effective_method == ConnectionMethod.ROUTER and service.has_router:
                # For router services, check if module is importable
                try:
                    self._get_router_module(service)
                    return {
                        "status": "healthy", 
                        "method": "router",
                        "service": self.service_name
                    }
                except Exception as e:
                    return {
                        "status": "unhealthy", 
                        "method": "router", 
                        "error": str(e)
                    }
            
            elif service.rest_url:
                # Try REST health endpoint
                async with httpx.AsyncClient(timeout=10.0) as client:
                    health_url = f"{service.rest_url.rstrip('/')}/health"
                    response = await client.get(
                        health_url,
                        headers=get_service_headers()
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "status": data.get("status", "healthy"),
                            "method": "rest",
                            "service": self.service_name,
                            "url": health_url
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "method": "rest",
                            "status_code": response.status_code
                        }
            
        except Exception as e:
            return {
                "status": "error",
                "method": effective_method.value,
                "error": str(e)
            }
        
        return {"status": "unknown", "message": "No available connection method"}
    
    def __repr__(self) -> str:
        return f"ServiceProxy(service='{self.service_name}')"


# Convenience functions for common service proxies
def get_ai_service() -> ServiceProxy:
    """Get AI service proxy"""
    return ServiceProxy("ai_svc")


def get_formatting_service() -> ServiceProxy:
    """Get formatting service proxy"""
    return ServiceProxy("formatting_svc")


def get_user_service() -> ServiceProxy:
    """Get user service proxy"""
    return ServiceProxy("user_svc")


def get_bot_service() -> ServiceProxy:
    """Get bot service proxy"""
    return ServiceProxy("bot_svc")


def get_db_service() -> ServiceProxy:
    """Get database service proxy"""
    return ServiceProxy("db_svc")


def get_channel_mgr_service() -> ServiceProxy:
    """Get channel manager service proxy"""
    return ServiceProxy("channel_mgr_svc")


def get_payment_service() -> ServiceProxy:
    """Get payment service proxy"""
    return ServiceProxy("payment_svc")


def get_miniapp_service() -> ServiceProxy:
    """Get miniapp service proxy"""
    return ServiceProxy("miniapp_svc")