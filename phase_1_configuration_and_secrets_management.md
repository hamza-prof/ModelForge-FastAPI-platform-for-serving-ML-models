# Phase 1 — Configuration & Secrets Management

> **Goal:** Never hardcode secrets. Every environment-specific value lives in `.env` and is loaded
> through a single, type-safe `Settings` class using `pydantic-settings`.

---

## Table of Contents

1. [Subtask 1.1 — Install Required Dependency](#subtask-11--install-required-dependency)
2. [Subtask 1.2 — Create the Settings Class (`app/core/config.py`)](#subtask-12--create-the-settings-class-appcoreconfighpy)
3. [Subtask 1.3 — Create the `.env.example` Template](#subtask-13--create-the-envexample-template)
4. [Subtask 1.4 — Validate & Secure the `.env` File](#subtask-14--validate--secure-the-env-file)
5. [Subtask 1.5 — Create `.gitignore`](#subtask-15--create-gitignore)
6. [Subtask 1.6 — Create Custom Exceptions (`app/core/exceptions.py`)](#subtask-16--create-custom-exceptions-appcoreexceptionspy)
7. [Subtask 1.7 — Wire Settings into the App Entry Point (`app/main.py`)](#subtask-17--wire-settings-into-the-app-entry-point-appmainpy)
8. [Subtask 1.8 — Write Unit Tests for Configuration](#subtask-18--write-unit-tests-for-configuration)
9. [Subtask 1.9 — Verification & Smoke Test](#subtask-19--verification--smoke-test)

---

## Subtask 1.1 — Install Required Dependency

### What
Ensure the `pydantic-settings` package is installed. This package provides the `BaseSettings` class that reads values from environment variables and `.env` files with full Pydantic validation.

### Why
`pydantic-settings` was separated from Pydantic v2 into its own package. Without it, `from pydantic_settings import BaseSettings` will raise an `ImportError`.

### Steps
```bash
poetry add pydantic-settings
```

### Verification
Run `poetry show pydantic-settings` and confirm it appears in `pyproject.toml` under `[tool.poetry.dependencies]`.

### Current Status
✅ Already present in `pyproject.toml` as `pydantic-settings = "2.13.1"`. **No action needed.**

---

## Subtask 1.2 — Create the Settings Class (`app/core/config.py`)

### What
Create the central configuration module that reads all environment variables, validates their types, and provides typed access throughout the application.

### Why
- **Type Safety:** Pydantic validates every config value at startup. A missing `DATABASE_URL` will crash immediately with a clear error instead of silently failing at runtime.
- **Single Source of Truth:** Every module imports `settings` from this file instead of reading `os.getenv()` scattered across the codebase.
- **Caching:** The `@lru_cache` decorator ensures the `Settings` object is created only once, even if `get_settings()` is called many times.

### File: `app/core/config.py`

```python
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

    # ── App Metadata ──────────────────────────────────────────────
    APP_NAME: str = "ML Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── Database ──────────────────────────────────────────────────
    DATABASE_URL: str  # REQUIRED — no default, enforces explicit config
    # Example: postgresql+asyncpg://mluser:mlpassword@localhost:5432/mlplatform

    # ── Security / JWT ────────────────────────────────────────────
    SECRET_KEY: str  # REQUIRED — generate with: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Redis ─────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── ML Model Storage ──────────────────────────────────────────
    MODEL_STORE_PATH: str = "./model_store"
    MAX_MODEL_SIZE_MB: int = 500

    # ── CORS ──────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Using lru_cache means the .env file is read only once.
    To refresh settings in tests, call get_settings.cache_clear().
    """
    return Settings()


# Module-level convenience — import this directly:
#   from app.core.config import settings
settings = get_settings()
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| `DATABASE_URL` and `SECRET_KEY` have **no default** | Forces the developer to explicitly set them. Prevents accidental use of insecure defaults in production. |
| `@lru_cache` on `get_settings()` | The `.env` file is read and parsed only once. Subsequent calls return the cached object. |
| `case_sensitive=True` | Environment variables are case-sensitive on Linux. Prevents subtle bugs across OS. |
| `model_config` via `SettingsConfigDict` | Pydantic v2 style — avoids the deprecated inner `class Config`. |

### Depends On
- `pydantic-settings` (Subtask 1.1)

---

## Subtask 1.3 — Create the `.env.example` Template

### What
Create a committed template file that documents every required and optional environment variable.

### Why
- New developers can `copy .env.example .env` and immediately know what to fill in.
- It serves as living documentation of the application's configuration surface.
- It is **always committed** to version control (unlike `.env`).

### File: `.env.example`

```env
# ──────────────────────────────────────────────────────────────────
# ML Platform — Environment Configuration Template
# ──────────────────────────────────────────────────────────────────
# Copy this file to .env and fill in real values:
#   cp .env.example .env
# ──────────────────────────────────────────────────────────────────

# ── App ───────────────────────────────────────────────────────────
APP_NAME=ML Platform
APP_VERSION=1.0.0
ENVIRONMENT=development

# ── Database (REQUIRED) ──────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://mluser:mlpassword@localhost:5432/mlplatform

# ── Security (REQUIRED) ──────────────────────────────────────────
# Generate a secure key: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=CHANGE-ME-generate-a-real-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Redis ─────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ── ML Model Storage ─────────────────────────────────────────────
MODEL_STORE_PATH=./model_store
MAX_MODEL_SIZE_MB=500

# ── CORS ──────────────────────────────────────────────────────────
ALLOWED_ORIGINS=["http://localhost:3000"]
```

### Depends On
- Nothing

---

## Subtask 1.4 — Validate & Secure the `.env` File

### What
Review and update the existing `.env` file to ensure:
1. It contains all required variables that match the `Settings` class.
2. The `SECRET_KEY` placeholder is replaced with a **real** randomly generated value.

### Why
The current `.env` has `SECRET_KEY=your-secret-key-here-generate-with-openssl` which is insecure. This must be replaced with a real cryptographic key before any JWT tokens are created.

### Steps

1. **Generate a real secret key:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Copy the output** and replace the `SECRET_KEY` value in `.env`.

3. **Verify all variables match** the `Settings` class definition (cross-reference Subtask 1.2).

### Current `.env` Status

| Variable | Present? | Valid? |
|---|---|---|
| `APP_NAME` | ✅ | ✅ |
| `APP_VERSION` | ✅ | ✅ |
| `ENVIRONMENT` | ✅ | ✅ |
| `DATABASE_URL` | ✅ | ✅ (placeholder credentials) |
| `SECRET_KEY` | ✅ | ❌ Placeholder — must be replaced |
| `ALGORITHM` | ✅ | ✅ |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ | ✅ |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ✅ | ✅ |
| `REDIS_URL` | ✅ | ✅ |
| `MODEL_STORE_PATH` | ✅ | ✅ |
| `MAX_MODEL_SIZE_MB` | ✅ | ✅ |
| `ALLOWED_ORIGINS` | ✅ | ✅ |

### Depends On
- Subtask 1.2 (to know which fields exist)

---

## Subtask 1.5 — Create `.gitignore`

### What
Create a comprehensive `.gitignore` file to prevent secrets, caches, and build artifacts from being committed.

### Why
- `.env` contains secrets and must never be committed.
- `__pycache__/`, `.ruff_cache/`, `.mypy_cache/`, `model_store/` are generated files that pollute the repo.
- IDE folders (`.vscode/`, `.idea/`) are developer-specific.

### File: `.gitignore`

```gitignore
# ── Secrets ───────────────────────────────────────────────────────
.env

# ── Python ────────────────────────────────────────────────────────
__pycache__/
*.py[cod]
*.pyo
*.egg-info/
dist/
build/
*.egg

# ── Virtual Environments ─────────────────────────────────────────
.venv/
venv/

# ── Tool Caches ───────────────────────────────────────────────────
.ruff_cache/
.mypy_cache/
.pytest_cache/

# ── IDE ───────────────────────────────────────────────────────────
.vscode/
.idea/
*.swp
*.swo

# ── ML Model Storage (large binaries) ────────────────────────────
model_store/*.pkl
model_store/*.pt
model_store/*.onnx
model_store/*.joblib

# ── OS ────────────────────────────────────────────────────────────
.DS_Store
Thumbs.db
```

### Depends On
- Nothing

---

## Subtask 1.6 — Create Custom Exceptions (`app/core/exceptions.py`)

### What
Define a base set of custom exception classes that the entire application will use. These exceptions will be caught by a global exception handler and converted into consistent API error responses.

### Why
- Using generic `HTTPException` everywhere mixes HTTP concerns into the service layer.
- Custom exceptions let the service layer raise meaningful errors (e.g., `ModelNotFoundError`) without knowing about HTTP status codes.
- A global handler translates these into JSON API responses.

### File: `app/core/exceptions.py`

```python
"""
Custom exception hierarchy for the ML Platform.

Usage:
    - Services raise these exceptions for business logic errors.
    - A global exception handler in main.py converts them to HTTP responses.
"""


class MLPlatformError(Exception):
    """Base exception for all application errors."""

    def __init__(self, detail: str = "An unexpected error occurred"):
        self.detail = detail
        super().__init__(self.detail)


class NotFoundError(MLPlatformError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} with id '{identifier}' not found")


class AlreadyExistsError(MLPlatformError):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource: str, field: str, value: str):
        super().__init__(f"{resource} with {field} '{value}' already exists")


class AuthenticationError(MLPlatformError):
    """Raised when authentication fails (bad credentials, expired token)."""

    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(detail)


class AuthorizationError(MLPlatformError):
    """Raised when an authenticated user lacks permission."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(detail)


class ValidationError(MLPlatformError):
    """Raised when input data fails business-level validation."""

    def __init__(self, detail: str):
        super().__init__(detail)


class ModelLoadError(MLPlatformError):
    """Raised when an ML model file cannot be loaded or deserialized."""

    def __init__(self, model_name: str, reason: str):
        super().__init__(f"Failed to load model '{model_name}': {reason}")
```

### Depends On
- Nothing

---

## Subtask 1.7 — Wire Settings into the App Entry Point (`app/main.py`)

### What
Create a minimal `app/main.py` with the FastAPI app factory pattern that:
1. Imports and uses the `settings` object.
2. Conditionally exposes Swagger docs based on the `ENVIRONMENT` setting.
3. Registers a global exception handler for custom exceptions.
4. Includes a basic `/health` endpoint to verify the config is loaded.

### Why
This is the first place where `config.py` is actually used. Without this, there is no way to verify that the Settings class loads correctly.

### File: `app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    MLPlatformError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown logic.
    Lifespan replaces the deprecated @app.on_event("startup").
    """
    # Startup: Future phases will add DB init, model registry loading, etc.
    yield
    # Shutdown: Future phases will add engine.dispose(), registry.clear(), etc.


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # ── CORS Middleware ───────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global Exception Handlers ─────────────────────────────────
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(status_code=401, content={"detail": exc.detail})

    @app.exception_handler(AuthorizationError)
    async def authz_error_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @app.exception_handler(MLPlatformError)
    async def generic_error_handler(request: Request, exc: MLPlatformError):
        return JSONResponse(status_code=500, content={"detail": exc.detail})

    # ── Health Check ──────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    return app


app = create_app()
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| `docs_url=None` in production | Prevents exposing internal API structure in production environments. |
| Global exception handlers | Catches custom exceptions from the service layer and returns consistent JSON responses. More specific handlers (404, 401, 403) are registered before the generic 500 handler. |
| `/health` endpoint | Returns app metadata from `settings` — serves as a smoke test that config is loaded correctly and can be used by load balancers. |
| App factory pattern | Makes the app testable — you can call `create_app()` in tests to get an isolated instance. |

### Depends On
- Subtask 1.2 (`config.py`)
- Subtask 1.6 (`exceptions.py`)

---

## Subtask 1.8 — Write Unit Tests for Configuration

### What
Write tests that verify:
1. The `Settings` class can be instantiated with valid environment variables.
2. Missing required variables (`DATABASE_URL`, `SECRET_KEY`) raise a validation error.
3. Default values are applied correctly when optional variables are not set.
4. The `get_settings()` function returns a cached instance.

### File: `tests/unit/test_config.py`

```python
import pytest
from unittest.mock import patch
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
            s = Settings()
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
            s = Settings()
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
```

### How to Run
```bash
poetry run pytest tests/unit/test_config.py -v
```

### Depends On
- Subtask 1.2 (`config.py`)

---

## Subtask 1.9 — Verification & Smoke Test

### What
After all files are created, run a full verification to ensure everything works together.

### Steps

#### Step 1: Verify Dependencies
```bash
poetry install
poetry show pydantic-settings
```
Expected: `pydantic-settings` version is listed.

#### Step 2: Run Unit Tests
```bash
poetry run pytest tests/unit/test_config.py -v
```
Expected: All 5 tests pass.

#### Step 3: Run the Application
```bash
poetry run uvicorn app.main:app --reload --port 8000
```
Expected: The server starts without errors and logs show `Uvicorn running on http://127.0.0.1:8000`.

#### Step 4: Hit the Health Endpoint
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{
  "status": "healthy",
  "app_name": "ML Platform",
  "version": "1.0.0",
  "environment": "development"
}
```

#### Step 5: Check Swagger Docs
Open `http://localhost:8000/api/docs` in a browser.
Expected: Swagger UI loads with the `/health` endpoint visible.

#### Step 6: Linting
```bash
poetry run ruff check app/core/
poetry run mypy app/core/
```
Expected: No errors.

---

## Summary of Files Created/Modified

| File | Action | Description |
|---|---|---|
| `app/core/config.py` | **CREATE** | Central Settings class with Pydantic validation |
| `app/core/exceptions.py` | **CREATE** | Custom exception hierarchy |
| `app/main.py` | **CREATE** | App factory with health endpoint and exception handlers |
| `.env.example` | **CREATE** | Documented environment variable template |
| `.gitignore` | **CREATE** | Prevents secrets and caches from being committed |
| `.env` | **MODIFY** | Generate and replace the placeholder SECRET_KEY |
| `tests/unit/test_config.py` | **CREATE** | Unit tests for the Settings class |

## Dependency Graph

```
Subtask 1.1 (pydantic-settings)  ──→  Subtask 1.2 (config.py)  ──→  Subtask 1.7 (main.py)
                                                │                          │
                                                ├── Subtask 1.4 (.env)     │
                                                │                          │
                                                ├── Subtask 1.8 (tests) ←──┘
                                                │ 
Subtask 1.3 (.env.example)        (independent)
Subtask 1.5 (.gitignore)          (independent)
Subtask 1.6 (exceptions.py)  ─────────────────→ Subtask 1.7 (main.py)
```

> All independent subtasks (1.1, 1.3, 1.5, 1.6) can be executed in parallel.
> Subtask 1.7 depends on 1.2 and 1.6.
> Subtask 1.8 depends on 1.2 and 1.7.
> Subtask 1.9 is the final verification gate.
