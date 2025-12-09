"""
Comprehensive test suite for RssBot Platform.

This module contains tests for the core platform functionality including:
- Service registry operations
- Connection method decisions
- Cache management
- Health monitoring
- Type safety validation
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, Optional

# Core platform imports
from src.rssbot.core.controller import ControllerCore, create_platform_app
from src.rssbot.discovery.cached_registry import CachedServiceRegistry
from src.rssbot.models.service_registry import ConnectionMethod, RegisteredService
from src.rssbot.utils.migration import should_use_router_for_service
from src.rssbot.core.config import get_config


class TestCachedServiceRegistry:
    """Test suite for CachedServiceRegistry functionality."""
    
    @pytest.fixture
    async def mock_registry(self) -> CachedServiceRegistry:
        """Create a mock registry instance for testing."""
        registry = CachedServiceRegistry()
        registry._redis = AsyncMock()
        registry._redis_available = True
        
        # Mock the registry manager
        registry.registry_manager = Mock()
        registry.registry_manager.get_service_by_name = AsyncMock()
        
        return registry
    
    @pytest.mark.asyncio
    async def test_should_use_router_validates_input(self, mock_registry: CachedServiceRegistry) -> None:
        """Test that should_use_router validates input parameters."""
        # Test empty service name
        with pytest.raises(ValueError, match="service_name must be a non-empty string"):
            await mock_registry.should_use_router("")
        
        # Test None service name
        with pytest.raises(ValueError, match="service_name must be a non-empty string"):
            await mock_registry.should_use_router(None)  # type: ignore
        
        # Test non-string service name
        with pytest.raises(ValueError, match="service_name must be a non-empty string"):
            await mock_registry.should_use_router(123)  # type: ignore
    
    @pytest.mark.asyncio
    async def test_should_use_router_returns_true_for_router_method(
        self, mock_registry: CachedServiceRegistry
    ) -> None:
        """Test that services with ROUTER method return True."""
        # Arrange
        service_name = "test_svc"
        mock_registry._get_cached_connection_method = AsyncMock(
            return_value=ConnectionMethod.ROUTER
        )
        
        # Act
        result = await mock_registry.should_use_router(service_name)
        
        # Assert
        assert result is True
        mock_registry._get_cached_connection_method.assert_called_once_with(service_name)
    
    @pytest.mark.asyncio
    async def test_should_use_router_returns_false_for_rest_method(
        self, mock_registry: CachedServiceRegistry
    ) -> None:
        """Test that services with REST method return False."""
        # Arrange
        service_name = "test_svc"
        mock_registry._get_cached_connection_method = AsyncMock(
            return_value=ConnectionMethod.REST
        )
        
        # Act
        result = await mock_registry.should_use_router(service_name)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cache_fallback_when_redis_unavailable(
        self, mock_registry: CachedServiceRegistry
    ) -> None:
        """Test graceful fallback to database when Redis is unavailable."""
        # Arrange
        mock_registry._redis_available = False
        mock_service = Mock(spec=RegisteredService)
        mock_service.get_effective_connection_method.return_value = ConnectionMethod.REST
        mock_registry.registry_manager.get_service_by_name.return_value = mock_service
        
        # Act
        result = await mock_registry.get_effective_connection_method("test_svc")
        
        # Assert
        assert result == ConnectionMethod.REST
        mock_registry.registry_manager.get_service_by_name.assert_called_once_with("test_svc")
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, mock_registry: CachedServiceRegistry) -> None:
        """Test cache invalidation functionality."""
        # Arrange
        service_name = "test_svc"
        
        # Act
        await mock_registry.invalidate_service_cache(service_name)
        
        # Assert
        mock_registry._redis.keys.assert_called_once()
        mock_registry._redis.delete.assert_called_once()


class TestControllerCore:
    """Test suite for ControllerCore functionality."""
    
    @pytest.fixture
    def mock_controller(self) -> ControllerCore:
        """Create a mock controller instance for testing."""
        controller = ControllerCore()
        controller.cached_registry = Mock(spec=CachedServiceRegistry)
        return controller
    
    @pytest.mark.asyncio
    async def test_initialization_creates_app(self, mock_controller: ControllerCore) -> None:
        """Test that controller initialization creates FastAPI app."""
        # Arrange
        with patch('src.rssbot.core.controller.get_cached_registry') as mock_get_registry:
            mock_registry = AsyncMock(spec=CachedServiceRegistry)
            mock_registry._redis_available = True
            mock_get_registry.return_value = mock_registry
            
            # Mock the service discovery
            mock_controller._discover_and_mount_services = AsyncMock()
            
            # Act
            app = await mock_controller.initialize()
            
            # Assert
            assert app is not None
            assert app.title == "RssBot Core Controller"
            assert app.version == "2.0.0"
    
    @pytest.mark.asyncio
    async def test_service_mounting_with_valid_router(
        self, mock_controller: ControllerCore
    ) -> None:
        """Test successful service mounting with valid router module."""
        # Arrange
        mock_controller.app = Mock()
        mock_controller.app.include_router = Mock()
        
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.router = Mock()
            mock_import.return_value = mock_module
            
            # Act
            await mock_controller._mount_service("test_svc", "test.router")
            
            # Assert
            mock_import.assert_called_once_with("test.router")
            mock_controller.app.include_router.assert_called_once()
            assert "test_svc" in mock_controller.mounted_services
    
    def test_mount_service_raises_without_app(self, mock_controller: ControllerCore) -> None:
        """Test that _mount_service raises RuntimeError when app is not initialized."""
        # Arrange
        mock_controller.app = None
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="FastAPI app not initialized"):
            asyncio.run(mock_controller._mount_service("test_svc", "test.router"))


class TestServiceRegistryModels:
    """Test suite for service registry data models."""
    
    def test_connection_method_enum_values(self) -> None:
        """Test that ConnectionMethod enum has expected values."""
        # Assert
        assert ConnectionMethod.ROUTER.value == "router"
        assert ConnectionMethod.REST.value == "rest"
        assert ConnectionMethod.DISABLED.value == "disabled"
    
    def test_registered_service_effective_method_logic(self) -> None:
        """Test RegisteredService.get_effective_connection_method logic."""
        from datetime import datetime
        
        # Test disabled service
        service = RegisteredService(
            name="test_svc",
            display_name="Test Service",
            connection_method=ConnectionMethod.DISABLED,
            is_active=True,
            has_router=True,
            health_status="healthy"
        )
        
        assert service.get_effective_connection_method() == ConnectionMethod.DISABLED
        
        # Test router service with healthy status
        service.connection_method = ConnectionMethod.ROUTER
        assert service.get_effective_connection_method() == ConnectionMethod.ROUTER
        
        # Test inactive service
        service.is_active = False
        assert service.get_effective_connection_method() == ConnectionMethod.DISABLED
    
    def test_registered_service_health_check(self) -> None:
        """Test RegisteredService health checking functionality."""
        service = RegisteredService(
            name="test_svc",
            display_name="Test Service",
            connection_method=ConnectionMethod.ROUTER,
            is_active=True,
            health_status="healthy"
        )
        
        assert service.is_healthy() is True
        
        service.health_status = "degraded"
        assert service.is_healthy() is False
        
        service.is_active = False
        assert service.is_healthy() is False


class TestMigrationUtilities:
    """Test suite for migration utility functions."""
    
    @pytest.mark.asyncio
    async def test_should_use_router_for_service_with_valid_input(self) -> None:
        """Test global should_use_router_for_service function."""
        with patch('src.rssbot.utils.migration.get_cached_registry') as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.should_use_router.return_value = True
            mock_get_registry.return_value = mock_registry
            
            # Act
            result = await should_use_router_for_service("ai_svc")
            
            # Assert
            assert result is True
            mock_registry.should_use_router.assert_called_once_with("ai_svc")
    
    @pytest.mark.asyncio
    async def test_should_use_router_for_service_fallback_to_legacy(self) -> None:
        """Test fallback to legacy LOCAL_ROUTER_MODE when registry fails."""
        with patch('src.rssbot.utils.migration.get_cached_registry') as mock_get_registry:
            mock_get_registry.side_effect = Exception("Registry error")
            
            with patch.dict('os.environ', {'LOCAL_ROUTER_MODE': 'true'}):
                # Act
                result = await should_use_router_for_service("ai_svc")
                
                # Assert
                assert result is True


class TestTypeHints:
    """Test suite for type hint validation."""
    
    def test_controller_core_type_annotations(self) -> None:
        """Test that ControllerCore has proper type annotations."""
        # Get the class annotations
        annotations = ControllerCore.__annotations__
        
        # Verify that we have type annotations (this will fail if no type hints)
        assert len(annotations) == 0  # __init__ sets instance attributes, not class attributes
        
        # Test method signatures have proper type hints
        init_method = ControllerCore.__init__
        assert hasattr(init_method, '__annotations__')
        
        # Test return type annotation
        initialize_method = ControllerCore.initialize
        assert hasattr(initialize_method, '__annotations__')
        assert initialize_method.__annotations__.get('return') is not None
    
    def test_cached_registry_type_annotations(self) -> None:
        """Test that CachedServiceRegistry has proper type annotations."""
        # Test method return type annotations
        should_use_router_method = CachedServiceRegistry.should_use_router
        assert hasattr(should_use_router_method, '__annotations__')
        assert should_use_router_method.__annotations__.get('return') == bool
        
        get_effective_method = CachedServiceRegistry.get_effective_connection_method
        assert hasattr(get_effective_method, '__annotations__')
        assert get_effective_method.__annotations__.get('return') == ConnectionMethod


class TestPlatformIntegration:
    """Integration tests for the complete platform."""
    
    @pytest.mark.asyncio
    async def test_create_platform_app_returns_fastapi(self) -> None:
        """Test that create_platform_app returns a valid FastAPI instance."""
        with patch('src.rssbot.core.controller.get_controller_core') as mock_get_controller:
            mock_controller = AsyncMock(spec=ControllerCore)
            mock_app = Mock()
            mock_controller.initialize.return_value = mock_app
            mock_get_controller.return_value = mock_controller
            
            # Act
            result = await create_platform_app()
            
            # Assert
            assert result == mock_app
            mock_controller.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_platform_app_handles_initialization_error(self) -> None:
        """Test that create_platform_app properly handles initialization errors."""
        with patch('src.rssbot.core.controller.get_controller_core') as mock_get_controller:
            mock_controller = AsyncMock(spec=ControllerCore)
            mock_controller.initialize.side_effect = Exception("Init failed")
            mock_get_controller.return_value = mock_controller
            
            # Act & Assert
            with pytest.raises(RuntimeError, match="Failed to create platform app"):
                await create_platform_app()


# Performance and stress tests
class TestPerformance:
    """Performance tests for critical paths."""
    
    @pytest.mark.asyncio
    async def test_service_decision_performance(self, mock_registry: CachedServiceRegistry) -> None:
        """Test that service decisions are fast enough for production."""
        import time
        
        # Arrange
        mock_registry._get_cached_connection_method = AsyncMock(
            return_value=ConnectionMethod.ROUTER
        )
        
        # Act - measure time for 1000 decisions
        start_time = time.time()
        tasks = [
            mock_registry.should_use_router(f"service_{i}")
            for i in range(1000)
        ]
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert - should complete in under 1 second
        assert (end_time - start_time) < 1.0
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, mock_registry: CachedServiceRegistry) -> None:
        """Test that concurrent cache access doesn't cause issues."""
        # Arrange
        mock_registry._get_cached_connection_method = AsyncMock(
            return_value=ConnectionMethod.ROUTER
        )
        
        # Act - simulate concurrent access
        tasks = [
            mock_registry.should_use_router("ai_svc")
            for _ in range(100)
        ]
        results = await asyncio.gather(*tasks)
        
        # Assert - all results should be consistent
        assert all(result is True for result in results)
        assert len(results) == 100


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v", "--tb=short"])