"""
Central configuration for Orange Systems Sales Intelligence Platform.
"""
import os

STRICT_PRODUCTION: bool = os.getenv("STRICT_PRODUCTION", "false").lower() in ("true", "1", "yes")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
REDIS_URL: str = os.getenv("REDIS_URL", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
