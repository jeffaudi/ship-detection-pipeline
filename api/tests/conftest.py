"""Configuration for pytest fixtures."""

import pytest
from src import create_app


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )
    return app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def sentinel_service():
    """Create a test instance of SentinelService."""
    from src.services.sentinel_service import SentinelService

    return SentinelService()
