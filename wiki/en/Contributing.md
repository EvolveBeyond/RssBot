# 🤝 Contributing to RssBot Platform

Thank you for your interest in contributing to RssBot Platform! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Workflow](#contributing-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## 🤝 Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and considerate in all interactions.

### Our Standards

- **Be respectful**: Treat all community members with respect and kindness
- **Be inclusive**: Welcome newcomers and help them get started
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember that everyone has different levels of experience

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Git**
- **Redis** (for local development)
- **PostgreSQL** or SQLite
- **Node.js** (for documentation builds, optional)

### Fork and Clone

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:

```bash
git clone https://github.com/your-username/rssbot-platform.git
cd rssbot-platform
```

3. **Add upstream** remote:

```bash
git remote add upstream https://github.com/original-username/rssbot-platform.git
```

## 🛠️ Development Setup

### Quick Setup

```bash
# Install dependencies
rye sync

# Or with pip
pip install -e .
pip install -r requirements-dev.lock

# Copy environment configuration
cp .env.example .env

# Edit .env with your local settings
vim .env
```

### Database Setup

```bash
# Option 1: SQLite (easiest)
DATABASE_URL=sqlite:///./rssbot.db

# Option 2: PostgreSQL (recommended)
createdb rssbot
DATABASE_URL=postgresql://user:pass@localhost/rssbot
```

### Redis Setup

```bash
# Install Redis
# Ubuntu/Debian: apt install redis-server
# macOS: brew install redis
# Start Redis
redis-server
```

### Verify Setup

```bash
# Start the platform
python -m rssbot

# Check health
curl http://localhost:8004/health
```

## 🔄 Contributing Workflow

### 1. **Create a Feature Branch**

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# Or: git checkout -b fix/bug-description
# Or: git checkout -b docs/documentation-update
```

### 2. **Make Changes**

- Follow our [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 3. **Commit Changes**

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add service health monitoring dashboard

- Add real-time health status display
- Implement WebSocket updates for live data
- Add service restart functionality
- Update admin interface documentation

Fixes #123"
```

#### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): add service health endpoints
fix(redis): resolve connection timeout issue
docs: update installation guide
refactor(core): simplify service registry logic
```

### 4. **Push and Create PR**

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

## 📏 Coding Standards

### Python Code Style

We follow **PEP 8** with some modifications:

```python
# Line length: 120 characters
# String quotes: Double quotes preferred
# Import order: isort configuration in pyproject.toml

# Example function with proper typing
from typing import List, Dict, Optional, Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

async def process_services(
    service_names: List[str],
    connection_method: str = "router"
) -> Dict[str, Union[str, bool]]:
    """
    Process multiple services with specified connection method.

    Args:
        service_names: List of service names to process
        connection_method: Connection method ("router", "rest", "hybrid")

    Returns:
        Dictionary with processing results for each service

    Raises:
        HTTPException: If service configuration fails
    """
    results = {}

    for service_name in service_names:
        try:
            result = await configure_service(service_name, connection_method)
            results[service_name] = result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to configure {service_name}: {str(e)}"
            )
    return results
```

### Type Hints

**Required** for all public functions and methods:

```python
# Good
async def get_service_status(service_name: str) -> Optional[ServiceStatus]:
    pass

def calculate_health_score(
    metrics: Dict[str, float],
    weights: Optional[Dict[str, float]] = None
) -> float:
    pass

# Bad
async def get_service_status(service_name):
    pass
```

### Documentation Strings

Use **Google-style** docstrings:

```python
class ServiceRegistry:
    """
    Redis-backed service registry with database persistence.

    This class manages service discovery, health monitoring, and
    connection method configuration for the hybrid microservices platform.

    Attributes:
        redis_client: Redis client for caching
        db_session: Database session factory

    Example:
        ```python
        registry = ServiceRegistry()
        await registry.initialize()

        # Check if service should use router
        use_router = await registry.should_use_router("ai_svc")
        ```
    """

    async def should_use_router(self, service_name: str) -> bool:
        """
        Determine if service should use router connection method.

        Args:
            service_name: Name of the service (e.g., 'ai_svc')

        Returns:
            True if service should use router mode, False for REST

        Raises:
            ServiceNotFoundError: If service is not registered
            CacheConnectionError: If Redis is unavailable and DB fails
        """
        pass
```

### Error Handling

```python
from rssbot.core.exceptions import ServiceError, ServiceNotFoundError

# Custom exceptions
class ServiceConfigurationError(ServiceError):
    """Raised when service configuration is invalid."""
    pass

# Proper exception handling
async def configure_service(service_name: str, method: str) -> bool:
    try:
        service = await self.get_service(service_name)
        if not service:
            raise ServiceNotFoundError(f"Service {service_name} not found")

        # Configure service
        await service.set_connection_method(method)
    except ServiceNotFoundError:
        # Re-raise specific exceptions
        raise
    except Exception as e:
        # Wrap unexpected exceptions
        raise ServiceConfigurationError(
            f"Failed to configure {service_name}: {str(e)}"
        ) from e
```

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests for individual components
│   ├── test_registry.py
│   ├── test_proxy.py
│   └── test_controller.py
├── integration/       # Integration tests
│   ├── test_service_communication.py
│   └── test_api_endpoints.py
└── e2e/              # End-to-end tests
    └── test_platform_workflow.py
```

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, Mock
from rssbot.discovery.cached_registry import CachedServiceRegistry

class TestCachedServiceRegistry:
    """Test suite for CachedServiceRegistry."""
    @pytest.fixture
    async def registry(self):
        """Create test registry instance."""
        registry = CachedServiceRegistry()
        # Mock Redis for testing
        registry._redis = AsyncMock()
        registry._redis_available = True
        return registry
    @pytest.mark.asyncio
    async def test_should_use_router_returns_true_for_router_services(self, registry):
        """Test that router services return True for router decision."""
        # Arrange
        service_name = "test_svc"
        registry._get_cached_connection_method = AsyncMock(
            return_value=ConnectionMethod.ROUTER
        )

        # Act
        result = await registry.should_use_router(service_name)

        # Assert
        assert result is True
        registry._get_cached_connection_method.assert_called_once_with(service_name)

    @pytest.mark.asyncio
    async def test_cache_fallback_when_redis_unavailable(self, registry):
        """Test that system falls back to database when Redis is down."""
        # Arrange
        registry._redis_available = False
        mock_service = Mock()
        mock_service.get_effective_connection_method.return_value = ConnectionMethod.REST
        registry.registry_manager.get_service_by_name = AsyncMock(return_value=mock_service)

        # Act
        result = await registry.get_effective_connection_method("test_svc")

        # Assert
        assert result == ConnectionMethod.REST
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/rssbot --cov-report=html

# Run specific test file
pytest tests/unit/test_registry.py

# Run with verbose output
pytest -v

# Run only tests matching pattern
pytest -k "test_cache"
```

## 📚 Documentation

### Code Documentation

- **All public APIs** must have docstrings
- **Complex logic** should have inline comments
- **Examples** should be provided for public interfaces

### User Documentation

When updating user-facing features:

1. **Update relevant docs** in `docs/` directory
2. **Add examples** to README if applicable
3. **Update API documentation** in `docs/API.md`
4. **Add migration notes** if breaking changes

### Documentation Build

```bash
# Install docs dependencies
pip install mkdocs mkdocs-material

# Serve documentation locally
mkdocs serve

# Build documentation
mkdocs build
```

## 🔄 Pull Request Process

### Before Submitting

- [ ] **Tests pass**: `pytest`
- [ ] **Code formatted**: `black src/` and `isort src/`
- [ ] **Type checking**: `mypy src/rssbot`
- [ ] **Documentation updated** (if needed)
- [ ] **Changelog updated** (for significant changes)

### PR Template

When creating a PR, please include:

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added and passing
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **At least one maintainer** review required
3. **Address feedback** promptly and professionally
4. **Squash commits** before merge (if requested)

## 🐛 Issue Reporting

### Bug Reports

Please use the bug report template:

```markdown
**Describe the Bug**
Clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Start platform with '...'
2. Configure service with '...'
3. Send request to '...'
4. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.11.5]
- RssBot Version: [e.g., 2.0.0]
- Redis Version: [e.g., 7.0]

**Additional Context**
Add any other context, logs, or screenshots.
```

### Feature Requests

Use the feature request template:

```markdown
**Feature Summary**
Brief description of the feature.

**Motivation**
Why is this feature needed? What problem does it solve?

**Detailed Description**
Detailed description of the proposed feature.

**Possible Implementation**
Ideas for how this could be implemented.

**Alternatives Considered**
Other approaches you've considered.
```

## 🏷️ Release Process

### Version Numbers

We use [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 2.1.0)
- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes (backward compatible)

### Release Notes

Include in release notes:
- **New features** with examples
- **Bug fixes** with issue numbers
- **Breaking changes** with migration guide
- **Deprecations** with timeline
- **Performance improvements**

## 🏆 Recognition

Contributors will be recognized in:
- **README.md** contributors section
- **Release notes** for significant contributions
- **GitHub contributors** page
- **Special thanks** in documentation

## ❓ Getting Help

- **Discord**: Join our development Discord server
- **GitHub Discussions**: Ask questions and discuss ideas
- **Issues**: Report bugs and request features
- **Email**: maintainers@rssbot-platform.com

## 📞 Contact Maintainers

- **Lead Maintainer**: @username
- **Core Team**: @team-rssbot
- **Security Issues**: security@rssbot-platform.com

---

Thank you for contributing to RssBot Platform! 🚀