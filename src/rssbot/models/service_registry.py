"""
Service Registry Models - Persistent service discovery and health tracking
"""
import enum
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class ConnectionMethod(str, enum.Enum):
    """Service connection methods with automatic fallback"""
    ROUTER = "router"      # in-process (fastest)
    REST = "rest"          # HTTP fallback
    DISABLED = "disabled"  # manually disabled


class BaseEntity(SQLModel):
    """Base entity with common fields"""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RegisteredService(BaseEntity, table=True):
    """Persistent service registry with health tracking and connection preferences"""
    __tablename__ = "registered_services"
    
    # Core identity
    name: str = Field(index=True, unique=True, description="Service name (e.g., 'ai_svc')")
    display_name: str = Field(description="Human-readable name")
    description: Optional[str] = Field(default=None, description="Service description")
    
    # Connection configuration
    connection_method: ConnectionMethod = Field(
        default=ConnectionMethod.ROUTER,
        description="Preferred connection method"
    )
    rest_url: Optional[str] = Field(
        default=None, 
        description="REST endpoint URL (http://localhost:8005)"
    )
    port: Optional[int] = Field(default=None, description="Service port")
    
    # Health and status
    is_active: bool = Field(default=True, description="Service enabled/disabled")
    last_health_check: Optional[datetime] = Field(
        default=None, 
        description="Last health check timestamp"
    )
    health_status: str = Field(
        default="unknown", 
        description="Health status: healthy, degraded, down, unknown"
    )
    
    # Discovery metadata
    auto_discovered: bool = Field(
        default=True, 
        description="Was this service auto-discovered?"
    )
    priority: int = Field(
        default=100, 
        description="Service priority (lower = higher priority)"
    )
    
    # Router availability
    has_router: bool = Field(
        default=False, 
        description="Service has router.py for in-process mounting"
    )
    router_path: Optional[str] = Field(
        default=None, 
        description="Python import path to router"
    )
    
    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        return self.health_status == "healthy" and self.is_active
    
    def get_effective_connection_method(self) -> ConnectionMethod:
        """Get the effective connection method based on health and availability"""
        if not self.is_active:
            return ConnectionMethod.DISABLED
        
        if self.connection_method == ConnectionMethod.DISABLED:
            return ConnectionMethod.DISABLED
        
        # If router is preferred and available, use it
        if (self.connection_method == ConnectionMethod.ROUTER and 
            self.has_router and 
            self.health_status in ["healthy", "unknown"]):
            return ConnectionMethod.ROUTER
        
        # Fallback to REST if available
        if self.rest_url and self.health_status in ["healthy", "degraded", "unknown"]:
            return ConnectionMethod.REST
        
        return ConnectionMethod.DISABLED
    
    def __str__(self) -> str:
        return f"RegisteredService(name={self.name}, method={self.connection_method}, status={self.health_status})"