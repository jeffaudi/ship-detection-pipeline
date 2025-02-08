"""CORS configuration for the API."""

from flask import Flask
from flask_cors import CORS


def configure_cors(app: Flask) -> None:
    """Configure CORS for the Flask application.

    Args:
        app: The Flask application instance.
    """
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:5173",  # Vite dev server
                    "http://localhost:4173",  # Vite preview server
                    "http://localhost:8080",  # Vue CLI dev server
                    "https://ship-pipeline-web-577713910386.europe-west1.run.app",  # Production
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
                "supports_credentials": True,
            }
        },
        expose_headers=["Access-Control-Allow-Origin"],
    )
