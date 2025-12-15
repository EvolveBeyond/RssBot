"""
Service Builder - Main entry point for creating Evox services

This module provides the fluent API for building Evox services with minimal configuration.
It supports priority-aware request queuing and aggressive cache fallback mechanisms.
"""

import asyncio
import uvicorn
from typing import Optional, Callable, Any, Dict, List
from fastapi import FastAPI, APIRouter

from .queue import PriorityLevel, get_priority_queue


class ServiceBuilder:
    """
    Service Builder - Main entry point for creating Evox services
    
    Provides a fluent API for building services with minimal configuration.
    
    Design Notes:
    - Uses method chaining for clean, readable service definitions
    - Integrates with priority queue for request scheduling
    - Supports both direct endpoint registration and decorator-based definitions
    - Automatic health endpoint generation
    
    Good first issue: Add support for custom middleware registration
    """
    
    def __init__(self, name: str):
        self.name = name
        self._port = 8000
        self._health_endpoint = "/health"
        self.app = FastAPI(title=f"Evox Service - {name}")
        self.router = APIRouter()
        self.startup_handlers: List[Callable] = []
        self.shutdown_handlers: List[Callable] = []
        self.background_tasks: List[Dict[str, Any]] = []
        
        # Include router in app
        self.app.include_router(self.router)
        
        # Add default health endpoint
        @self.router.get(self._health_endpoint)
        async def health_check():
            return {"status": "healthy", "service": self.name}
    
    def port(self, port: int):
        """Set the service port"""
        self._port = port
        return self
    
    def health(self, endpoint: str = "/health"):
        """Set the health check endpoint"""
        self._health_endpoint = endpoint
        return self
    
    def build(self):
        """Build and finalize the service"""
        return self
    
    def endpoint(self, path: str, methods: List[str] = ["GET"], **kwargs):
        """
        Decorator for defining service endpoints
        
        Args:
            path: Endpoint path
            methods: HTTP methods
            **kwargs: Additional endpoint configuration including priority settings
        """
        def decorator(func: Callable):
            # Extract priority from kwargs if present
            priority_str = kwargs.pop('priority', 'medium')
            try:
                priority = PriorityLevel(priority_str)
            except ValueError:
                priority = PriorityLevel.MEDIUM  # Default to medium priority
            
            # Store priority information for later use
            func._evox_priority = priority
            
            self.router.add_api_route(
                path=path,
                endpoint=func,
                methods=methods,
                **kwargs
            )
            return func
        return decorator
    
    def group(self, prefix: str):
        """Create a grouped router with a prefix"""
        group_router = APIRouter(prefix=prefix)
        self.app.include_router(group_router)
        return group_router
    
    def on_startup(self, func: Callable):
        """Register a startup handler"""
        self.startup_handlers.append(func)
        self.app.on_event("startup")(func)
        return func
    
    def on_shutdown(self, func: Callable):
        """Register a shutdown handler"""
        self.shutdown_handlers.append(func)
        self.app.on_event("shutdown")(func)
        return func
    
    def background_task(self, interval: int):
        """Decorator for defining background tasks"""
        def decorator(func: Callable):
            self.background_tasks.append({
                "func": func,
                "interval": interval
            })
            return func
        return decorator
    
    async def gather(self, 
                     *requests,
                     priority: str = "medium",
                     concurrency: int = 5) -> List[Any]:
        """
        Execute multiple requests concurrently with priority and concurrency control.
        
        This method integrates with the priority-aware queue system to execute
        multiple requests with controlled concurrency and priority levels.
        
        Args:
            *requests: Request coroutines to execute
            priority: Priority level for all requests ("high", "medium", "low")
            concurrency: Maximum number of concurrent requests
            
        Returns:
            List of results in the same order as requests
            
        Example:
            results = await service.gather(
                service1.call(), 
                service2.call(),
                priority="high",
                concurrency=3
            )
        """
        try:
            priority_level = PriorityLevel(priority)
        except ValueError:
            priority_level = PriorityLevel.MEDIUM
            
        queue = get_priority_queue()
        return await queue.gather(*requests, priority=priority_level, concurrency=concurrency)
    
    def run(self, dev: bool = False):
        """Run the service"""
        if dev:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=self._port,
                reload=True,
                log_level="debug"
            )
        else:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=self._port,
                log_level="info"
            )


# Convenience functions
def service(name: str) -> ServiceBuilder:
    """Create a new service builder"""
    return ServiceBuilder(name)


# Decorators for endpoints
def get(path: str, **kwargs):
    """GET endpoint decorator with priority support"""
    def decorator(func: Callable):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["GET"],
            "kwargs": kwargs
        }
        return func
    return decorator


def post(path: str, **kwargs):
    """POST endpoint decorator with priority support"""
    def decorator(func: Callable):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["POST"],
            "kwargs": kwargs
        }
        return func
    return decorator


def put(path: str, **kwargs):
    """PUT endpoint decorator with priority support"""
    def decorator(func: Callable):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["PUT"],
            "kwargs": kwargs
        }
        return func
    return decorator


def delete(path: str, **kwargs):
    """DELETE endpoint decorator with priority support"""
    def decorator(func: Callable):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["DELETE"],
            "kwargs": kwargs
        }
        return func
    return decorator


def endpoint(path: str = None, methods: List[str] = ["GET"], **kwargs):
    """
    Generic endpoint decorator for internal/non-route handlers
    
    Args:
        path: Endpoint path (optional for internal handlers)
        methods: HTTP methods
        **kwargs: Additional endpoint configuration including priority settings
    """
    def decorator(func: Callable):
        func._evox_endpoint = {
            "path": path,
            "methods": methods,
            "kwargs": kwargs
        }
        return func
    return decorator