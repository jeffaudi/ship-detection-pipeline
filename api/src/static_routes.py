"""Static routes for the API."""

from flask import Flask, send_from_directory


def configure_static_routes(app: Flask) -> None:
    """Configure static routes for the Flask application.

    Args:
        app: The Flask application instance.
    """

    @app.route("/favicon.ico")
    def favicon():
        """Serve the favicon."""
        return send_from_directory(
            app.root_path + "/static",
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )
