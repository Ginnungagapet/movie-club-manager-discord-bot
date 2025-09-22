"""
Configuration management for the Movie Club Bot
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings and configuration"""

    def __init__(self):
        # Discord Configuration
        self.discord_token: str = self._get_required_env("DISCORD_TOKEN")
        self.command_prefix: str = os.getenv("COMMAND_PREFIX", "!")

        # Database Configuration
        self.database_url: str = self._get_required_env("DATABASE_URL")

        # Movie Search Configuration
        self.imdb_cache_timeout: int = int(os.getenv("IMDB_CACHE_TIMEOUT", "3600"))
        self.max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))

        # Rotation Configuration
        self.rotation_period_days: int = int(os.getenv("ROTATION_PERIOD_DAYS", "14"))
        self.early_access_days: int = int(os.getenv("EARLY_ACCESS_DAYS", "7"))

        # Rating Configuration
        self.min_rating: float = float(os.getenv("MIN_RATING", "1.0"))
        self.max_rating: float = float(os.getenv("MAX_RATING", "10.0"))

        # Logging Configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.debug_mode: bool = os.getenv("DEBUG", "False").lower() == "true"

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    @property
    def database_url_corrected(self) -> str:
        """Get database URL with postgres:// corrected to postgresql://"""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    def __repr__(self):
        return f"<Settings(prefix='{self.command_prefix}', debug={self.debug_mode})>"
