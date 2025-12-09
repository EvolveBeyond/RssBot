"""
Health Checker - Background task for monitoring service health
"""
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..core.config import get_config
from ..core.security import get_service_headers
from ..core.exceptions import HealthCheckError
from ..models.service_registry import RegisteredService, ConnectionMethod
from .registry import ServiceRegistryManager


@dataclass
class HealthStatus:
    """Service health check result"""
    service_name: str
    status: str  # healthy, degraded, down
    response_time: Optional[float]
    error_message: Optional[str]
    timestamp: datetime
    method_used: str  # router or rest


class HealthChecker:
    """Monitors service health and updates registry"""
    
    def __init__(self, registry_manager: ServiceRegistryManager):
        self.config = get_config()
        self.registry = registry_manager
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self):
        """Start background health monitoring"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        print(f"🩺 Health monitoring started (interval: {self.config.service_discovery_interval}s)")
    
    async def stop_monitoring(self):
        """Stop background health monitoring"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("🩺 Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self.check_all_services()
                await asyncio.sleep(self.config.service_discovery_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️  Health monitoring error: {e}")
                await asyncio.sleep(10)  # Short delay before retrying
    
    async def check_all_services(self) -> Dict[str, HealthStatus]:
        """Check health of all registered services"""
        services = await self.registry.get_active_services()
        
        if not services:
            return {}
        
        print(f"🩺 Checking health of {len(services)} services...")
        
        # Run health checks concurrently
        tasks = [
            self.check_service_health(service) 
            for service in services
        ]
        
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update registry
        results = {}
        for service, result in zip(services, health_results):
            if isinstance(result, Exception):
                # Health check failed with exception
                health_status = HealthStatus(
                    service_name=service.name,
                    status="down",
                    response_time=None,
                    error_message=str(result),
                    timestamp=datetime.utcnow(),
                    method_used="unknown"
                )
            else:
                health_status = result
            
            # Update registry
            await self.registry.update_health_status(
                service.name, 
                health_status.status, 
                health_status.timestamp
            )
            
            results[service.name] = health_status
            
            # Log status changes
            if service.health_status != health_status.status:
                print(f"🔄 Service {service.name}: {service.health_status} → {health_status.status}")
        
        return results
    
    async def check_service_health(self, service: RegisteredService) -> HealthStatus:
        """
        Check health of a single service.
        
        Args:
            service: Service to check
            
        Returns:
            Health status result
        """
        effective_method = service.get_effective_connection_method()
        
        if effective_method == ConnectionMethod.DISABLED:
            return HealthStatus(
                service_name=service.name,
                status="down",
                response_time=None,
                error_message="Service disabled",
                timestamp=datetime.utcnow(),
                method_used="disabled"
            )
        
        # Try router method first (if available and preferred)
        if effective_method == ConnectionMethod.ROUTER:
            try:
                return await self._check_router_health(service)
            except Exception:
                # Router failed, fall back to REST if available
                if service.rest_url:
                    return await self._check_rest_health(service, fallback=True)
                else:
                    raise
        
        # Use REST method
        return await self._check_rest_health(service)
    
    async def _check_router_health(self, service: RegisteredService) -> HealthStatus:
        """Check health via router (in-process)"""
        start_time = datetime.utcnow()
        
        try:
            # For router-based services, we assume they're healthy if they're mounted
            # This is a simplified check - in production you might want more sophisticated checks
            
            # TODO: Implement actual router health check
            # This could involve checking if the router is properly mounted in controller
            # For now, we'll return healthy for services with routers
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthStatus(
                service_name=service.name,
                status="healthy",
                response_time=response_time,
                error_message=None,
                timestamp=datetime.utcnow(),
                method_used="router"
            )
            
        except Exception as e:
            return HealthStatus(
                service_name=service.name,
                status="down",
                response_time=None,
                error_message=str(e),
                timestamp=datetime.utcnow(),
                method_used="router"
            )
    
    async def _check_rest_health(self, service: RegisteredService, fallback: bool = False) -> HealthStatus:
        """Check health via REST endpoint"""
        if not service.rest_url:
            raise HealthCheckError(f"No REST URL configured for service {service.name}")
        
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try /health endpoint first
                health_url = f"{service.rest_url.rstrip('/')}/health"
                
                response = await client.get(
                    health_url,
                    headers=get_service_headers()
                )
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    # Check response content
                    try:
                        data = response.json()
                        if data.get("status") == "healthy":
                            status = "healthy"
                        else:
                            status = "degraded"
                    except:
                        status = "degraded"  # Response not JSON
                else:
                    status = "degraded"  # Non-200 response
                
                return HealthStatus(
                    service_name=service.name,
                    status=status,
                    response_time=response_time,
                    error_message=None,
                    timestamp=datetime.utcnow(),
                    method_used="rest" + (" (fallback)" if fallback else "")
                )
                
        except httpx.TimeoutException:
            return HealthStatus(
                service_name=service.name,
                status="down",
                response_time=None,
                error_message="Health check timeout",
                timestamp=datetime.utcnow(),
                method_used="rest" + (" (fallback)" if fallback else "")
            )
        except Exception as e:
            return HealthStatus(
                service_name=service.name,
                status="down",
                response_time=None,
                error_message=str(e),
                timestamp=datetime.utcnow(),
                method_used="rest" + (" (fallback)" if fallback else "")
            )
    
    async def force_health_check(self, service_name: str) -> HealthStatus:
        """Force immediate health check for specific service"""
        service = await self.registry.get_service_by_name(service_name)
        if not service:
            raise HealthCheckError(f"Service not found: {service_name}")
        
        return await self.check_service_health(service)