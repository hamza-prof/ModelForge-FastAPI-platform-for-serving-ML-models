# 🚀 FastAPI ML Model Serving Platform — Production Implementation Plan

> **Philosophy:** Build this like it will serve 100,000 users on day one.
> Every decision — naming, layering, error handling — should reflect that mindset.

---

## 📐 Table of Contents

1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Tech Stack & Rationale](#2-tech-stack--rationale)
3. [Phase 0 — Foundation & Project Scaffold](#phase-0--foundation--project-scaffold)
4. [Phase 1 — Configuration & Secrets Management](#phase-1--configuration--secrets-management)
5. [Phase 2 — Database Layer (PostgreSQL + SQLAlchemy)](#phase-2--database-layer-postgresql--sqlalchemy)
6. [Phase 3 — Authentication System (JWT + OAuth2)](#phase-3--authentication-system-jwt--oauth2)
7. [Phase 4 — ML Model Registry & Serving Core](#phase-4--ml-model-registry--serving-core)
8. [Phase 5 — Logging, Observability & Middleware](#phase-5--logging-observability--middleware)
9. [Phase 6 — Async Architecture & Background Tasks](#phase-6--async-architecture--background-tasks)
10. [Phase 7 — Batch Predictions & File Handling](#phase-7--batch-predictions--file-handling)
11. [Phase 8 — Caching Layer (Redis)](#phase-8--caching-layer-redis)
12. [Phase 9 — Testing Strategy](#phase-9--testing-strategy)
13. [Phase 10 — Dockerization & Docker Compose](#phase-10--dockerization--docker-compose)
14. [Phase 11 — CI/CD Pipeline](#phase-11--cicd-pipeline)
15. [Phase 12 — Optional Dashboard](#phase-12--optional-dashboard)
16. [Execution Timeline](#execution-timeline)
17. [Senior Engineering Checklist](#senior-engineering-checklist)

---

## 1. Project Overview & Architecture

### What You're Building

A **production-grade REST API platform** that:
- Authenticates users with JWT
- Accepts uploaded ML models (scikit-learn, PyTorch, etc.)
- Serves predictions via versioned API endpoints
- Logs every prediction with full observability
- Handles batch jobs asynchronously
- Caches deterministic predictions via Redis

### High-Level Architecture

```
                         ┌─────────────────────────────────────┐
                         │             FastAPI App              │
                         │                                      │
  Client ──── HTTPS ───▶ │  ┌──────────┐   ┌──────────────┐   │
                         │  │  Router  │──▶│  Auth Layer  │   │
                         │  └──────────┘   └──────┬───────┘   │
                         │       │                 │           │
                         │  ┌────▼────────────────▼──────┐    │
                         │  │       Service Layer         │    │
                         │  │  (Business Logic Lives Here)│    │
                         │  └──┬──────────┬──────────┬───┘    │
                         │     │          │          │         │
                         │  ┌──▼──┐  ┌───▼───┐  ┌──▼──────┐  │
                         │  │ DB  │  │  ML   │  │  Redis  │  │
                         │  │Repo │  │Service│  │  Cache  │  │
                         │  └──┬──┘  └───┬───┘  └─────────┘  │
                         │     │          │                    │
                         └─────┼──────────┼────────────────────┘
                               │          │
                         ┌─────▼──┐  ┌────▼──────┐
                         │Postgres│  │Model Store│
                         │  (RDS) │  │(Local/S3) │
                         └────────┘  └───────────┘
```

### Layered Architecture (Strict)

```
HTTP Request
     │
     ▼
[ Router ]           ← Only routing, no logic
     │
     ▼
[ Schema ]           ← Pydantic validation, request/response shaping
     │
     ▼
[ Service ]          ← ALL business logic lives here
     │
     ▼
[ Repository ]       ← All DB access lives here, nothing else
     │
     ▼
[ Model / ORM ]      ← SQLAlchemy table definitions only
```

> **Rule:** A router function should never touch the database directly.
> A service should never know what HTTP is. Violating this is a code smell.

---

## 2. Tech Stack & Rationale

| Layer | Technology | Why |
|---|---|---|
| Framework | FastAPI | Async-native, auto docs, DI system, Pydantic |
| ORM | SQLAlchemy 2.x (async) | Industry standard, async support |
| Migrations | Alembic | Version-controlled schema changes |
| Database | PostgreSQL | ACID, JSON support, production standard |
| Cache | Redis | Fast, simple, widely used |
| Auth | python-jose + passlib | JWT handling + bcrypt hashing |
| ML Serving | joblib / torch / onnx | Format-flexible model loading |
| Task Queue | FastAPI BackgroundTasks → Celery (later) | Progressive complexity |
| Testing | pytest + httpx | Async-compatible test client |
| Containerization | Docker + Docker Compose | Reproducible environments |
| CI/CD | GitHub Actions | Free, integrates with Docker Hub |
| Linting | Ruff + Black | Fast, opinionated, PEP8 compliant |
| Type Checking | mypy | Catch bugs before runtime |

---

## Phase 0 — Foundation & Project Scaffold

### 🎯 Goal
Establish a clean, maintainable folder structure that supports scaling to dozens of features without spaghetti.

### Project Structure

```
ml-platform/
│
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # Shared dependencies (get_db, get_current_user)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # Aggregates all v1 routers
│   │       ├── auth.py          # /auth/* endpoints
│   │       ├── models.py        # /models/* endpoints
│   │       ├── predictions.py   # /predict/* endpoints
│   │       └── health.py        # /health endpoint
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings (env vars)
│   │   ├── security.py          # JWT, hashing utilities
│   │   ├── exceptions.py        # Custom exception classes
│   │   └── logging.py           # Structured logger setup
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py              # SQLAlchemy Base, engine, session factory
│   │   └── init_db.py           # First-run DB setup
│   │
│   ├── models/                  # SQLAlchemy ORM models (DB tables)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── ml_model.py
│   │   └── prediction_log.py
│   │
│   ├── schemas/                 # Pydantic schemas (API contracts)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── ml_model.py
│   │   ├── prediction.py
│   │   └── common.py            # Pagination, base response
│   │
│   ├── repositories/            # All DB queries live here
│   │   ├── __init__.py
│   │   ├── base.py              # Generic CRUD base
│   │   ├── user_repo.py
│   │   ├── model_repo.py
│   │   └── prediction_repo.py
│   │
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── model_service.py
│   │   ├── prediction_service.py
│   │   └── cache_service.py
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── registry.py          # In-memory model registry (singleton)
│   │   ├── loader.py            # Model loading strategies per format
│   │   └── validator.py         # Input shape/type validation
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── logging_middleware.py
│   │   └── timing_middleware.py
│   │
│   └── main.py                  # App factory
│
├── alembic/                     # DB migrations
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
├── tests/
│   ├── conftest.py              # Fixtures (test DB, test client)
│   ├── unit/
│   │   ├── test_auth_service.py
│   │   └── test_prediction_service.py
│   └── integration/
│       ├── test_auth_endpoints.py
│       └── test_prediction_endpoints.py
│
├── model_store/                 # Local model storage (mounted volume)
├── .env                         # Local secrets (NEVER commit)
├── .env.example                 # Template (always commit this)
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml               # Project metadata + tool config
├── requirements.txt
└── README.md
```

### Initial Setup Commands

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install core dependencies
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
            pydantic-settings python-jose[cryptography] passlib[bcrypt] \
            redis[asyncio] httpx pytest pytest-asyncio ruff

# Save dependencies
pip freeze > requirements.txt
```

### `pyproject.toml` — Tooling Configuration

```toml
[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### `app/main.py` — App Factory Pattern

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import engine
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.timing_middleware import TimingMiddleware
from app.ml.registry import ModelRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown logic.
    Lifespan replaces the deprecated @app.on_event("startup").
    """
    setup_logging()
    # Pre-load active models into registry on startup
    await ModelRegistry.initialize()
    yield
    # Cleanup on shutdown
    await engine.dispose()
    ModelRegistry.clear()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Middleware (order matters — outermost runs first)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
```

> **Best Practice:** The app factory pattern (`create_app()`) makes the app testable — you can create isolated instances per test without polluting global state.

---

## Phase 1 — Configuration & Secrets Management

### 🎯 Goal
Never hardcode secrets. Every environment-specific value lives in `.env`.

### `app/core/config.py`

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "ML Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | staging | production

    # Database
    DATABASE_URL: str  # e.g. postgresql+asyncpg://user:pass@localhost/mldb

    # Security
    SECRET_KEY: str          # openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # ML
    MODEL_STORE_PATH: str = "./model_store"
    MAX_MODEL_SIZE_MB: int = 500

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

### `.env.example`

```env
APP_NAME=ML Platform
APP_VERSION=1.0.0
ENVIRONMENT=development

DATABASE_URL=postgresql+asyncpg://mluser:mlpassword@localhost:5432/mlplatform
SECRET_KEY=your-secret-key-here-generate-with-openssl
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

REDIS_URL=redis://localhost:6379

MODEL_STORE_PATH=./model_store
MAX_MODEL_SIZE_MB=500

ALLOWED_ORIGINS=["http://localhost:3000"]
```

> **Rule:** `.env` is in `.gitignore`. `.env.example` is always committed. Your teammates should be able to `cp .env.example .env` and fill in real values.

---

## Phase 2 — Database Layer (PostgreSQL + SQLAlchemy)

### 🎯 Goal
Clean, async-first database access with strict separation between queries and business logic.

### `app/db/base.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,   # Detect dead connections
    echo=settings.ENVIRONMENT == "development",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoid lazy loading issues after commit
)


class Base(DeclarativeBase):
    pass
```

### `app/api/deps.py` — Dependency Injection

```python
from collections.abc import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_access_token
from app.db.base import AsyncSessionLocal
from app.models.user import User
from app.repositories.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user
```

### ORM Models

**`app/models/user.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    models: Mapped[list["MLModel"]] = relationship("MLModel", back_populates="owner")
    prediction_logs: Mapped[list["PredictionLog"]] = relationship(
        "PredictionLog", back_populates="user"
    )
```

**`app/models/ml_model.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base


class ModelStatus(str, enum.Enum):
    UPLOADING = "uploading"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    framework: Mapped[str] = mapped_column(String(50))          # sklearn | torch | onnx
    file_path: Mapped[str] = mapped_column(String(500))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[ModelStatus] = mapped_column(Enum(ModelStatus), default=ModelStatus.UPLOADING)
    input_schema: Mapped[dict | None] = mapped_column(JSONB)    # Expected input structure
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="models")

    __table_args__ = (
        # A user can't have two models with the same name+version
        UniqueConstraint("owner_id", "name", "version", name="uq_owner_model_version"),
    )
```

**`app/models/prediction_log.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ml_models.id"), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prediction: Mapped[dict] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    user: Mapped["User"] = relationship("User", back_populates="prediction_logs")
```

### Repository Pattern

**`app/repositories/base.py`**

```python
from typing import Generic, TypeVar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: UUID) -> ModelType | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()  # Get ID without committing
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.db.delete(obj)
        await self.db.flush()
```

**`app/repositories/user_repo.py`**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
```

### Alembic Setup

```bash
# Initialize Alembic
alembic init alembic

# Generate first migration
alembic revision --autogenerate -m "initial_tables"

# Run migrations
alembic upgrade head
```

> **Rule:** Never manually edit your database schema in production. Always generate a migration, review it, and apply it. Migrations are version control for your database.

---

## Phase 3 — Authentication System (JWT + OAuth2)

### 🎯 Goal
Stateless, secure, production-grade auth with access + refresh tokens.

### `app/core/security.py`

```python
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return _create_token({"sub": subject, "type": "access", "exp": expire})


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token({"sub": subject, "type": "refresh", "exp": expire})


def verify_access_token(token: str) -> dict[str, Any] | None:
    return _decode_token(token, expected_type="access")


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    return _decode_token(token, expected_type="refresh")


def _create_token(data: dict) -> str:
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_token(token: str, expected_type: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
```

### `app/schemas/user.py`

```python
import uuid
from pydantic import BaseModel, EmailStr, field_validator


class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric")
        return v.lower()


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    is_active: bool

    model_config = {"from_attributes": True}
```

### `app/services/auth_service.py`

```python
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import TokenResponse, UserRegisterRequest


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(self, data: UserRegisterRequest) -> User:
        if await self.repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        if await self.repo.get_by_username(data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
        )
        return await self.repo.create(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        user = await self.repo.get_by_id(payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )
```

### `app/api/v1/auth.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    service = AuthService(db)
    user = await service.register(data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and receive access + refresh tokens."""
    service = AuthService(db)
    return await service.login(data.email, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Exchange a refresh token for a new token pair."""
    service = AuthService(db)
    return await service.refresh(refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return current_user
```

---

## Phase 4 — ML Model Registry & Serving Core

### 🎯 Goal
Load models once, serve predictions fast, validate inputs strictly.

### `app/ml/registry.py` — Singleton Model Registry

```python
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    In-memory model registry. Loaded once at startup.
    Keyed by model_id (UUID string).
    """
    _registry: dict[str, Any] = {}

    @classmethod
    async def initialize(cls) -> None:
        """Called at app startup to load all active models."""
        # TODO: Query DB for active models and load them
        logger.info("ModelRegistry initialized")

    @classmethod
    def register(cls, model_id: str, model_obj: Any) -> None:
        cls._registry[model_id] = model_obj
        logger.info(f"Model {model_id} registered in registry")

    @classmethod
    def get(cls, model_id: str) -> Any | None:
        return cls._registry.get(model_id)

    @classmethod
    def unregister(cls, model_id: str) -> None:
        cls._registry.pop(model_id, None)

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
```

### `app/ml/loader.py` — Multi-Framework Model Loading

```python
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ModelLoader:
    @staticmethod
    def load(file_path: str, framework: str) -> Any:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {file_path}")

        loaders = {
            "sklearn": ModelLoader._load_sklearn,
            "torch": ModelLoader._load_torch,
            "onnx": ModelLoader._load_onnx,
        }
        loader = loaders.get(framework)
        if not loader:
            raise ValueError(f"Unsupported framework: {framework}")

        logger.info(f"Loading {framework} model from {file_path}")
        return loader(path)

    @staticmethod
    def _load_sklearn(path: Path) -> Any:
        import joblib
        return joblib.load(path)

    @staticmethod
    def _load_torch(path: Path) -> Any:
        import torch
        return torch.load(path, map_location="cpu")

    @staticmethod
    def _load_onnx(path: Path) -> Any:
        import onnxruntime as ort
        return ort.InferenceSession(str(path))
```

### `app/services/prediction_service.py`

```python
import time
import logging
import numpy as np
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.registry import ModelRegistry
from app.models.prediction_log import PredictionLog
from app.models.user import User
from app.repositories.model_repo import ModelRepository
from app.repositories.prediction_repo import PredictionRepository
from app.schemas.prediction import PredictRequest, PredictResponse

logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model_repo = ModelRepository(db)
        self.prediction_repo = PredictionRepository(db)

    async def predict(
        self, model_id: UUID, data: PredictRequest, user: User
    ) -> PredictResponse:
        # 1. Validate model exists and is active
        ml_model = await self.model_repo.get_active_by_id(model_id)
        if not ml_model:
            raise HTTPException(status_code=404, detail="Model not found or not active")

        # 2. Fetch from registry (loaded at startup, not from disk)
        model_obj = ModelRegistry.get(str(model_id))
        if not model_obj:
            raise HTTPException(status_code=503, detail="Model not currently loaded")

        # 3. Run inference with timing
        start = time.perf_counter()
        try:
            input_array = np.array(data.features)
            prediction = model_obj.predict(input_array.reshape(1, -1))
            result = prediction.tolist()
        except Exception as e:
            logger.error(f"Inference error for model {model_id}: {e}")
            raise HTTPException(status_code=422, detail=f"Inference failed: {str(e)}")
        latency_ms = (time.perf_counter() - start) * 1000

        # 4. Log asynchronously (via background task in router)
        log_entry = PredictionLog(
            user_id=user.id,
            model_id=ml_model.id,
            input_data={"features": data.features},
            prediction={"result": result},
            latency_ms=latency_ms,
        )
        await self.prediction_repo.create(log_entry)

        return PredictResponse(
            model_id=str(model_id),
            model_version=ml_model.version,
            prediction=result,
            latency_ms=round(latency_ms, 2),
        )
```

### `app/schemas/prediction.py`

```python
from pydantic import BaseModel, field_validator


class PredictRequest(BaseModel):
    features: list[float]

    @field_validator("features")
    @classmethod
    def features_not_empty(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("Features list cannot be empty")
        return v


class PredictResponse(BaseModel):
    model_id: str
    model_version: str
    prediction: list
    latency_ms: float
```

---

## Phase 5 — Logging, Observability & Middleware

### 🎯 Goal
Every request should be traceable. Every error should have context.

### `app/core/logging.py` — Structured JSON Logging

```python
import logging
import sys


def setup_logging() -> None:
    """Configure structured logging for the entire application."""
    logging.basicConfig(
        level=logging.INFO,
        format='{"time": "%(asctime)s", "level": "%(levelname)s", '
               '"module": "%(name)s", "message": "%(message)s"}',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Silence noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

### `app/middleware/logging_middleware.py`

```python
import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Attach a unique request ID for tracing across log lines
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
```

### `app/core/exceptions.py` — Global Error Handling

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str = "GENERAL_ERROR"):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "detail": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "detail": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None),
            },
        )
```

---

## Phase 6 — Async Architecture & Background Tasks

### 🎯 Goal
Keep requests non-blocking. Offload slow work.

### Key Principles

| Task Type | Strategy |
|---|---|
| DB queries | `async` with SQLAlchemy async session |
| File I/O | `asyncio` + `aiofiles` |
| ML inference | Sync (CPU-bound) — run in threadpool |
| Logging to DB | `BackgroundTasks` (FastAPI) |
| Heavy batch jobs | Celery + Redis (future phase) |

### Running CPU-Bound Code Correctly

```python
# WRONG — blocks the event loop for all other requests
result = model.predict(data)

# CORRECT — offloads to threadpool, event loop stays free
import asyncio
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, model.predict, data)
```

### Background Task for Logging

```python
# In your router
from fastapi import BackgroundTasks

@router.post("/predict/{model_id}")
async def predict(
    model_id: UUID,
    data: PredictRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PredictionService(db)
    result, log_entry = await service.predict(model_id, data, current_user)

    # Log asynchronously — don't make the client wait
    background_tasks.add_task(service.save_prediction_log, log_entry)

    return result
```

---

## Phase 7 — Batch Predictions & File Handling

### 🎯 Goal
Accept CSV/JSON files, run predictions on all rows, stream results back.

### `app/api/v1/predictions.py` — Batch Endpoint

```python
import csv
import io
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/predict", tags=["Predictions"])

CHUNK_SIZE = 100  # Process 100 rows at a time


@router.post("/batch/{model_id}")
async def predict_batch(
    model_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("text/csv", "application/json"):
        raise HTTPException(status_code=415, detail="Only CSV or JSON accepted")

    service = PredictionService(db)

    async def generate_results():
        content = await file.read()
        reader = csv.DictReader(io.StringIO(content.decode()))
        yield '{"results": [\n'
        first = True
        for row in reader:
            features = [float(v) for v in row.values()]
            result = await service.predict_single(model_id, features, current_user)
            if not first:
                yield ",\n"
            yield result.model_dump_json()
            first = False
        yield "\n]}"

    return StreamingResponse(generate_results(), media_type="application/json")
```

---

## Phase 8 — Caching Layer (Redis)

### 🎯 Goal
Cache deterministic prediction results to reduce latency and DB load.

### `app/services/cache_service.py`

```python
import hashlib
import json
import logging
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl_seconds = 3600  # 1 hour

    def _make_key(self, model_id: str, features: list) -> str:
        """Deterministic cache key based on model + exact input."""
        payload = json.dumps({"model_id": model_id, "features": features}, sort_keys=True)
        return f"pred:{hashlib.sha256(payload.encode()).hexdigest()}"

    async def get_prediction(self, model_id: str, features: list) -> dict | None:
        key = self._make_key(model_id, features)
        cached = await self.redis.get(key)
        if cached:
            logger.debug(f"Cache HIT for key {key[:12]}...")
            return json.loads(cached)
        return None

    async def set_prediction(self, model_id: str, features: list, result: dict) -> None:
        key = self._make_key(model_id, features)
        await self.redis.setex(key, self.ttl_seconds, json.dumps(result))

    async def close(self) -> None:
        await self.redis.aclose()
```

> **Cache rules:**
> - Only cache when input → output is deterministic (no randomness in model)
> - Always hash the key — don't store raw feature vectors as keys
> - Set a reasonable TTL — cache invalidation when model version changes

---

## Phase 9 — Testing Strategy

### 🎯 Goal
Test the service layer, not just endpoints. Catch bugs before they hit production.

### Test Structure

```
tests/
├── conftest.py         # Shared fixtures
├── unit/               # Test services in isolation (mock repos)
│   ├── test_auth_service.py
│   └── test_prediction_service.py
└── integration/        # Test full request → response cycle
    ├── test_auth_endpoints.py
    └── test_predict_endpoints.py
```

### `tests/conftest.py`

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.api.deps import get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5432/mlplatform_test"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

### `tests/integration/test_auth_endpoints.py`

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepass123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dupe@example.com", "username": "user1", "password": "pass1234"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json={**payload, "username": "user2"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_tokens(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "username": "loginuser", "password": "pass1234"
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "pass1234"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
```

---

## Phase 10 — Dockerization & Docker Compose

### `Dockerfile` — Multi-Stage Build

```dockerfile
# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install only what's needed for building
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runner ---
FROM python:3.11-slim AS runner

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Non-root user for security
RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://mluser:mlpassword@db:5432/mlplatform
      - REDIS_URL=redis://cache:6379
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=development
    volumes:
      - ./model_store:/app/model_store
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: mluser
      POSTGRES_PASSWORD: mlpassword
      POSTGRES_DB: mlplatform
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mluser -d mlplatform"]
      interval: 5s
      timeout: 5s
      retries: 5
    ports:
      - "5432:5432"

  cache:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  redis_data:
```

### Run Commands

```bash
# Build and start all services
docker compose up --build

# Run migrations inside container
docker compose exec api alembic upgrade head

# View logs
docker compose logs -f api

# Stop everything
docker compose down
```

---

## Phase 11 — CI/CD Pipeline

### `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff mypy
      - run: ruff check app/
      - run: mypy app/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: mlplatform_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --tb=short
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/mlplatform_test
          REDIS_URL: redis://localhost:6379
          SECRET_KEY: test-secret-key-for-ci

  build:
    needs: [lint-and-type-check, test]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: false   # Set to true when deploying
          tags: ml-platform:latest
```

---

## Phase 12 — Optional Dashboard

### Option A: Streamlit (Fastest, Python-native)

```python
# dashboard/app.py
import streamlit as st
import pandas as pd
import httpx

API_URL = "http://localhost:8000/api/v1"

st.title("ML Platform Dashboard")

token = st.sidebar.text_input("Access Token", type="password")

if token:
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(f"{API_URL}/logs", headers=headers)
    logs = response.json()

    df = pd.DataFrame(logs)
    st.subheader("Recent Predictions")
    st.dataframe(df)
    st.line_chart(df["latency_ms"])
```

### Option B: React Frontend (Better for portfolio)

```
dashboard/
├── src/
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   └── ModelManager.tsx
│   ├── components/
│   │   ├── PredictionChart.tsx
│   │   └── ModelCard.tsx
│   └── api/
│       └── client.ts       # Axios client with interceptors
```

---

## Execution Timeline

| Week | Phases | Deliverable |
|---|---|---|
| Week 1 | 0, 1, 2 | Running app with auth + DB, migrations working |
| Week 2 | 3, 4, 5 | Auth endpoints tested, model upload + predict working |
| Week 3 | 6, 7, 8 | Async logging, batch predict, Redis cache |
| Week 4 | 9, 10, 11 | Full test suite, Dockerized, CI passing |
| Week 5 | 12 | Dashboard (optional), README, portfolio write-up |

---

## Senior Engineering Checklist

Use this before calling any phase "done."

### Code Quality
- [ ] Routes contain zero business logic (only call services)
- [ ] Services contain zero SQL (only call repositories)
- [ ] No secrets in source code (all via `settings`)
- [ ] All endpoints have Pydantic request/response schemas
- [ ] All inputs validated before touching services
- [ ] All DB operations inside repository layer

### Error Handling
- [ ] All `HTTPException`s have clear `detail` messages
- [ ] Unhandled exceptions return structured JSON (not stack traces)
- [ ] Request IDs attached to every error response
- [ ] Sensitive data (passwords, tokens) never appear in logs

### Performance
- [ ] ML model loaded once at startup, never per-request
- [ ] All DB queries are async
- [ ] CPU-bound inference runs in threadpool executor
- [ ] Connection pool configured (not default)

### Security
- [ ] Passwords hashed with bcrypt
- [ ] Access tokens expire (< 60 minutes)
- [ ] Refresh tokens expire (< 30 days)
- [ ] CORS restricted to known origins
- [ ] Docs endpoint disabled in production
- [ ] Docker runs as non-root user

### Testing
- [ ] Unit tests for each service
- [ ] Integration tests for each endpoint group
- [ ] Test DB is separate from dev DB
- [ ] CI runs tests on every push

### Deployment
- [ ] App runs inside Docker
- [ ] Migrations run on startup (or explicitly via CI)
- [ ] Health check endpoint exists (`GET /health`)
- [ ] `.env.example` is committed and up to date

---

## Health Check Endpoint

Always implement this first — your Docker healthcheck and any cloud load balancer needs it.

```python
# app/api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "database": db_status,
        "version": "1.0.0",
    }
```

---

*This document is your engineering spec. Treat each phase as a PR on a real team. Don't move to the next phase until the current one passes the checklist.*
