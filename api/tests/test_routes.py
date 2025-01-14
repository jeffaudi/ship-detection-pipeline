"""Unit tests for the API routes."""

import json

from src.services.sentinel_service import SentinelService  # Adjusted import


def test_search_images_route(client, mocker):
    """Test the /api/sentinel/search endpoint."""
    # Mock the sentinel service
    mock_results = [
        {
            "id": "test_id",
            "title": "Test Image",
            "timestamp": "2024-01-01T00:00:00",
            "cloud_cover": 10.5,
            "metadata": {},
        }
    ]

    mocker.patch("src.routes.sentinel_service.search_images", return_value=mock_results)

    # Test data
    data = {
        "bbox": [[-15.0, 40.0], [-8.0, 47.0]],
        "date_from": "2024-01-01",
        "date_to": "2024-01-10",
        "cloud_cover": 20,
    }

    # Make request
    response = client.post(
        "/api/sentinel/search", data=json.dumps(data), content_type="application/json"
    )

    # Check response
    assert response.status_code == 200
    result = json.loads(response.data)
    assert len(result) == 1
    assert result[0]["title"] == "Test Image"
    assert result[0]["cloud_cover"] == 10.5


def test_search_images_invalid_bbox(client):
    """Test the /api/sentinel/search endpoint with invalid bbox."""
    data = {
        "bbox": [[-15.0], [-8.0, 47.0]],  # Invalid format
        "date_from": "2024-01-01",
        "date_to": "2024-01-10",
        "cloud_cover": 20,
    }

    # Make request
    response = client.post(
        "/api/sentinel/search", data=json.dumps(data), content_type="application/json"
    )

    # Check response
    assert response.status_code == 400
    result = json.loads(response.data)
    assert "error" in result
    assert "Invalid bbox format" in result["error"]


def test_get_image_metadata(client, mocker):
    """Test the /api/sentinel/<image_id> endpoint."""
    # Mock data
    mock_metadata = {
        "id": "test_id",
        "title": "Test Image",
        "timestamp": "2024-01-01T00:00:00",
        "cloud_cover": 10.5,
        "metadata": {},
    }

    mocker.patch("src.routes.sentinel_service.get_metadata", return_value=mock_metadata)

    # Make request
    response = client.get("/api/sentinel/test_id")

    # Check response
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result["title"] == "Test Image"
    assert result["id"] == "test_id"
    assert result["cloud_cover"] == 10.5


def test_cors_headers(client):
    """Test that CORS headers are properly set."""
    response = client.options("/api/sentinel/search")
    headers = response.headers

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in headers
    assert "Access-Control-Allow-Methods" in headers
    assert "Access-Control-Allow-Headers" in headers


def test_health_check(client, mocker):
    """Test the /api/health endpoint."""
    # Mock Sentinel API
    mocker.patch("src.routes.sentinel_service.sentinel_api.get_products_size", return_value=100)

    # Mock Supabase
    mock_execute = mocker.MagicMock()
    mocker.patch.object(
        SentinelService.supabase.table("sentinel_images"),
        "select",
        return_value=mocker.MagicMock(limit=mocker.MagicMock(execute=mock_execute)),
    )

    # Make request
    response = client.get("/api/health")

    # Check response
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result["status"] == "healthy"
    assert result["services"]["api"] is True
    assert result["services"]["sentinel_api"] is True
    assert result["services"]["supabase"] is True
    assert "version" in result


def test_health_check_service_failure(client, mocker):
    """Test the /api/health endpoint when services are down."""
    # Mock Sentinel API failure
    mocker.patch(
        "src.routes.sentinel_service.sentinel_api.get_products_size",
        side_effect=Exception("Sentinel API error"),
    )

    # Mock Supabase failure
    mock_execute = mocker.MagicMock(side_effect=Exception("Supabase error"))
    mocker.patch.object(
        SentinelService.supabase.table("sentinel_images"),
        "select",
        return_value=mocker.MagicMock(limit=mocker.MagicMock(execute=mock_execute)),
    )

    # Make request
    response = client.get("/api/health")

    # Check response
    assert response.status_code == 200  # Still returns 200 as the API itself is up
    result = json.loads(response.data)
    assert result["status"] == "healthy"  # API is still healthy
    assert result["services"]["api"] is True
    assert result["services"]["sentinel_api"] is False
    assert result["services"]["supabase"] is False
