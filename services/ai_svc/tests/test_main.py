
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Make sure the app can be imported
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app, usage_storage, AIResponse

client = TestClient(app)

# A mock service token for testing
SERVICE_TOKEN = "test_service_token"
os.environ["SERVICE_TOKEN"] = SERVICE_TOKEN
HEADERS = {"X-Service-Token": SERVICE_TOKEN}

@pytest.fixture(autouse=True)
def clear_storage():
    """Clear in-memory usage storage before each test."""
    usage_storage.clear()

@pytest.fixture
def mock_openai():
    """Fixture to mock the call_openai_api function."""
    with patch("main.call_openai_api", new_callable=AsyncMock) as mock_api:
        yield mock_api

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "ai_svc"

def test_call_ai_success(mock_openai):
    # Arrange
    mock_openai.return_value = {
        "result": "Mocked AI response",
        "model": "gpt-3.5-turbo",
        "tokens_used": 50,
        "mock": True
    }
    request_data = {
        "prompt": "Test prompt",
        "content": "Test content",
        "user_id": 1
    }

    # Act
    response = client.post("/call", json=request_data, headers=HEADERS)

    # Assert
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["result"] == "Mocked AI response"
    mock_openai.assert_called_once()

def test_call_ai_quota_exceeded(mock_openai):
    # Arrange
    from main import UsageStats
    usage_storage[1] = UsageStats(
        user_id=1,
        total_requests=10,
        total_tokens=1000,
        requests_today=10,
        tokens_today=1000,
        quota_remaining=0
    )
    request_data = {
        "prompt": "Test prompt",
        "content": "Test content",
        "user_id": 1
    }

    # Act
    response = client.post("/call", json=request_data, headers=HEADERS)

    # Assert
    assert response.status_code == 429
    mock_openai.assert_not_called()

@patch("main.call_ai", new_callable=AsyncMock)
def test_summarize_content(mock_call_ai):
    # Arrange
    mock_response = AIResponse(
        result="Mocked summary",
        model_used="gpt-3.5-turbo-mock",
        tokens_used=25,
        processing_time=0.1,
        metadata={"test": True}
    )
    mock_call_ai.return_value = mock_response

    request_data = {
        "content": "This is a long text to be summarized.",
        "max_length": 50
    }

    # Act
    response = client.post("/summarize", json=request_data, headers=HEADERS)

    # Assert
    assert response.status_code == 200
    assert response.json()['result'] == "Mocked summary"
    mock_call_ai.assert_called_once()

def test_invalid_service_token():
    response = client.post("/call", json={}, headers={"X-Service-Token": "invalid_token"})
    assert response.status_code == 401
