"""
EVIDRA Core Configuration Module.
Loads all environment variables with type-safe defaults.

Usage:
    from core.config import settings
    print(settings.DATABASE_URL)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    """Typed settings container. All values sourced from environment."""

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://evidra:evidra_secret@localhost:5432/evidra_db")
    DB_MIN_POOL: int = int(os.getenv("DB_MIN_POOL", "2"))
    DB_MAX_POOL: int = int(os.getenv("DB_MAX_POOL", "10"))

    # --- Redis ---
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # --- MinIO ---
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "evidra_minio")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "evidra_minio_secret")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "evidra-evidence")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # --- LLM ---
    FEATHERLESS_API_KEY: str = os.getenv("FEATHERLESS_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_MAX_CONCURRENT: int = int(os.getenv("LLM_MAX_CONCURRENT", "5"))
    LLM_MAX_TOKENS_PER_RUN: int = int(os.getenv("LLM_MAX_TOKENS_PER_RUN", "100000"))
    LLM_RATE_LIMIT_RPM: int = int(os.getenv("LLM_RATE_LIMIT_RPM", "60"))

    # --- JWT ---
    JWT_SECRET: str = os.getenv("JWT_SECRET", "evidra-super-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

    # --- App ---
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
