from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables.

    Required variables (no default → must be in .env):
        - DATABASE_URL
        - SECRET_KEY

    All other variables have sensible defaults for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_NAME: str = "ML Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_URL: str = "redis://localhost:6379"

    MODEL_STORE_PATH: str = "./model_store"
    MAX_MODEL_SIZE_MB: int = 500

    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Using lru_cache means the .env file is read only once.
    To refresh settings in tests, call get_settings.cache_clear().
    """
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
