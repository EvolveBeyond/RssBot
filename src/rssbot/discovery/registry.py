"""
Service Registry Manager - Syncs discovered services with database
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

from ..models.service_registry import RegisteredService, ConnectionMethod
from ..core.config import get_config
from ..core.exceptions import DiscoveryError
from .scanner import ServiceScanner, ServiceInfo


class ServiceRegistryManager:
    """Manages the persistent service registry in database"""
    
    def __init__(self, db_session_factory=None):
        self.config = get_config()
        self.scanner = ServiceScanner()
        self._db_session_factory = db_session_factory
    
    def set_db_session_factory(self, session_factory):
        """Set database session factory (injected by controller)"""
        self._db_session_factory = session_factory
    
    def _get_session(self):
        """Get database session"""
        if not self._db_session_factory:
            raise DiscoveryError("Database session factory not configured")
        return self._db_session_factory()
    
    async def sync_discovered_services(self) -> Dict[str, Any]:
        """
        Discover services and sync with database registry.
        
        Returns:
            Summary of sync operation
        """
        print("🔄 Starting service discovery and registry sync...")
        
        # Discover services from filesystem
        discovered_services = self.scanner.discover_services()
        
        # Sync with database
        with self._get_session() as session:
            sync_results = self._sync_with_database(session, discovered_services)
            session.commit()
        
        print(f"✅ Service registry sync complete: {sync_results}")
        return sync_results
    
    def _sync_with_database(self, session: Session, discovered: List[ServiceInfo]) -> Dict[str, Any]:
        """
        Sync discovered services with database registry.
        
        Args:
            session: Database session
            discovered: List of discovered services
            
        Returns:
            Sync operation summary
        """
        # Get existing services from database
        existing_services = {
            service.name: service 
            for service in session.exec(select(RegisteredService)).all()
        }
        
        discovered_names = {service.name for service in discovered}
        existing_names = set(existing_services.keys())
        
        # Track changes
        created = []
        updated = []
        marked_inactive = []
        
        # Process discovered services
        for service_info in discovered:
            if service_info.name in existing_services:
                # Update existing service
                service = existing_services[service_info.name]
                updated_fields = self._update_service_from_discovery(service, service_info)
                if updated_fields:
                    service.updated_at = datetime.utcnow()
                    updated.append((service_info.name, updated_fields))
            else:
                # Create new service
                service = self._create_service_from_discovery(service_info)
                session.add(service)
                created.append(service_info.name)
        
        # Mark missing services as inactive (but don't delete)
        missing_services = existing_names - discovered_names
        for service_name in missing_services:
            service = existing_services[service_name]
            if service.is_active and service.auto_discovered:
                service.is_active = False
                service.updated_at = datetime.utcnow()
                marked_inactive.append(service_name)
        
        # Reactivate services that came back
        reactivated = []
        for service_info in discovered:
            if service_info.name in existing_services:
                service = existing_services[service_info.name]
                if not service.is_active and service.auto_discovered:
                    service.is_active = True
                    service.updated_at = datetime.utcnow()
                    reactivated.append(service_info.name)
        
        return {
            "total_discovered": len(discovered),
            "created": created,
            "updated": updated,
            "marked_inactive": marked_inactive,
            "reactivated": reactivated,
            "total_registered": len(discovered_names | existing_names)
        }
    
    def _create_service_from_discovery(self, service_info: ServiceInfo) -> RegisteredService:
        """Create new RegisteredService from ServiceInfo"""
        return RegisteredService(
            name=service_info.name,
            display_name=service_info.display_name,
            description=service_info.description,
            connection_method=ConnectionMethod.ROUTER if service_info.has_router else ConnectionMethod.REST,
            rest_url=self.config.get_service_url(service_info.name),
            port=service_info.port,
            is_active=True,
            health_status="unknown",
            auto_discovered=True,
            priority=100,
            has_router=service_info.has_router,
            router_path=service_info.router_path
        )
    
    def _update_service_from_discovery(self, service: RegisteredService, service_info: ServiceInfo) -> List[str]:
        """Update existing service with discovered information"""
        updated_fields = []
        
        # Update display name if not manually customized
        if service.auto_discovered and service.display_name != service_info.display_name:
            service.display_name = service_info.display_name
            updated_fields.append("display_name")
        
        # Update description
        if service.description != service_info.description:
            service.description = service_info.description
            updated_fields.append("description")
        
        # Update router availability
        if service.has_router != service_info.has_router:
            service.has_router = service_info.has_router
            updated_fields.append("has_router")
        
        if service.router_path != service_info.router_path:
            service.router_path = service_info.router_path
            updated_fields.append("router_path")
        
        # Update port if service is auto-discovered
        if service.auto_discovered and service.port != service_info.port:
            service.port = service_info.port
            updated_fields.append("port")
        
        # Update REST URL if not manually configured
        if service.auto_discovered:
            expected_url = self.config.get_service_url(service_info.name)
            if service.rest_url != expected_url:
                service.rest_url = expected_url
                updated_fields.append("rest_url")
        
        return updated_fields
    
    async def get_active_services(self) -> List[RegisteredService]:
        """Get all active services from registry"""
        with self._get_session() as session:
            services = session.exec(
                select(RegisteredService)
                .where(RegisteredService.is_active == True)
                .order_by(RegisteredService.priority, RegisteredService.name)
            ).all()
            return list(services)
    
    async def get_service_by_name(self, name: str) -> Optional[RegisteredService]:
        """Get service by name"""
        with self._get_session() as session:
            service = session.exec(
                select(RegisteredService)
                .where(RegisteredService.name == name)
            ).first()
            return service
    
    async def update_service_config(self, name: str, **kwargs) -> bool:
        """Update service configuration"""
        with self._get_session() as session:
            service = session.exec(
                select(RegisteredService)
                .where(RegisteredService.name == name)
            ).first()
            
            if not service:
                return False
            
            # Update allowed fields
            allowed_fields = [
                'connection_method', 'rest_url', 'is_active', 
                'priority', 'display_name', 'description'
            ]
            
            updated = False
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(service, field):
                    setattr(service, field, value)
                    updated = True
            
            if updated:
                service.updated_at = datetime.utcnow()
                # Mark as manually configured
                service.auto_discovered = False
                session.commit()
            
            return updated
    
    async def update_health_status(self, name: str, status: str, timestamp: datetime = None) -> bool:
        """Update service health status"""
        with self._get_session() as session:
            service = session.exec(
                select(RegisteredService)
                .where(RegisteredService.name == name)
            ).first()
            
            if not service:
                return False
            
            service.health_status = status
            service.last_health_check = timestamp or datetime.utcnow()
            session.commit()
            return True
    
    def get_router_services(self) -> Dict[str, str]:
        """
        Get services that should be mounted as routers.
        
        Returns:
            Dict mapping service names to their router import paths
        """
        with self._get_session() as session:
            services = session.exec(
                select(RegisteredService)
                .where(
                    RegisteredService.is_active == True,
                    RegisteredService.has_router == True,
                    RegisteredService.connection_method == ConnectionMethod.ROUTER
                )
            ).all()
            
            return {
                service.name: service.router_path 
                for service in services 
                if service.router_path
            }