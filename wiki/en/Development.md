# 👨‍💻 Development Guide

This comprehensive guide covers development workflows, adding new features, creating services, and contributing to the **RssBot Hybrid Microservices Platform**.

## 🎯 Development Philosophy

The RssBot Platform follows modern development principles:

- **🔒 Type Safety First**: 100% type hints with mypy validation
- **📚 Documentation-Driven**: Comprehensive docstrings and examples
- **🧪 Test-Driven Development**: Tests written before implementation
- **🔧 Per-Service Architecture**: Independent service development and deployment
- **⚡ Performance-Conscious**: Redis caching and optimized algorithms

## 🛠️ Development Environment Setup

### 🔧 Prerequisites

```bash
# Required tools
python >= 3.11
git
redis-server
postgresql (optional, SQLite works for dev)

# Recommended tools
rye (modern Python package manager)
docker & docker-compose
vs code or pycharm
```

### 📦 Project Setup

```bash
# Clone and setup development environment
git clone https://github.com/your-username/rssbot-platform.git
cd rssbot-platform

# Install dependencies with rye (recommended)
pip install rye
rye sync

# Or use traditional pip
pip install -e .
pip install -r requirements-dev.lock

# Setup pre-commit hooks
pre-commit install

# Copy environment configuration
cp .env.example .env
# Edit .env for development settings
```

### 🔧 Development Configuration

Edit `.env` for development:

```bash
# === Development Settings ===
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# === Database (SQLite for simplicity) ===
DATABASE_URL=sqlite:///./dev_rssbot.db
DB_ECHO=true  # Show SQL queries

# === Redis (required for caching) ===
REDIS_URL=redis://localhost:6379/0

# === Service Communication ===
SERVICE_TOKEN=dev_service_token_change_in_production

# === External Services (optional for dev) ===
TELEGRAM_BOT_TOKEN=your_test_bot_token
OPENAI_API_KEY=your_dev_api_key
STRIPE_SECRET_KEY=your_test_stripe_key
```

### 🚀 Start Development Environment

```bash
# Method 1: Core platform (recommended)
python -m rssbot

# Method 2: Development script
./scripts/start_dev.sh

# Method 3: With hot reload
uvicorn rssbot.core.controller:create_platform_app --reload --host 0.0.0.0 --port 8004
```

## 📐 Code Standards & Guidelines

### 🎯 Type Safety Requirements

**All code must be 100% type-safe.** Examples:

```python
# ✅ Correct: Full type annotations
from typing import Dict, List, Optional, Union
from datetime import datetime

async def process_services(
    service_names: List[str],
    connection_method: ConnectionMethod = ConnectionMethod.ROUTER
) -> Dict[str, Union[str, bool]]:
    """
    Process multiple services with specified connection method.


    Args:
        service_names: List of service names to process
        connection_method: How services should connect

    Returns:
        Dictionary with processing results for each service

    Raises:
        ValueError: If service_names is empty
        ServiceError: If processing fails
    """
    if not service_names:
        raise ValueError("service_names cannot be empty")

    results: Dict[str, Union[str, bool]] = {}

    for service_name in service_names:
        try:
            success = await configure_service(service_name, connection_method)
            results[service_name] = success
        except ServiceError as e:
            logger.error(f"Failed to process {service_name}: {e}")
            results[service_name] = False

    return results

# ❌ Incorrect: Missing type hints
def process_services(service_names, connection_method=None):
    # This will fail CI/CD pipeline
    pass
```

### 📚 Documentation Standards

**Google-style docstrings are required:**

```python
class CachedServiceRegistry:
    """
    High-performance service registry with Redis caching.

    This class provides service discovery, health monitoring, and connection
    method management using Redis for caching and database for persistence.

    Attributes:
        redis_client: Redis client for caching operations
        db_session: Database session for persistent storage

    Example:
        ```python
        registry = CachedServiceRegistry()
        await registry.initialize()

        # Check if service should use router
        use_router = await registry.should_use_router("ai_svc")
        if use_router:
            # Mount as router for maximum performance
            pass
        ```
    """

    async def should_use_router(self, service_name: str) -> bool:
        """
        Determine if service should use router connection method.

        This is the primary method for making per-service connection decisions.
        It checks cached configuration and service health to determine the
        optimal connection method.

        Args:
            service_name: Name of the service (e.g., 'ai_svc', 'formatting_svc')

        Returns:
            True if service should be mounted as FastAPI router (in-process),
            False if service should use REST HTTP calls

        Raises:
            ValueError: If service_name is empty or invalid format
            CacheConnectionError: If Redis is down and database is unreachable


        Example:
            ```python
            # Check AI service connection method
            if await registry.should_use_router("ai_svc"):
                result = ai_router.summarize(text)  # Direct function call
            else:
                result = await http_client.post("/ai/summarize", ...)  # HTTP
            ```
        """
        # Implementation...
```

### 🧪 Testing Requirements

**All new features require comprehensive tests:**

```python
# tests/test_new_feature.py
import pytest
from unittest.mock import AsyncMock, Mock
from rssbot.discovery.cached_registry import CachedServiceRegistry
from rssbot.models.service_registry import ConnectionMethod

class TestCachedServiceRegistry:
    """Comprehensive test suite for CachedServiceRegistry."""
    @pytest.fixture
    async def mock_registry(self) -> CachedServiceRegistry:
        """Create mock registry for testing."""
        registry = CachedServiceRegistry()
        registry._redis = AsyncMock()
        registry._redis_available = True
        return registry

    @pytest.mark.asyncio
    async def test_should_use_router_validates_input(
        self, mock_registry: CachedServiceRegistry
    ) -> None:
        """Test input validation for should_use_router method."""
        # Test empty service name
        with pytest.raises(ValueError, match="service_name must be non-empty"):
            await mock_registry.should_use_router("")


        # Test None input
        with pytest.raises(ValueError):
            await mock_registry.should_use_router(None)  # type: ignore


    @pytest.mark.asyncio
    async def test_should_use_router_returns_correct_decision(
        self, mock_registry: CachedServiceRegistry
    ) -> None:
        """Test that should_use_router returns correct decisions."""
        # Arrange
        mock_registry._get_cached_connection_method = AsyncMock(
            return_value=ConnectionMethod.ROUTER
        )


        # Act
        result = await mock_registry.should_use_router("ai_svc")

        # Assert
        assert result is True
        mock_registry._get_cached_connection_method.assert_called_once_with("ai_svc")

    @pytest.mark.asyncio
    async def test_cache_fallback_behavior(
        self, mock_registry: CachedServiceRegistry
    ) -> None:
        """Test graceful fallback when Redis is unavailable."""
        # Arrange
        mock_registry._redis_available = False
        mock_service = Mock()
        mock_service.get_effective_connection_method.return_value = ConnectionMethod.REST
        mock_registry.registry_manager.get_service_by_name = AsyncMock(
            return_value=mock_service
        )

        # Act
        result = await mock_registry.get_effective_connection_method("test_svc")

        # Assert
        assert result == ConnectionMethod.REST
```

## 🏗️ Adding New Services

### 📝 Service Creation Checklist

1. **Create service directory structure**
2. **Implement main.py for standalone mode**
3. **Create router.py for router mode (optional)**
4. **Add type-safe models and schemas**
5. **Write comprehensive tests**
6. **Update documentation**
7. **Configure service in registry**

### 🛠️ Step-by-Step Service Creation

#### 1. Create Service Directory

```bash
# Create new service
mkdir services/new_svc
cd services/new_svc

# Create essential files
touch __init__.py main.py router.py models.py tests.py
```

#### 2. Implement Main Application

```python
# services/new_svc/main.py
"""
New Service - Standalone FastAPI application.

This service demonstrates the per-service architecture pattern.
It can run independently (REST mode) or be mounted as router.
"""
import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from rssbot.discovery.proxy import ServiceProxy
from rssbot.core.security import verify_service_token

# Type-safe request/response models
class ProcessRequest(BaseModel):
    """Request model for processing operations."""
    data: str = Field(..., description="Data to process")
    options: Dict[str, Any] = Field(default_factory=dict)

class ProcessResponse(BaseModel):
    """Response model for processing results."""
    result: str = Field(..., description="Processing result")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")

# FastAPI application
app = FastAPI(
    title="New Service",
    description="Example service demonstrating per-service architecture",
    version="1.0.0",
)

# Service dependencies (using ServiceProxy)
ai_service = ServiceProxy("ai_svc")
formatting_service = ServiceProxy("formatting_svc")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Service health check endpoint.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "service": "new_svc",
        "version": "1.0.0"
    }

@app.post("/process", response_model=ProcessResponse)
async def process_data(
    request: ProcessRequest,
    token: str = Depends(verify_service_token)
) -> ProcessResponse:
    """
    Process data using AI and formatting services.

    Args:
        request: Processing request with data and options
        token: Service authentication token

    Returns:
        Processing results with metadata

    Raises:
        HTTPException: If processing fails
    """
    import time
    start_time = time.time()

    try:
        # Use other services via ServiceProxy
        if request.options.get("use_ai", False):
            ai_result = await ai_service.process(data=request.data)
            processed_data = ai_result.get("result", request.data)
        else:
            processed_data = request.data

        if request.options.get("format", False):
            formatted_result = await formatting_service.format(
                content=processed_data,
                format_type="default"
            )
            final_result = formatted_result.get("formatted_content", processed_data)
        else:
            final_result = processed_data


        processing_time = (time.time() - start_time) * 1000


        return ProcessResponse(
            result=final_result,
            metadata={
                "original_length": len(request.data),
                "final_length": len(final_result),
                "used_ai": request.options.get("use_ai", False),
                "used_formatting": request.options.get("format", False)
            },
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )

@app.get("/services/dependencies")
async def get_service_dependencies(
    token: str = Depends(verify_service_token)
) -> Dict[str, List[str]]:
    """
    Get service dependencies for monitoring.
    
    Returns:
        Dictionary of service dependencies
    """
    return {
        "required_services": ["ai_svc", "formatting_svc"],
        "optional_services": [],
        "health_check_services": ["ai_svc", "formatting_svc"]
    }

# Service initialization for router mode
async def initialize_service() -> None:
    """Initialize service when mounted as router."""
    print("🔧 New Service initialized in router mode")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8011,  # Unique port for this service
        log_level="info"
    )
```

#### 3. Create Router Module (Optional)

```python
# services/new_svc/router.py
"""
New Service Router - For mounting in controller.

This module provides the router for mounting the service in the main
controller when using router mode.
"""
from fastapi import APIRouter
from .main import process_data, get_service_dependencies, health_check

# Create router for mounting
router = APIRouter(
    prefix="/new",
    tags=["new_svc"],
    responses={404: {"description": "Not found"}}
)

# Add routes from main application
router.add_api_route("/health", health_check, methods=["GET"])
router.add_api_route("/process", process_data, methods=["POST"])
router.add_api_route("/services/dependencies", get_service_dependencies, methods=["GET"])

# Service initialization function
async def initialize_service() -> None:
    """Initialize service for router mode."""
    print("🔧 New Service router initialized")
```

#### 4. Add Service Models

```python
# services/new_svc/models.py
"""
New Service Models - Type-safe data models.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class ServiceConfig(BaseModel):
    """Configuration model for new service."""
    enable_ai_processing: bool = Field(default=True)
    enable_formatting: bool = Field(default=True)
    max_processing_time: int = Field(default=30, description="Max processing time in seconds")
    allowed_data_types: List[str] = Field(default=["text", "json"])

class ProcessingMetrics(BaseModel):
    """Metrics model for processing operations."""
    total_requests: int = Field(default=0)
    successful_requests: int = Field(default=0)
    failed_requests: int = Field(default=0)
    avg_processing_time: float = Field(default=0.0)
    last_request_time: Optional[datetime] = Field(default=None)

class ServiceStatus(BaseModel):
    """Service status model."""
    is_healthy: bool = Field(...)
    connection_method: str = Field(...)
    dependencies_status: Dict[str, str] = Field(default_factory=dict)
    metrics: ProcessingMetrics = Field(default_factory=ProcessingMetrics)
    config: ServiceConfig = Field(default_factory=ServiceConfig)
```

#### 5. Write Tests

```python
# services/new_svc/tests.py
"""
Comprehensive tests for New Service.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch

from .main import app
from .models import ProcessRequest, ProcessResponse

class TestNewService:
    """Test suite for New Service."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service dependency."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_formatting_service(self):
        """Mock formatting service dependency."""
        return AsyncMock()
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "new_svc"
        assert "version" in data
    
    @patch('services.new_svc.main.verify_service_token')
    async def test_process_data_success(self, mock_token, client, mock_ai_service, mock_formatting_service):
        """Test successful data processing."""
        # Arrange
        mock_token.return_value = "valid_token"
        
        with patch('services.new_svc.main.ai_service', mock_ai_service), \
             patch('services.new_svc.main.formatting_service', mock_formatting_service):
            
            mock_ai_service.process.return_value = {"result": "processed data"}
            mock_formatting_service.format.return_value = {"formatted_content": "formatted data"}
            
            request_data = {
                "data": "test data",
                "options": {"use_ai": True, "format": True}
            }
            
            # Act
            response = client.post(
                "/process",
                json=request_data,
                headers={"X-Service-Token": "valid_token"}
            )
            
            # Assert
            assert response.status_code == 200
            
            data = response.json()
            assert data["result"] == "formatted data"
            assert data["processing_time_ms"] > 0
            assert data["metadata"]["used_ai"] is True
            assert data["metadata"]["used_formatting"] is True
    
    def test_process_data_validation(self, client):
        """Test request validation."""
        # Missing required field
        response = client.post(
            "/process",
            json={"options": {}},  # Missing 'data' field
            headers={"X-Service-Token": "valid_token"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('services.new_svc.main.verify_service_token')
    def test_get_dependencies(self, mock_token, client):
        """Test service dependencies endpoint."""
        mock_token.return_value = "valid_token"
        
        response = client.get(
            "/services/dependencies",
            headers={"X-Service-Token": "valid_token"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "required_services" in data
        assert "ai_svc" in data["required_services"]
        assert "formatting_svc" in data["required_services"]
```

#### 6. Register Service in Platform

```python
# Add to service registry (automatic discovery)
# The platform will automatically discover the service if it follows the naming convention

# Configure service connection method
curl -X POST http://localhost:8004/services/new_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{"connection_method": "router"}'  # or "rest", "hybrid", "disabled"
```

### 📊 Service Configuration Options

```python
# Service can be configured for different scenarios:

# High-performance scenario (router mode)
{
    "connection_method": "router",
    "description": "In-process mounting for maximum performance"
}

# Scalable scenario (REST mode)  
{
    "connection_method": "rest",
    "description": "HTTP-based for independent scaling"
}

# Reliable scenario (hybrid mode)
{
    "connection_method": "hybrid", 
    "description": "Router preferred with REST fallback"
}

# Maintenance scenario (disabled)
{
    "connection_method": "disabled",
    "description": "Service completely disabled"
}
```

## 🔧 Extending Core Platform

### 🎯 Adding New Features to Core

When adding features to the core platform:

1. **Update Core Models** in `src/rssbot/models/`
2. **Add Type-Safe APIs** in `src/rssbot/core/`
3. **Write Comprehensive Tests** in `tests/`
4. **Update Documentation** in `docs/`

#### Example: Adding Service Metrics

```python
# 1. Update models
# src/rssbot/models/service_metrics.py
from typing import Dict, List
from datetime import datetime
from pydantic import BaseModel

class ServiceMetrics(BaseModel):
    """Service performance metrics model."""
    service_name: str
    requests_per_second: float
    average_response_time_ms: float
    error_rate: float
    cache_hit_ratio: float
    last_updated: datetime

# 2. Update core controller  
# src/rssbot/core/controller.py
async def get_service_metrics(self, service_name: str) -> ServiceMetrics:
    """Get comprehensive metrics for a service."""
    # Implementation with type safety
    
# 3. Add API endpoint
@app.get("/services/{service_name}/metrics", response_model=ServiceMetrics)
async def get_service_metrics_endpoint(service_name: str) -> ServiceMetrics:
    """Get service performance metrics."""
    return await controller.get_service_metrics(service_name)

# 4. Write tests
class TestServiceMetrics:
    async def test_get_service_metrics_returns_valid_data(self):
        """Test metrics collection returns valid data."""
        # Comprehensive test implementation
```

### 🔄 Adding New Connection Methods

```python
# 1. Update ConnectionMethod enum
# src/rssbot/models/service_registry.py
class ConnectionMethod(str, enum.Enum):
    ROUTER = "router"
    REST = "rest" 
    HYBRID = "hybrid"
    DISABLED = "disabled"
    STREAMING = "streaming"  # New connection method

# 2. Update decision logic
# src/rssbot/discovery/cached_registry.py
async def get_effective_connection_method(self, service_name: str) -> ConnectionMethod:
    """Enhanced logic supporting new connection methods."""
    # Add streaming logic
    if method == ConnectionMethod.STREAMING:
        return self._handle_streaming_connection(service)

# 3. Update controller mounting
# src/rssbot/core/controller.py  
async def _mount_service(self, service_name: str, router_path: str) -> None:
    """Enhanced mounting supporting streaming connections."""
    # Add streaming support
```

## 🧪 Testing Framework

### 🎯 Testing Strategy

The platform uses **pytest** with **comprehensive test coverage**:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/rssbot --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests  
pytest tests/test_platform.py  # Platform tests

# Run tests with performance profiling
pytest --profile

# Run tests with specific markers
pytest -m "not slow"       # Skip slow tests
pytest -m "redis"          # Only Redis-related tests
```

### 📊 Test Categories

#### 1. Unit Tests
```python
# Test individual functions and methods
class TestCachedRegistry:
    async def test_should_use_router_validates_input(self):
        """Test input validation."""
        
    async def test_cache_invalidation_works(self):
        """Test cache invalidation."""
        
    async def test_fallback_to_database(self):
        """Test Redis fallback behavior."""
```

#### 2. Integration Tests
```python
# Test service interactions
class TestServiceIntegration:
    async def test_ai_formatting_pipeline(self):
        """Test AI + formatting service pipeline."""
        
    async def test_cache_database_sync(self):
        """Test cache and database synchronization."""
        
    async def test_health_monitoring_updates_cache(self):
        """Test health monitoring integration."""
```

#### 3. Performance Tests
```python
# Test performance characteristics
class TestPerformance:
    async def test_service_decision_speed(self):
        """Test service decisions are sub-millisecond."""
        
    async def test_concurrent_cache_access(self):
        """Test concurrent cache access performance."""
        
    async def test_memory_usage_under_load(self):
        """Test memory usage under load."""
```

### 🔧 Testing Utilities

```python
# tests/conftest.py - Shared test fixtures
import pytest
from unittest.mock import AsyncMock
from rssbot.discovery.cached_registry import CachedServiceRegistry

@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    return redis_mock

@pytest.fixture
async def test_registry(mock_redis):
    """Create test service registry."""
    registry = CachedServiceRegistry()
    registry._redis = mock_redis
    registry._redis_available = True
    return registry

@pytest.fixture
def sample_service_config():
    """Sample service configuration for testing."""
    return {
        "name": "test_svc",
        "connection_method": "router",
        "health_status": "healthy",
        "has_router": True
    }
```

## 🚀 Performance Optimization

### ⚡ Performance Best Practices

#### 1. Cache Optimization
```python
# Use appropriate cache TTLs
CACHE_SETTINGS = {
    "service_decisions": 300,    # 5 minutes (frequently accessed)
    "service_health": 60,        # 1 minute (health changes)
    "service_config": 1800,      # 30 minutes (config rarely changes)
}

# Implement cache warming
async def warm_service_cache():
    """Pre-populate cache with frequently accessed data."""
    active_services = await get_active_services()
    
    for service in active_services:
        # Pre-cache service decisions
        await cache_service_decision(service.name)
```

#### 2. Database Optimization
```python
# Use async database operations
async with AsyncSession() as session:
    # Batch operations for better performance
    services = await session.exec(
        select(RegisteredService)
        .where(RegisteredService.is_active == True)
        .options(selectinload(RegisteredService.health_checks))
    )

# Use connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600
)
```

#### 3. Service Call Optimization
```python
# Use connection pooling for HTTP calls
async with httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    timeout=httpx.Timeout(connect=5.0, read=30.0)
) as client:
    # Efficient HTTP calls
    response = await client.post(url, json=data)
```

## 📊 Monitoring & Debugging

### 🔍 Development Debugging

```python
# Enable debug logging
import logging
logging.getLogger("rssbot").setLevel(logging.DEBUG)

# Add debug endpoints
@app.get("/debug/cache")
async def debug_cache():
    """Debug cache state."""
    return await get_cache_debug_info()

@app.get("/debug/services")  
async def debug_services():
    """Debug service registry state."""
    return await get_service_debug_info()
```

### 📈 Performance Monitoring

```python
# Add performance monitoring
import time
from contextlib import asynccontextmanager

@asynccontextmanager
async def monitor_performance(operation: str):
    """Context manager for performance monitoring."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        await record_performance_metric(operation, duration)

# Usage
async def service_operation():
    async with monitor_performance("service_decision"):
        result = await make_service_decision()
    return result
```

## 📚 Documentation Guidelines

### 📖 Documentation Requirements

1. **API Documentation**: All endpoints documented with OpenAPI
2. **Code Documentation**: Google-style docstrings for all public functions
3. **Architecture Documentation**: High-level system design
4. **User Guides**: Step-by-step instructions for common tasks

### 📝 Documentation Updates

When adding features, update:

```bash
# Update API documentation
# Automatic via FastAPI OpenAPI

# Update user guides
docs/GETTING_STARTED.md
docs/DEVELOPMENT.md  
docs/PRODUCTION.md

# Update architecture docs
docs/ARCHITECTURE.md
NEW_ARCHITECTURE.md

# Update changelog
CHANGELOG.md
```

## 🎯 Development Workflow

### 🔄 Daily Workflow

```bash
# 1. Start development environment
python -m rssbot

# 2. Configure services for fast development
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -d '{"ai_svc": "router", "formatting_svc": "router"}'

# 3. Make code changes
# Edit files in src/rssbot/ or services/

# 4. Run tests
pytest tests/

# 5. Check code quality
black src/ services/
isort src/ services/
flake8 src/ services/
mypy src/rssbot

# 6. Commit changes
git add .
git commit -m "feat: add new service feature"
git push origin feature-branch
```

### 🚀 Release Workflow

```bash
# 1. Update version
# Edit pyproject.toml version

# 2. Update changelog
# Add entries to CHANGELOG.md

# 3. Run comprehensive tests
pytest --cov=src/rssbot

# 4. Create release
git tag v2.1.0
git push origin v2.1.0

# 5. GitHub Actions handles CI/CD
# - Runs all tests
# - Builds package
# - Publishes to PyPI
```

## 🤝 Contributing Guidelines

### 📋 Contribution Checklist

Before submitting a PR:

- [ ] **Code is type-safe** (mypy passes)
- [ ] **Tests are comprehensive** (>90% coverage)
- [ ] **Documentation is updated**
- [ ] **Pre-commit hooks pass**
- [ ] **Performance is considered**
- [ ] **Security is validated**

### 🎯 Pull Request Process

1. **Fork repository** and create feature branch
2. **Implement feature** with tests and documentation
3. **Ensure code quality** passes all checks
4. **Submit PR** with clear description
5. **Address feedback** from code review
6. **Merge** after approval

---

**The development experience on RssBot Platform is designed to be productive, type-safe, and enjoyable. Happy coding! 🚀✨**