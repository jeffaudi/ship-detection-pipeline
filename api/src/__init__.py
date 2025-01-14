"""Initialization module for the API package."""

from flask import Flask, request
from flask_cors import CORS

from .routes import api_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configure CORS
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ["http://localhost:5173"],  # Frontend dev server
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
    def handle_options():
        """Handle OPTIONS requests."""
        if request.method == "OPTIONS":
            return "", 200

    return app
