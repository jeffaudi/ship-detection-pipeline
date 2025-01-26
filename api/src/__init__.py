"""Initialization module for the API package."""

from typing import Tuple, Union

from flask import Flask, request
from flask_cors import CORS

from .routes import api_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configure CORS
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:5173",  # Vite dev server
                    "http://localhost:8080",  # Vue CLI dev server
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True,
            }
        },
        expose_headers=["Access-Control-Allow-Origin"],
    )

    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")

    # Add OPTIONS handler
    @app.before_request
    def handle_options() -> Union[None, Tuple[str, int]]:
        """Handle OPTIONS requests."""
        if request.method == "OPTIONS":
            return "", 200
        return None

    return app
