"""Configuration module for the application."""

import os
from typing import Optional

from dotenv import load_dotenv


def is_production() -> bool:
    """Check if the application is running in production (Cloud Run)."""
    return os.getenv("K_SERVICE") is not None


def get_config() -> dict:
    """Get configuration based on the environment.

    In development: Load from .env file
    In production: Use environment variables (set by Cloud Run from Secret Manager)
    """
    config = {}

    # Only load .env file in development
    if not is_production():
        load_dotenv()

    # Required configuration
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "CDSE_USERNAME",
        "CDSE_PASSWORD",
        "API_KEY",
    ]

    # Optional configuration with defaults
    optional_vars = {
        "FLASK_ENV": "production" if is_production() else "development",
        "FLASK_DEBUG": "0" if is_production() else "1",
    }

    # Get required variables and strip whitespace
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value is None:
            missing_vars.append(var)
        else:
            # Strip whitespace from all environment variables
            config[var] = value.strip()

    # If in production, all required variables must be set
    if is_production() and missing_vars:
        raise ValueError(
            f"Missing required environment variables in production: {', '.join(missing_vars)}"
        )

    # Get optional variables with defaults
    for var, default in optional_vars.items():
        config[var] = os.getenv(var, default).strip()

    return config


class Config:
    """Configuration class for environment variables."""

    _config: Optional[dict] = None
    _instance = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get(cls) -> dict:
        """Get the configuration dictionary, initializing it if necessary."""
        if cls._config is None:
            cls._config = get_config()
        return cls._config

    @classmethod
    def get_required(cls, key: str) -> str:
        """Get a required configuration value.

        Args:
            key: The configuration key to get.

        Returns:
            The configuration value.

        Raises:
            ValueError: If the configuration value is not set.
        """
        value = cls.get().get(key)
        if value is None:
            raise ValueError(f"Required configuration '{key}' is not set")
        return value

    @classmethod
    def get_optional(cls, key: str, default: str = "") -> str:
        """Get an optional configuration value with a default."""
        return cls.get().get(key, default)

    # Static properties for direct access (for backward compatibility)
    SUPABASE_URL = property(lambda _: Config.get_required("SUPABASE_URL"))
    SUPABASE_KEY = property(lambda _: Config.get_required("SUPABASE_KEY"))
    CDSE_USERNAME = property(lambda _: Config.get_required("CDSE_USERNAME"))
    CDSE_PASSWORD = property(lambda _: Config.get_required("CDSE_PASSWORD"))
    API_KEY = property(lambda _: Config.get_required("API_KEY"))
    SECRET_KEY = property(lambda _: Config.get_optional("SECRET_KEY", "dev"))
    MODAL_TOKEN = property(lambda _: Config.get_optional("MODAL_TOKEN"))

    # Class methods for static access
    @classmethod
    def get_supabase_url(cls) -> str:
        """Get the Supabase URL."""
        return cls.get_required("SUPABASE_URL")

    @classmethod
    def get_supabase_key(cls) -> str:
        """Get the Supabase key."""
        return cls.get_required("SUPABASE_KEY")

    @classmethod
    def get_cdse_username(cls) -> str:
        """Get the CDSE username."""
        return cls.get_required("CDSE_USERNAME")

    @classmethod
    def get_cdse_password(cls) -> str:
        """Get the CDSE password."""
        return cls.get_required("CDSE_PASSWORD")

    @classmethod
    def get_api_key(cls) -> str:
        """Get the API key."""
        return cls.get_required("API_KEY")


def get_api_key() -> Optional[str]:
    """Get the API key from environment variables.

    Returns:
        The API key if configured, None otherwise.
    """
    api_key = os.getenv("API_KEY")
    if not api_key:
        # In production (e.g. Cloud Run), we require an API key
        if os.getenv("ENVIRONMENT") == "production":
            raise ValueError("API_KEY environment variable must be set in production")
        # In development, we warn but allow running without an API key
        print("WARNING: API_KEY environment variable not set. API authentication is disabled.")
    return api_key
