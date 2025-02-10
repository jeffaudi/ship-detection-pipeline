""" Enforce API key validation for protected routes. """

from functools import wraps

from flask import jsonify, request

from .config import get_api_key


def require_api_key(f):
    """Decorator to require API key for routes.

    Args:
        f: The function to wrap.

    Returns:
        The wrapped function that checks for API key authentication.

    Raises:
        Unauthorized: If no API key is provided in the request.
        Forbidden: If an invalid API key is provided.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth for health check endpoint
        if request.path == "/health":
            return f(*args, **kwargs)

        api_key = get_api_key()
        if not api_key:
            # If no API key is configured, skip authentication
            return f(*args, **kwargs)

        # Check request header for API key
        request_api_key = request.headers.get("X-API-Key")
        if not request_api_key:
            return (
                jsonify(
                    {
                        "error": "API key missing",
                        "message": "Please provide an API key in the X-API-Key header",
                    }
                ),
                401,
            )

        if request_api_key.strip() != api_key.strip():
            return (
                jsonify(
                    {
                        "error": "Invalid API key",
                        "message": "The provided API key is not valid",
                    }
                ),
                403,
            )
        return f(*args, **kwargs)

    return decorated_function
