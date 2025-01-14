"""Unit tests for the SentinelService."""

from datetime import datetime

import pytest
from src.services.sentinel_service import SentinelService


@pytest.fixture
def sentinel_service():
    """Create a test instance of SentinelService."""
    return SentinelService()


def test_bbox_to_wkt(sentinel_service):
    """Test conversion of bbox to WKT format."""
    bbox = {"south": -15.0, "west": 40.0, "north": -8.0, "east": 47.0}
    wkt = sentinel_service._bbox_to_wkt(bbox)
    expected = "POLYGON((40.0 -15.0, 47.0 -15.0, 47.0 -8.0, 40.0 -8.0, 40.0 -15.0))"
    # Remove whitespace for comparison
    assert wkt.replace(" ", "") == expected.replace(" ", "")


def test_search_images(sentinel_service, mocker):
    """Test searching for Sentinel images."""
    # Mock the Sentinel API query response
    mock_products = {
        "product1": {
            "title": "Test Image 1",
            "beginposition": datetime(2024, 1, 1),
            "cloudcoverpercentage": 10.5,
        }
    }
    mocker.patch.object(sentinel_service.sentinel_api, "query", return_value=mock_products)

    # Mock Supabase upsert
    mock_upsert = mocker.MagicMock()
    mocker.patch.object(
        sentinel_service.supabase.table("sentinel_images"), "upsert", return_value=mock_upsert
    )

    # Test parameters
    bbox = [[-15.0, 40.0], [-8.0, 47.0]]
    date_from = "2024-01-01"
    date_to = "2024-01-10"
    cloud_cover = 20

    # Call the method
    results = sentinel_service.search_images(bbox, date_from, date_to, cloud_cover)

    # Verify results
    assert len(results) == 1
    assert results[0]["title"] == "Test Image 1"
    assert results[0]["cloud_cover"] == 10.5

    # Verify API was called with correct parameters
    sentinel_service.sentinel_api.query.assert_called_once()
    call_args = sentinel_service.sentinel_api.query.call_args[1]
    assert call_args["platformname"] == "Sentinel-2"
    assert call_args["cloudcoverpercentage"] == (0, cloud_cover)


def test_get_metadata(sentinel_service, mocker):
    """Test getting image metadata."""
    # Mock Supabase response
    mock_data = {
        "id": "test_id",
        "title": "Test Image",
        "timestamp": "2024-01-01T00:00:00",
        "cloud_cover": 10.5,
        "metadata": {},
    }
    mock_response = mocker.MagicMock()
    mock_response.data = mock_data
    mocker.patch.object(
        sentinel_service.supabase.table("sentinel_images"),
        "select",
        return_value=mocker.MagicMock(
            eq=mocker.MagicMock(
                single=mocker.MagicMock(execute=mocker.MagicMock(return_value=mock_response))
            )
        ),
    )

    # Test getting metadata
    result = sentinel_service.get_metadata("test_id")

    # Verify results
    assert result == mock_data
    assert result["title"] == "Test Image"
    assert result["cloud_cover"] == 10.5
