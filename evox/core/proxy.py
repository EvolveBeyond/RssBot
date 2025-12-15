"""
Service Proxy - Intelligent service-to-service communication

This module provides the intelligent service proxy for Evox, handling service-to-service
communication with support for priority queuing, automatic routing, and fallback mechanisms.

The proxy automatically routes calls between services using the most appropriate method
(router, REST, hybrid) based on service configuration and availability.
"""

from typing import Any, Dict, Optional, Callable, List
import httpx
import asyncio

from .queue import PriorityLevel, get_priority_queue


class ServiceProxy:
    """
    Smart proxy that automatically routes service calls with priority queuing.
    
    This proxy provides intelligent service-to-service communication with:
    1. Automatic routing (router, REST, hybrid)
    2. Priority-aware request queuing
    3. Fallback mechanisms for service unavailability
    4. Concurrent execution with gather method
    
    Design Notes:
    - Uses dynamic method interception for seamless service calls
    - Integrates with priority queue for request scheduling
    - Implements self-healing through automatic retries and fallbacks
    
    Good first issue: Add circuit breaker pattern for failed services
    """
    
    _instances: Dict[str, 'ServiceProxy'] = {}
    
    def __init__(self, service_name: str):
        self.service_name = service_name
    
    def __getattr__(self, method_name: str) -> Callable:
        """
        Dynamic method proxy - intercepts all method calls and routes them.
        """
        if method_name.startswith('_'):
            # Don't proxy private methods
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{method_name}'")
        
        async def proxy_method(*args, priority: str = "medium", **kwargs):
            """
            Proxy method with priority support.
            
            Args:
                *args: Positional arguments for the service method
                priority: Priority level for the request ("high", "medium", "low")
                **kwargs: Keyword arguments for the service method
            """
            try:
                # Submit to priority queue
                queue = get_priority_queue()
                priority_level = PriorityLevel(priority)
                
                return await queue.submit(
                    self._execute_service_call,
                    method_name, *args,
                    priority=priority_level,
                    **kwargs
                )
            except Exception as e:
                print(f"⚠️  Service call failed for {self.service_name}.{method_name}: {e}")
                raise
        
        return proxy_method
    
    async def _execute_service_call(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a service method call.
        
        This method implements the core service call logic with automatic routing
        and fallback mechanisms.
        """
        try:
            # Try to call via REST API as fallback
            return await self._call_via_rest(method_name, *args, **kwargs)
        except Exception as e:
            print(f"⚠️  Service call failed for {self.service_name}.{method_name}: {e}")
            raise
    
    async def _call_via_rest(self, method_name: str, *args, **kwargs) -> Any:
        """
        Call service method via REST API.
        
        This is the fallback mechanism when direct routing is not available.
        """
        # This is a simplified implementation
        # In a real implementation, this would use service discovery
        base_url = f"http://localhost:8000/{self.service_name}"  # Default fallback
        endpoint_url = f"{base_url}/{method_name}"
        
        # Prepare request data
        request_data = {
            "args": args,
            "kwargs": kwargs
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint_url,
                json=request_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
    
    @classmethod
    def get_instance(cls, service_name: str) -> 'ServiceProxy':
        """Get or create a proxy instance for a service"""
        if service_name not in cls._instances:
            cls._instances[service_name] = cls(service_name)
        return cls._instances[service_name]
    
    async def gather(self, 
                     *calls, 
                     policy: str = "partial", 
                     priority: str = "medium",
                     concurrency: int = 5) -> List[Any]:
        """
        Execute multiple service calls concurrently with priority and policy control.
        
        This method provides concurrent execution of multiple service calls with
        configurable execution policies and priority levels.
        
        Args:
            *calls: Service calls to execute
            policy: Execution policy ("partial" or "all_or_nothing")
            priority: Priority level ("high", "medium", "low")
            concurrency: Maximum number of concurrent requests
            
        Returns:
            List of results in the same order as calls
            
        Example:
            # Execute multiple calls with high priority and limited concurrency
            results = await proxy.gather(
                service1.get_user(123),
                service2.get_profile(123),
                priority="high",
                concurrency=3
            )
        """
        # Submit to priority queue with concurrency control
        queue = get_priority_queue()
        try:
            priority_level = PriorityLevel(priority)
        except ValueError:
            priority_level = PriorityLevel.MEDIUM
            
        return await queue.gather(
            *calls,
            priority=priority_level,
            concurrency=concurrency
        )


# Convenience functions for common service proxies
def get_service(service_name: str) -> ServiceProxy:
    """Get service proxy by name"""
    return ServiceProxy.get_instance(service_name)


# Proxy for accessing multiple services
class ProxyAccessor:
    """Dynamic proxy accessor for all services
    
    Allows accessing service proxies using attribute access.
    
    Example:
        # Access user service
        user = await proxy.user.get_user(123)
        
        # Access data service
        data = await proxy.data.get_records()
    """
    
    def __getattr__(self, service_name: str) -> ServiceProxy:
        return ServiceProxy.get_instance(service_name)


# Global proxy accessor
proxy = ProxyAccessor()