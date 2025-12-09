"""
Migration utilities for transitioning from global LOCAL_ROUTER_MODE to per-service decisions.

This module provides convenience functions to replace LOCAL_ROUTER_MODE checks
throughout the existing codebase with minimal code changes.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def should_use_router_for_service(service_name: str) -> bool:
    """
    GLOBAL REPLACEMENT FUNCTION for LOCAL_ROUTER_MODE checks.
    
    Use this function everywhere in the codebase instead of:
    - os.getenv("LOCAL_ROUTER_MODE", "false").lower() == "true"
    - config.local_router_mode
    
    Examples:
        # Old way (OBSOLETE):
        if config.local_router_mode:
            # mount as router
        
        # New way (RECOMMENDED):
        if await should_use_router_for_service("ai_svc"):
            # mount as router
    
    Args:
        service_name: Name of the service (e.g., 'ai_svc')
        
    Returns:
        True if service should use router mode, False for REST mode
    """
    try:
        # Import here to avoid circular dependencies
        from ..discovery.cached_registry import get_cached_registry
        
        cached_registry = await get_cached_registry()
        return await cached_registry.should_use_router(service_name)
        
    except Exception as e:
        logger.warning(f"Failed to get cached registry decision for {service_name}: {e}")
        
        # Fallback to legacy LOCAL_ROUTER_MODE for backward compatibility
        legacy_mode = os.getenv("LOCAL_ROUTER_MODE", "false").lower() == "true"
        logger.warning(f"Falling back to legacy LOCAL_ROUTER_MODE={legacy_mode} for {service_name}")
        
        return legacy_mode


def get_legacy_router_mode() -> bool:
    """
    Get the legacy LOCAL_ROUTER_MODE setting.
    
    This is used for backward compatibility during migration.
    
    Returns:
        True if LOCAL_ROUTER_MODE=true, False otherwise
    """
    return os.getenv("LOCAL_ROUTER_MODE", "false").lower() == "true"


async def migrate_service_from_global_mode(service_name: str, has_router: bool = True) -> str:
    """
    Migrate a single service from global mode to per-service decision.
    
    Args:
        service_name: Name of the service
        has_router: Whether the service has a router.py file
        
    Returns:
        The connection method that was set
    """
    try:
        from ..discovery.cached_registry import get_cached_registry
        from ..models.service_registry import ConnectionMethod
        
        cached_registry = await get_cached_registry()
        legacy_mode = get_legacy_router_mode()
        
        # Determine new connection method based on legacy setting
        if legacy_mode and has_router:
            new_method = ConnectionMethod.ROUTER
        else:
            new_method = ConnectionMethod.REST
        
        # Update the service
        success = await cached_registry.update_service_connection_method(service_name, new_method)
        
        if success:
            logger.info(f"✅ Migrated {service_name}: {new_method.value}")
            return new_method.value
        else:
            logger.warning(f"❌ Failed to migrate {service_name}")
            return "migration_failed"
            
    except Exception as e:
        logger.error(f"Migration error for {service_name}: {e}")
        return "error"


class RouterModeContext:
    """
    Context manager for testing different router modes.
    
    Usage:
        async with RouterModeContext("ai_svc", "router"):
            # Service will use router mode in this block
            result = await some_service_call()
    """
    
    def __init__(self, service_name: str, temp_method: str):
        self.service_name = service_name
        self.temp_method = temp_method
        self.original_method: Optional[str] = None
    
    async def __aenter__(self):
        try:
            from ..discovery.cached_registry import get_cached_registry
            from ..models.service_registry import ConnectionMethod
            
            cached_registry = await get_cached_registry()
            
            # Store original method
            original = await cached_registry.get_effective_connection_method(self.service_name)
            self.original_method = original.value
            
            # Set temporary method
            new_method = ConnectionMethod(self.temp_method)
            await cached_registry.update_service_connection_method(self.service_name, new_method)
            
            logger.info(f"🔧 Temporarily set {self.service_name} to {self.temp_method}")
            
        except Exception as e:
            logger.error(f"Failed to set temporary connection method: {e}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.original_method:
            try:
                from ..discovery.cached_registry import get_cached_registry
                from ..models.service_registry import ConnectionMethod
                
                cached_registry = await get_cached_registry()
                original = ConnectionMethod(self.original_method)
                await cached_registry.update_service_connection_method(self.service_name, original)
                
                logger.info(f"🔙 Restored {self.service_name} to {self.original_method}")
                
            except Exception as e:
                logger.error(f"Failed to restore original connection method: {e}")


# === Convenience Functions for Common Usage Patterns ===

async def should_ai_use_router() -> bool:
    """Check if AI service should use router mode"""
    return await should_use_router_for_service("ai_svc")


async def should_formatting_use_router() -> bool:
    """Check if formatting service should use router mode"""
    return await should_use_router_for_service("formatting_svc")


async def should_user_use_router() -> bool:
    """Check if user service should use router mode"""
    return await should_use_router_for_service("user_svc")


async def should_db_use_router() -> bool:
    """Check if database service should use router mode"""
    return await should_use_router_for_service("db_svc")


async def should_bot_use_router() -> bool:
    """Check if bot service should use router mode"""
    return await should_use_router_for_service("bot_svc")


async def bulk_check_router_services() -> dict:
    """
    Check router mode for all common services at once.
    
    Returns:
        Dict mapping service names to their router decisions
    """
    services = [
        "db_svc", "bot_svc", "user_svc", "ai_svc", 
        "formatting_svc", "channel_mgr_svc", "payment_svc", "miniapp_svc"
    ]
    
    results = {}
    for service in services:
        try:
            results[service] = await should_use_router_for_service(service)
        except Exception as e:
            logger.warning(f"Failed to check {service}: {e}")
            results[service] = False  # Safe fallback to REST
    
    return results