"""Configuration module for the application."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for environment variables."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    CDSE_USERNAME = os.getenv("CDSE_USERNAME")
    CDSE_PASSWORD = os.getenv("CDSE_PASSWORD")
    MODAL_TOKEN = os.getenv("MODAL_TOKEN")
