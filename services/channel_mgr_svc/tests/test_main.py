
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Make sure the app can be imported
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)

# A mock service token for testing
SERVICE_TOKEN = "test_service_token"
os.environ["SERVICE_TOKEN"] = SERVICE_TOKEN
HEADERS = {"X-Service-Token": SERVICE_TOKEN}

@pytest.fixture(autouse=True)
def manage_background_task():
    """Fixture to start and stop the background task for tests."""
    with patch("main.feed_monitoring_loop", new_callable=AsyncMock):
        yield

@pytest.fixture(autouse=True)
def clear_storage():
    """Clear in-memory storage before each test and after."""
    from main import channels_storage, feeds_storage

    channels_storage.clear()
    feeds_storage.clear()

    globals_to_reset = {'channel_id_counter': 1, 'feed_id_counter': 1}
    for var, value in globals_to_reset.items():
        if hasattr(sys.modules['main'], var):
            setattr(sys.modules['main'], var, value)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
@patch("main.test_rss_feed", new_callable=AsyncMock)
async def test_create_feed_invalid_rss(mock_test_rss_feed):
    # Arrange
    channel_data = {"telegram_id": 12345, "title": "Test Channel", "owner_id": 1}
    response = client.post("/channels", json=channel_data, headers=HEADERS)
    assert response.status_code == 200
    channel_id = response.json()["id"]

    mock_test_rss_feed.return_value = {"valid": False}

    # Act
    feed_data = {"url": "http://invalid-rss.com", "channel_id": channel_id}
    response = client.post("/feeds", json=feed_data, headers=HEADERS)

    # Assert
    assert response.status_code == 400
    assert "Invalid RSS feed" in response.json()["detail"]

def test_create_feed_for_nonexistent_channel():
    feed_data = {"url": "http://example.com/rss", "channel_id": 999}
    response = client.post("/feeds", json=feed_data, headers=HEADERS)
    assert response.status_code == 404

@patch("main.check_feed_for_updates", new_callable=AsyncMock)
def test_check_feed_now_endpoint(mock_check_feed):
    # Arrange
    channel_data = {"telegram_id": 123, "title": "Test", "owner_id": 1}
    channel_res = client.post("/channels", json=channel_data, headers=HEADERS)
    assert channel_res.status_code == 200
    channel_id = channel_res.json()["id"]

    with patch("main.test_rss_feed", new_callable=AsyncMock) as mock_test_feed:
        mock_test_feed.return_value = {"valid": True, "title": "Test Feed"}
        feed_data = {"url": "http://test.com/rss", "channel_id": channel_id}
        feed_res = client.post("/feeds", json=feed_data, headers=HEADERS)
        assert feed_res.status_code == 200
        feed_id = feed_res.json()["id"]

    mock_check_feed.return_value = [{"title": "New Post", "link": "http://test.com/post"}]

    # Act
    response = client.get(f"/feeds/{feed_id}/check", headers=HEADERS)

    # Assert
    assert response.status_code == 200
    assert response.json()["new_items"] == 1
    mock_check_feed.assert_called_once()
