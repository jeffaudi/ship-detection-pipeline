"""Middleware classes for the FastAPI application."""

import gzip
import os
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
API_KEY = os.getenv("API_KEY", "")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to check for valid API key in request headers."""

    async def dispatch(self, request: Request, call_next):
        # Skip API key check for health check endpoint
        if request.url.path in ["/health", "/", "/favicon.ico"]:
            return await call_next(request)

        # Get API key from environment
        API_KEY = os.getenv("API_KEY")

        # Get API key from request header
        request_api_key = request.headers.get("X-API-Key")

        if not request_api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "API key missing",
                    "message": "Please provide an API key in the X-API-Key header",
                },
            )
        if API_KEY.strip() != request_api_key.strip():
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Invalid API key",
                    "message": "The provided API key is not valid",
                },
            )

        return await call_next(request)


class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware for compressing responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Compress response if client accepts gzip encoding."""
        response = await call_next(request)

        if "gzip" in request.headers.get("Accept-Encoding", "").lower():
            if hasattr(response, "body"):
                # Compress response body
                compressed_data = gzip.compress(response.body)
                return Response(
                    content=compressed_data,
                    status_code=response.status_code,
                    headers={
                        **response.headers,
                        "Content-Encoding": "gzip",
                        "Content-Length": str(len(compressed_data)),
                        "Vary": "Accept-Encoding",
                    },
                )

        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware for setting cache control headers."""

    def __init__(
        self,
        app: ASGIApp,
        max_age: int = 3600,  # 1 hour default
        include_paths: list = None,
    ):
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            max_age: Maximum age for cache in seconds.
            include_paths: List of paths to apply caching to.
        """
        super().__init__(app)
        self.max_age = max_age
        self.include_paths = include_paths or ["/tiles/", "/info/", "/preview/"]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Set cache control headers for configured paths."""
        response = await call_next(request)

        # Check if the path should be cached
        should_cache = any(
            request.url.path.startswith(path) for path in self.include_paths
        )

        if should_cache:
            response.headers["Cache-Control"] = f"public, max-age={self.max_age}"
            response.headers["Vary"] = "Accept-Encoding"

        return response
