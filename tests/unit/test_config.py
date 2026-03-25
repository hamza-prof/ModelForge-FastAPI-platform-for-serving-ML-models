from unittest.mock import patch

import pytest
from pydantic import ValidationError


class TestSettings:
    """Tests for app.core.config.Settings"""

    def test_settings_loads_from_env(self):
        """Settings should load all values from environment variables."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/testdb",
            "SECRET_KEY": "test-secret-key-1234567890abcdef",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            from app.core.config import Settings

            s = Settings(_env_file=None)
            assert s.DATABASE_URL == env_vars["DATABASE_URL"]
            assert s.SECRET_KEY == env_vars["SECRET_KEY"]

    def test_missing_database_url_raises_error(self):
        """Settings should fail if DATABASE_URL is not provided."""
        env_vars = {
            "SECRET_KEY": "test-secret-key",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            from app.core.config import Settings

            with pytest.raises(ValidationError):
                Settings(_env_file=None)

    def test_missing_secret_key_raises_error(self):
        """Settings should fail if SECRET_KEY is not provided."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/testdb",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            from app.core.config import Settings

            with pytest.raises(ValidationError):
                Settings(_env_file=None)

    def test_default_values_applied(self):
        """Optional settings should use their defaults when not in env."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/testdb",
            "SECRET_KEY": "test-secret-key-1234567890abcdef",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            from app.core.config import Settings

            s = Settings(_env_file=None)
            assert s.APP_NAME == "ML Platform"
            assert s.ENVIRONMENT == "development"
            assert s.ALGORITHM == "HS256"
            assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 30
            assert s.REDIS_URL == "redis://localhost:6379"
            assert s.MAX_MODEL_SIZE_MB == 500

    def test_get_settings_is_cached(self):
        """get_settings() should return the same object on repeated calls."""
        from app.core.config import get_settings

        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
