"""Initialization module for the API package."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .cors import configure_cors
from .routes import api_bp, configure_options_handler
from .static_routes import configure_static_routes


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configure components
    configure_cors(app)
    configure_static_routes(app)
    configure_options_handler(app)

    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")

    # Register error handlers
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle HTTP exceptions and return JSON response."""
        response = {"error": error.__class__.__name__, "message": error.description}
        return jsonify(response), error.code

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """Handle any other exceptions and return JSON response."""
        response = {"error": "InternalServerError", "message": str(error)}
        return jsonify(response), 500

    return app
