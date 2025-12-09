# 🧪 Testing Guide

Comprehensive testing strategies for RssBot Platform including unit tests, integration tests, and end-to-end testing.

## 🎯 Testing Philosophy

RssBot Platform follows a **multi-layered testing approach**:

- **🔬 Unit Tests**: Test individual functions and components in isolation
- **🔗 Integration Tests**: Test service interactions and API endpoints
- **🌐 End-to-End Tests**: Test complete user workflows
- **⚡ Performance Tests**: Test scalability and performance characteristics
- **🔒 Security Tests**: Test authentication, authorization, and input validation

## 📋 Test Structure

### Test Organization

```
tests/
├── unit/                    # Unit tests
│   ├── test_controller.py   # Core controller logic
│   ├── test_registry.py     # Service registry tests
│   ├── test_proxy.py        # Service proxy tests
│   └── services/            # Individual service tests
├── integration/             # Integration tests
│   ├── test_api.py         # API endpoint tests
│   ├── test_services.py    # Service interaction tests
│   └── test_database.py    # Database integration tests
├── e2e/                    # End-to-end tests
│   ├── test_bot_workflow.py
│   ├── test_feed_processing.py
│   └── test_admin_workflows.py
├── performance/            # Performance tests
│   ├── test_load.py
│   └── test_scalability.py
└── fixtures/               # Test data and fixtures
    ├── feeds.json
    ├── users.json
    └── responses.json
```

## 🚀 Running Tests

### Quick Test Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/rssbot --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest tests/e2e/          # E2E tests only

# Run specific test files
pytest tests/unit/test_controller.py
pytest tests/integration/test_api.py -v

# Run tests matching pattern
pytest -k "test_service_discovery"
pytest -k "not slow"
```

### Test Environment Setup

```bash
# Install test dependencies
rye sync --all-features

# Or with pip
pip install -r requirements-dev.lock

# Set up test environment
export ENVIRONMENT=testing
export DATABASE_URL=sqlite:///test.db
export REDIS_URL=redis://localhost:6379/1

# Run tests with test environment
pytest tests/ --env testing
```

## 🔬 Unit Testing

### Core Controller Tests

```python
# tests/unit/test_controller.py
import pytest
from unittest.mock import AsyncMock, patch
from rssbot.core.controller import create_platform_app
from rssbot.discovery.cached_registry import CachedServiceRegistry

@pytest.fixture
async def test_app():
    """Create test application instance"""
    with patch('rssbot.core.controller.get_cached_registry') as mock_registry:
        mock_registry.return_value = AsyncMock(spec=CachedServiceRegistry)
        app = await create_platform_app()
        yield app

@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    """Test platform health endpoint"""
    response = await test_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "architecture" in data
    assert "services_count" in data

@pytest.mark.asyncio
async def test_services_list(test_client, mock_registry):
    """Test services listing endpoint"""
    # Mock service data
    mock_registry.get_all_services.return_value = [
        {
            "name": "db_svc",
            "status": "running",
            "connection_method": "router"
        }
    ]
    
    response = await test_client.get("/services")
    
    assert response.status_code == 200
    services = response.json()
    assert len(services) > 0
    assert services[0]["name"] == "db_svc"
```

### Service Registry Tests

```python
# tests/unit/test_registry.py
import pytest
from unittest.mock import AsyncMock, patch
from rssbot.discovery.cached_registry import CachedServiceRegistry
from rssbot.models.service_registry import ServiceInfo

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    return redis_mock

@pytest.fixture
def mock_database():
    """Mock database connection"""
    db_mock = AsyncMock()
    return db_mock

@pytest.mark.asyncio
async def test_service_cache_miss(mock_redis, mock_database):
    """Test service registry cache miss scenario"""
    # Setup
    registry = CachedServiceRegistry(redis=mock_redis, db=mock_database)
    service_data = ServiceInfo(
        name="test_svc",
        status="running",
        connection_method="router"
    )
    
    # Configure mocks
    mock_redis.get.return_value = None  # Cache miss
    mock_database.get_service.return_value = service_data
    
    # Execute
    result = await registry.get_service("test_svc")
    
    # Verify
    assert result.name == "test_svc"
    mock_redis.get.assert_called_once_with("service:test_svc")
    mock_database.get_service.assert_called_once_with("test_svc")
    mock_redis.set.assert_called_once()

@pytest.mark.asyncio  
async def test_service_cache_hit(mock_redis, mock_database):
    """Test service registry cache hit scenario"""
    # Setup
    registry = CachedServiceRegistry(redis=mock_redis, db=mock_database)
    cached_data = '{"name": "test_svc", "status": "running"}'
    
    # Configure mocks
    mock_redis.get.return_value = cached_data
    
    # Execute
    result = await registry.get_service("test_svc")
    
    # Verify
    assert result.name == "test_svc"
    mock_redis.get.assert_called_once_with("service:test_svc")
    mock_database.get_service.assert_not_called()  # Should not hit database
```

## 🔗 Integration Testing

### API Integration Tests

```python
# tests/integration/test_api.py
import pytest
import httpx
from fastapi.testclient import TestClient

@pytest.fixture
def test_client():
    """Create test client for API testing"""
    from rssbot.core.controller import create_platform_app
    app = create_platform_app()
    return TestClient(app)

@pytest.mark.integration
def test_service_connection_method_update(test_client):
    """Test updating service connection method"""
    # Test data
    service_name = "ai_svc"
    new_method = "hybrid"
    
    # Execute API call
    response = test_client.post(
        f"/services/{service_name}/connection-method",
        json={"connection_method": new_method},
        headers={"Authorization": "Bearer test_token"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == service_name
    assert data["new_method"] == new_method
    
    # Verify change persisted
    status_response = test_client.get(f"/services/{service_name}/status")
    status_data = status_response.json()
    assert status_data["connection_method"] == new_method

@pytest.mark.integration
async def test_database_service_integration(test_client, test_database):
    """Test database service integration"""
    # Create test feed
    feed_data = {
        "url": "https://example.com/test-feed.xml",
        "title": "Test Feed",
        "chat_id": 12345,
        "update_interval": 3600
    }
    
    # Create feed via API
    response = test_client.post(
        "/services/db_svc/feeds",
        json=feed_data,
        headers={"Authorization": "Bearer test_token"}
    )
    
    assert response.status_code == 201
    created_feed = response.json()
    feed_id = created_feed["id"]
    
    # Verify feed exists in database
    get_response = test_client.get(f"/services/db_svc/feeds/{feed_id}")
    assert get_response.status_code == 200
    
    retrieved_feed = get_response.json()
    assert retrieved_feed["url"] == feed_data["url"]
    assert retrieved_feed["title"] == feed_data["title"]
```

### Service Communication Tests

```python
# tests/integration/test_services.py
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.integration
async def test_ai_service_communication():
    """Test AI service communication through proxy"""
    from rssbot.discovery.proxy import ServiceProxy
    from rssbot.models.service_registry import ServiceInfo
    
    # Setup
    proxy = ServiceProxy()
    
    with patch.object(proxy, 'registry') as mock_registry:
        # Mock service info
        service_info = ServiceInfo(
            name="ai_svc",
            connection_method="router",
            status="running",
            health_score=0.9
        )
        mock_registry.get_service.return_value = service_info
        
        # Mock AI service function
        with patch('rssbot.services.ai_svc.main.process_content') as mock_ai:
            mock_ai.return_value = {"summary": "Test summary"}
            
            # Execute
            result = await proxy.call_service(
                "ai_svc",
                "process_content",
                text="Test content",
                action="summarize"
            )
            
            # Verify
            assert result["summary"] == "Test summary"
            mock_ai.assert_called_once()

@pytest.mark.integration  
async def test_service_failover():
    """Test service failover in hybrid mode"""
    from rssbot.discovery.proxy import ServiceProxy
    
    proxy = ServiceProxy()
    
    # Test automatic failover from router to REST
    with patch.object(proxy, '_direct_call') as mock_direct:
        mock_direct.side_effect = ConnectionError("Service unavailable")
        
        with patch.object(proxy, '_http_call') as mock_http:
            mock_http.return_value = {"status": "success"}
            
            # This should automatically failover to HTTP
            result = await proxy._hybrid_call(service_info, "test_method")
            
            assert result["status"] == "success"
            mock_direct.assert_called_once()
            mock_http.assert_called_once()
```

## 🌐 End-to-End Testing

### Bot Workflow Tests

```python
# tests/e2e/test_bot_workflow.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.e2e
async def test_complete_bot_workflow(test_app, mock_telegram):
    """Test complete bot workflow from user interaction to feed processing"""
    
    # Setup test user and bot
    user_id = 12345
    chat_id = 12345
    
    # Step 1: User starts bot
    with patch('telegram.Bot.send_message') as mock_send:
        await mock_telegram.send_update({
            "message": {
                "from": {"id": user_id},
                "chat": {"id": chat_id},
                "text": "/start"
            }
        })
        
        # Verify welcome message sent
        mock_send.assert_called()
        welcome_call = mock_send.call_args
        assert "welcome" in welcome_call[1]["text"].lower()
    
    # Step 2: User subscribes to feed
    with patch('telegram.Bot.send_message') as mock_send:
        await mock_telegram.send_update({
            "message": {
                "from": {"id": user_id},
                "chat": {"id": chat_id},
                "text": "/subscribe https://example.com/feed.xml"
            }
        })
        
        # Verify subscription confirmation
        mock_send.assert_called()
        confirm_call = mock_send.call_args
        assert "subscribed" in confirm_call[1]["text"].lower()
    
    # Step 3: Simulate feed update
    feed_content = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Test Article</title>
                <description>Test description</description>
                <link>https://example.com/article</link>
            </item>
        </channel>
    </rss>"""
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.text = feed_content
        mock_get.return_value.status_code = 200
        
        with patch('telegram.Bot.send_message') as mock_send:
            # Trigger feed processing
            await test_app.services.channel_mgr.process_feeds()
            
            # Verify article was sent to user
            mock_send.assert_called()
            article_call = mock_send.call_args
            assert "Test Article" in article_call[1]["text"]

@pytest.mark.e2e
async def test_ai_enhancement_workflow(test_app, mock_openai):
    """Test AI enhancement in complete workflow"""
    
    # Setup
    user_id = 12345
    original_content = "This is a very long article about technology trends..."
    ai_summary = "Brief summary of technology trends."
    
    # Mock OpenAI response
    mock_openai.completions.create.return_value.choices[0].text = ai_summary
    
    # Create feed with AI enabled
    feed_data = {
        "url": "https://example.com/feed.xml",
        "title": "Tech Feed",
        "chat_id": user_id,
        "ai_processing": True,
        "ai_summary": True
    }
    
    # Process content with AI
    result = await test_app.services.ai_svc.process_content({
        "text": original_content,
        "action": "summarize",
        "max_length": 200
    })
    
    # Verify AI processing
    assert result["summary"] == ai_summary
    assert len(result["summary"]) < len(original_content)
```

### Feed Processing Tests

```python
# tests/e2e/test_feed_processing.py
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

@pytest.mark.e2e
async def test_feed_processing_pipeline(test_app):
    """Test complete feed processing pipeline"""
    
    # Step 1: Create feed
    feed_data = {
        "url": "https://example.com/test-feed.xml",
        "title": "Test Feed",
        "chat_id": 12345,
        "update_interval": 3600
    }
    
    created_feed = await test_app.services.db_svc.create_feed(feed_data)
    feed_id = created_feed.id
    
    # Step 2: Mock RSS content
    rss_content = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <title>Test Feed</title>
            <item>
                <title>Breaking News</title>
                <description>Important news update</description>
                <link>https://example.com/news1</link>
                <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>"""
    
    # Step 3: Process feed
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.text = rss_content
        mock_get.return_value.status_code = 200
        
        with patch('telegram.Bot.send_message') as mock_send:
            # Execute feed processing
            await test_app.services.channel_mgr.process_feed(feed_id)
            
            # Verify processing results
            mock_get.assert_called_once_with(feed_data["url"])
            mock_send.assert_called_once()
            
            # Check message content
            send_args = mock_send.call_args
            message_text = send_args[1]["text"]
            assert "Breaking News" in message_text
            assert "Important news update" in message_text
            
    # Step 4: Verify feed status updated
    updated_feed = await test_app.services.db_svc.get_feed(feed_id)
    assert updated_feed.last_updated is not None
    assert updated_feed.status == "active"
```

## ⚡ Performance Testing

### Load Testing

```python
# tests/performance/test_load.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.performance
async def test_concurrent_service_calls(test_app):
    """Test platform performance under concurrent load"""
    
    async def make_health_check():
        """Single health check request"""
        start_time = time.time()
        response = await test_app.test_client.get("/health")
        end_time = time.time()
        
        return {
            "status_code": response.status_code,
            "response_time": end_time - start_time
        }
    
    # Execute 100 concurrent requests
    tasks = [make_health_check() for _ in range(100)]
    results = await asyncio.gather(*tasks)
    
    # Analyze results
    successful_requests = [r for r in results if r["status_code"] == 200]
    response_times = [r["response_time"] for r in successful_requests]
    
    # Performance assertions
    assert len(successful_requests) >= 95  # 95% success rate
    assert max(response_times) < 1.0       # Max 1 second response time
    assert sum(response_times) / len(response_times) < 0.1  # Average < 100ms

@pytest.mark.performance
async def test_service_discovery_performance(test_app):
    """Test service discovery performance"""
    
    # Warm up cache
    await test_app.registry.get_service("db_svc")
    
    # Test cached performance
    start_time = time.time()
    for _ in range(1000):
        await test_app.registry.get_service("db_svc")
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time_per_call = total_time / 1000
    
    # Should be sub-millisecond for cached calls
    assert avg_time_per_call < 0.001  # Less than 1ms average

@pytest.mark.performance
async def test_feed_processing_performance(test_app):
    """Test feed processing performance with multiple feeds"""
    
    # Create 50 test feeds
    feeds = []
    for i in range(50):
        feed_data = {
            "url": f"https://example.com/feed{i}.xml",
            "title": f"Test Feed {i}",
            "chat_id": 12345 + i,
            "update_interval": 3600
        }
        feed = await test_app.services.db_svc.create_feed(feed_data)
        feeds.append(feed)
    
    # Process all feeds concurrently
    start_time = time.time()
    await test_app.services.channel_mgr.process_all_feeds()
    end_time = time.time()
    
    processing_time = end_time - start_time
    
    # Should process 50 feeds in reasonable time
    assert processing_time < 30  # Less than 30 seconds for 50 feeds
    assert processing_time / 50 < 1  # Less than 1 second per feed average
```

## 🔒 Security Testing

### Authentication Tests

```python
# tests/security/test_auth.py
import pytest
from unittest.mock import patch

@pytest.mark.security
async def test_unauthorized_api_access(test_client):
    """Test API endpoints require proper authentication"""
    
    # Test without token
    response = await test_client.post("/services/ai_svc/connection-method")
    assert response.status_code == 401
    
    # Test with invalid token
    response = await test_client.post(
        "/services/ai_svc/connection-method",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    
    # Test with valid token
    response = await test_client.post(
        "/services/ai_svc/connection-method",
        json={"connection_method": "router"},
        headers={"Authorization": "Bearer valid_test_token"}
    )
    assert response.status_code in [200, 422]  # 422 for validation errors

@pytest.mark.security
async def test_input_validation(test_client):
    """Test input validation and sanitization"""
    
    # Test SQL injection attempt
    malicious_feed = {
        "url": "https://example.com'; DROP TABLE feeds; --",
        "title": "Malicious Feed",
        "chat_id": 12345
    }
    
    response = await test_client.post(
        "/services/db_svc/feeds",
        json=malicious_feed,
        headers={"Authorization": "Bearer valid_test_token"}
    )
    
    # Should reject malicious input
    assert response.status_code == 422  # Validation error
    
    # Test XSS attempt
    xss_feed = {
        "url": "https://example.com/feed.xml",
        "title": "<script>alert('xss')</script>",
        "chat_id": 12345
    }
    
    response = await test_client.post(
        "/services/db_svc/feeds",
        json=xss_feed,
        headers={"Authorization": "Bearer valid_test_token"}
    )
    
    if response.status_code == 201:
        # If created, title should be sanitized
        created_feed = response.json()
        assert "<script>" not in created_feed["title"]
```

## 🛠️ Test Configuration

### Test Settings

```python
# tests/conftest.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_app():
    """Create test application"""
    from rssbot.core.controller import create_platform_app
    
    # Override configuration for testing
    with patch.dict(os.environ, {
        "ENVIRONMENT": "testing",
        "DATABASE_URL": "sqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/1",
        "SERVICE_TOKEN": "test_token"
    }):
        app = await create_platform_app()
        yield app

@pytest.fixture
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)

@pytest.fixture
def mock_telegram():
    """Mock Telegram bot for testing"""
    with patch('telegram.Bot') as mock_bot:
        yield mock_bot

@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing"""
    with patch('openai.OpenAI') as mock_client:
        yield mock_client
```

### Test Database Setup

```python
# tests/fixtures/database.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rssbot.models.service_registry import Base

@pytest.fixture
async def test_database():
    """Create test database"""
    engine = create_engine("sqlite:///test.db")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)
```

## 📊 Test Coverage

### Coverage Configuration

```ini
# .coveragerc
[run]
source = src/rssbot
omit = 
    */tests/*
    */venv/*
    */migrations/*
    */conftest.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:

[html]
directory = htmlcov
```

### Coverage Commands

```bash
# Run tests with coverage
pytest --cov=src/rssbot

# Generate HTML coverage report  
pytest --cov=src/rssbot --cov-report=html

# Generate coverage badge
coverage-badge -f -o coverage.svg

# Fail if coverage below threshold
pytest --cov=src/rssbot --cov-fail-under=85
```

## 🚀 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    services:
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install rye
        rye sync --all-features
    
    - name: Run tests
      run: |
        rye run pytest --cov=src/rssbot --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

**🧪 Comprehensive testing ensures RssBot Platform remains reliable, performant, and secure across all environments and use cases.**