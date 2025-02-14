"""Authentication middleware for the FastAPI application."""

import os
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

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
