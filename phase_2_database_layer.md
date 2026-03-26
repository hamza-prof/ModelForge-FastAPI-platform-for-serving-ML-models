# Phase 2 — Database Layer (PostgreSQL + SQLAlchemy)

> **Goal:** Build a clean, async-first database access layer with strict separation between
> queries (repositories) and business logic (services). Every DB interaction flows through
> the Repository pattern — no raw SQL in routers, no ORM queries in services.

---

## Table of Contents

1. [Concepts to Learn](#concepts-to-learn)
2. [Subtask 2.1 — Install & Verify Dependencies](#subtask-21--install--verify-dependencies)
3. [Subtask 2.2 — PostgreSQL Setup (Local)](#subtask-22--postgresql-setup-local)
4. [Subtask 2.3 — Create the Async Database Engine (`app/db/base.py`)](#subtask-23--create-the-async-database-engine-appdbbasepy)
5. [Subtask 2.4 — Create the DB Session Dependency (`app/api/deps.py`)](#subtask-24--create-the-db-session-dependency-appapidepspy)
6. [Subtask 2.5 — Create ORM Models](#subtask-25--create-orm-models)
7. [Subtask 2.6 — Configure Alembic for Async Migrations (`alembic/env.py`)](#subtask-26--configure-alembic-for-async-migrations-alembicenvpy)
8. [Subtask 2.7 — Generate & Run the First Migration](#subtask-27--generate--run-the-first-migration)
9. [Subtask 2.8 — Implement the Repository Pattern](#subtask-28--implement-the-repository-pattern)
10. [Subtask 2.9 — Create `app/db/init_db.py` (Optional Seed Script)](#subtask-29--create-appdbinit_dbpy-optional-seed-script)
11. [Subtask 2.10 — Wire Database into App Lifespan (`app/main.py`)](#subtask-210--wire-database-into-app-lifespan-appmainpy)
12. [Subtask 2.11 — Write Tests for the Database Layer](#subtask-211--write-tests-for-the-database-layer)
13. [Subtask 2.12 — Verification & Smoke Test](#subtask-212--verification--smoke-test)

---

## Concepts to Learn

Before writing code, study each concept below. Understanding the **why** is as important as the **how**.

### 1. SQLAlchemy 2.x — The Modern ORM

| Topic | What to Learn | Resources |
|---|---|---|
| **DeclarativeBase** | SQLAlchemy 2.x replaces the old `declarative_base()` function with a class-based `DeclarativeBase`. All models inherit from this. | [SQLAlchemy 2.0 Mapping](https://docs.sqlalchemy.org/en/20/orm/mapping_styles.html) |
| **Mapped & mapped_column** | New type-annotated column declarations. `Mapped[str]` replaces `Column(String)`. Improves IDE autocompletion and mypy compatibility. | [Mapped Column](https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html) |
| **Relationships** | `relationship()` defines how ORM models reference each other. Learn `back_populates` vs `backref`, lazy loading dangers in async. | [Relationship Patterns](https://docs.sqlalchemy.org/en/20/orm/relationships.html) |

### 2. Async SQLAlchemy — Why It Matters

| Topic | What to Learn |
|---|---|
| **`create_async_engine`** | Creates an async-compatible engine. Unlike sync engine, it uses `asyncpg` (or `aiosqlite`) as the driver. |
| **`async_sessionmaker`** | Factory for creating `AsyncSession` instances. Replaces the sync `sessionmaker`. |
| **`AsyncSession`** | The async session does NOT support lazy loading. You must use `selectinload()` or `joinedload()` for relationships. |
| **`expire_on_commit=False`** | After committing, sync sessions "expire" all attributes forcing a re-query. In async, this triggers a lazy load which fails. Always set this to `False`. |

> **Key Insight:** Async SQLAlchemy is not just "add `await`" — it fundamentally changes how relationships and session management work.

### 3. Connection Pooling

| Parameter | Purpose | Recommended Value |
|---|---|---|
| `pool_size` | Number of persistent connections kept open | 10 (adjust based on load) |
| `max_overflow` | Extra connections allowed beyond pool_size | 20 |
| `pool_pre_ping` | Sends a lightweight query before reusing a connection to detect stale connections | `True` |
| `pool_recycle` | Time (seconds) after which a connection is recycled | 3600 (1 hour) |

> **Why this matters:** Without pooling, every request creates a new TCP connection to PostgreSQL (~5-20ms overhead). With a pool of 10, those connections are reused instantly.

### 4. The Repository Pattern

| Concept | Explanation |
|---|---|
| **What** | A class that encapsulates all database queries for a specific entity (e.g., `UserRepository` handles all `User` table queries). |
| **Why** | Separates data access from business logic. Services call `repo.get_by_email()` instead of writing raw SQLAlchemy queries. This makes services testable by mocking the repository. |
| **Generic Base** | A `BaseRepository[T]` using Python generics provides CRUD operations (`get_by_id`, `get_all`, `create`, `delete`) that all entity repos inherit. |
| **Anti-pattern** | Don't put business logic in repositories. A repo should never decide if a user "is allowed" to do something — that's the service's job. |

### 5. Alembic — Database Migration Tool

| Concept | Explanation |
|---|---|
| **What** | Version control for your database schema. Each migration is a Python file with `upgrade()` and `downgrade()` functions. |
| **Autogenerate** | Alembic compares your ORM models against the current DB schema and generates migration scripts automatically. |
| **Async Config** | Alembic's default `env.py` is synchronous. For async engines, you must override `run_migrations_online()` to use `run_async()`. |
| **Migration Chain** | Migrations form a linked list via `revision` and `down_revision`. `alembic upgrade head` applies all pending migrations. |

> **Rule:** Never manually edit your database schema in production. Always generate a migration, review it, and apply it.

### 6. FastAPI Dependency Injection for DB Sessions

| Concept | Explanation |
|---|---|
| **`Depends(get_db)`** | FastAPI's DI system calls `get_db()` for each request, yielding a session that's automatically committed on success or rolled back on failure. |
| **Yield Dependencies** | `get_db` uses `yield` to provide cleanup logic. Code before `yield` runs on request start, code after runs on request end (like a context manager). |
| **Session-per-Request** | Each HTTP request gets its own `AsyncSession`. This prevents cross-request data contamination and ensures proper transaction boundaries. |

### 7. PostgreSQL Concepts

| Concept | Why It Matters |
|---|---|
| **UUID Primary Keys** | Using UUIDs instead of auto-incrementing integers prevents ID enumeration attacks and makes distributed systems easier. PostgreSQL has a native `UUID` type. |
| **JSONB Columns** | PostgreSQL's `JSONB` type stores structured data that can be indexed and queried. Perfect for ML model input schemas and prediction results. |
| **Server-Side Defaults** | `server_default=func.now()` runs the timestamp function on the database server, not in Python. This ensures consistency regardless of app server time. |
| **Unique Constraints** | Composite unique constraints (e.g., `owner_id + name + version`) enforce business rules at the DB level — the last line of defense. |
| **Indexes** | `index=True` on frequently queried columns (e.g., `email`, `created_at`) dramatically speeds up lookups. |

---

## Subtask 2.1 — Install & Verify Dependencies

### What
Verify that all database-related packages are installed in the Poetry environment.

### Why
Phase 0 already added these dependencies, but it's important to verify before writing code.

### Required Packages

| Package | Purpose |
|---|---|
| `sqlalchemy[asyncio]` | ORM with async extension |
| `asyncpg` | PostgreSQL async driver (fastest Python PG driver) |
| `alembic` | Database migration management |

### Steps
```bash
poetry show sqlalchemy
poetry show asyncpg
poetry show alembic
```

### Current Status
✅ Already present in `pyproject.toml`:
- `sqlalchemy = {extras = ["asyncio"], version = "2.0.48"}`
- `asyncpg = "0.31.0"`
- `alembic = "1.18.4"`

**No action needed.**

---

## Subtask 2.2 — PostgreSQL Setup (Local)

### What
Set up a local PostgreSQL instance and create the application database.

### Why
The application needs a running PostgreSQL server to connect to. The `DATABASE_URL` in `.env` must point to a real database.

### Option A: Using Docker (Recommended)
```bash
docker run -d \
  --name mlplatform-postgres \
  -e POSTGRES_USER=mluser \
  -e POSTGRES_PASSWORD=mlpassword \
  -e POSTGRES_DB=mlplatform \
  -p 5432:5432 \
  postgres:16-alpine
```

### Option B: Using System PostgreSQL
```sql
-- Connect as superuser
CREATE USER mluser WITH PASSWORD 'mlpassword';
CREATE DATABASE mlplatform OWNER mluser;
GRANT ALL PRIVILEGES ON DATABASE mlplatform TO mluser;
```

### Verify Connection
```bash
# Using psql
psql postgresql://mluser:mlpassword@localhost:5432/mlplatform -c "SELECT 1;"
```

### Verify `.env`
Ensure your `.env` contains:
```
DATABASE_URL=postgresql+asyncpg://mluser:mlpassword@localhost:5432/mlplatform
```

### Depends On
- Phase 1 (`.env` file exists with `DATABASE_URL`)

---

## Subtask 2.3 — Create the Async Database Engine (`app/db/base.py`)

### What
Create the central database module that configures the async engine, session factory, and ORM base class.

### Why
- **Single source of truth** for DB connectivity — every module imports from here.
- **Connection pooling** is configured once, not per-query.
- **`expire_on_commit=False`** prevents async lazy-loading crashes.

### File: `app/db/base.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Async Engine ─────────────────────────────────────────────────
# The engine manages a pool of database connections.
# - pool_size: permanent connections kept open
# - max_overflow: temporary connections allowed when pool is full
# - pool_pre_ping: tests connections before reuse (detects dead connections)
# - echo: logs SQL statements in development for debugging
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.ENVIRONMENT == "development",
)

# ── Session Factory ──────────────────────────────────────────────
# async_sessionmaker creates AsyncSession instances.
# expire_on_commit=False is CRITICAL for async — without it,
# accessing attributes after commit triggers a lazy load,
# which raises an error in async context.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── ORM Base Class ───────────────────────────────────────────────
# All ORM models inherit from this.
# SQLAlchemy 2.x style — replaces the old declarative_base() function.
class Base(DeclarativeBase):
    pass
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| `pool_size=10` | Reasonable default. Each connection uses ~5MB RAM on the PostgreSQL side. 10 connections handles ~10 concurrent queries without queueing. |
| `pool_pre_ping=True` | PostgreSQL closes idle connections after `idle_in_transaction_session_timeout`. Pre-ping detects this and reconnects automatically. |
| `echo=True` only in dev | SQL logs are invaluable for debugging but noisy in production. |
| `expire_on_commit=False` | **Most common async SQLAlchemy bug.** Without this, accessing `user.email` after commit raises `MissingGreenlet` error. |

### Depends On
- Subtask 2.1 (SQLAlchemy installed)
- Phase 1 (`config.py` with `DATABASE_URL`)

---

## Subtask 2.4 — Create the DB Session Dependency (`app/api/deps.py`)

### What
Create the FastAPI dependency that provides an `AsyncSession` to route handlers, with automatic commit/rollback lifecycle.

### Why
- **Session-per-request** is the standard pattern — each request gets an isolated session.
- **Automatic cleanup** — the `try/except/finally` ensures sessions are always committed or rolled back.
- Centralizing this logic prevents every route from managing its own session lifecycle.

### File: `app/api/deps.py`

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Lifecycle:
        1. Session is created from the pool
        2. Yielded to the route handler
        3. On success: committed
        4. On exception: rolled back, then re-raised
        5. Session is always closed (returned to pool)

    Usage in routes:
        @router.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Important Notes

| Point | Explanation |
|---|---|
| No `finally: session.close()` | The `async with` context manager handles closing automatically. |
| Commit happens after the route | If the route handler raises an exception, `rollback()` is called instead. |
| One session per request | FastAPI calls `get_db()` for each request. Concurrent requests get separate sessions. |

### Depends On
- Subtask 2.3 (`base.py` with `AsyncSessionLocal`)

---

## Subtask 2.5 — Create ORM Models

### What
Define SQLAlchemy ORM models that map to PostgreSQL tables. Phase 2 creates three models: `User`, `MLModel`, and `PredictionLog`.

### Why
- **Type safety** — `Mapped[str]` gives IDE autocompletion and mypy checks.
- **Relationships** — ORM relationships let you navigate between related entities without writing JOINs.
- **Constraints** — Unique constraints and indexes enforce data integrity at the DB level.

### 2.5.1 — `app/models/user.py`

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """
    User account table.

    Design decisions:
    - UUID primary key: prevents ID enumeration attacks
    - email + username both unique and indexed: fast lookups
    - server_default for timestamps: DB server generates time, not app
    - is_superuser: simple role flag (can be expanded to RBAC later)
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    models: Mapped[list["MLModel"]] = relationship(
        "MLModel", back_populates="owner", cascade="all, delete-orphan"
    )
    prediction_logs: Mapped[list["PredictionLog"]] = relationship(
        "PredictionLog", back_populates="user", cascade="all, delete-orphan"
    )
```

### 2.5.2 — `app/models/ml_model.py`

```python
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ModelStatus(str, enum.Enum):
    """
    Lifecycle states for an ML model.
    Using str mixin allows JSON serialization: ModelStatus.ACTIVE == "active"
    """

    UPLOADING = "uploading"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class MLModel(Base):
    """
    ML model metadata table.

    Stores metadata about uploaded models — the actual model binary
    lives on disk at `file_path` (or S3 in production).
    """

    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    framework: Mapped[str] = mapped_column(String(50))  # sklearn | torch | onnx
    file_path: Mapped[str] = mapped_column(String(500))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus), default=ModelStatus.UPLOADING
    )
    input_schema: Mapped[dict | None] = mapped_column(JSONB)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    owner: Mapped["User"] = relationship("User", back_populates="models")

    # ── Table-Level Constraints ──────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "name", "version", name="uq_owner_model_version"
        ),
    )
```

### 2.5.3 — `app/models/prediction_log.py`

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PredictionLog(Base):
    """
    Immutable log of every prediction served.

    This table is append-only — predictions are never updated or deleted.
    Useful for auditing, debugging, and model performance monitoring.
    """

    __tablename__ = "prediction_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ml_models.id"), nullable=False
    )
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prediction: Mapped[dict] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # ── Relationships ────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="prediction_logs")
```

### 2.5.4 — `app/models/__init__.py` (Model Registry)

```python
"""
Import all models here so Alembic's autogenerate can detect them.
Alembic compares Base.metadata against the DB — if a model isn't imported,
its table won't appear in autogenerated migrations.
"""

from app.models.ml_model import MLModel, ModelStatus
from app.models.prediction_log import PredictionLog
from app.models.user import User

__all__ = ["User", "MLModel", "ModelStatus", "PredictionLog"]
```

> **Critical:** Without this import in `__init__.py`, Alembic will generate empty migrations because
> it doesn't know about your models.

### Depends On
- Subtask 2.3 (`Base` class from `base.py`)

---

## Subtask 2.6 — Configure Alembic for Async Migrations (`alembic/env.py`)

### What
Create the `alembic/env.py` file configured for async SQLAlchemy. The default Alembic `env.py` is synchronous and won't work with `create_async_engine`.

### Why
- Alembic needs to connect to your database to autogenerate migrations.
- With an async engine, you must use `connectable.connect()` inside `run_async()`.
- `env.py` must import your `Base.metadata` and all models for autogeneration to work.

### File: `alembic/env.py`

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from app.core.config import settings
from app.db.base import Base

# Import ALL models so that Base.metadata is populated
import app.models  # noqa: F401

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Override sqlalchemy.url with the app's DATABASE_URL
# This ensures alembic.ini doesn't need to hardcode credentials
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL scripts without a DB connection.
    Useful for generating migration SQL for review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_name="postgresql",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Helper to configure and run migrations with a given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to DB and applies changes.

    Key difference from default Alembic:
    - Uses async_engine_from_config instead of engine_from_config
    - Wraps migration execution in run_async() / run_sync()
    - Uses NullPool to avoid connection pool issues during migrations
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)` | Overrides `alembic.ini` value so credentials come from `.env`, not a committed file. |
| `import app.models` | Forces all model modules to load, populating `Base.metadata`. Without this, autogenerate sees zero tables. |
| `pool.NullPool` | Migrations are short-lived one-off scripts. Using a connection pool wastes resources and can cause issues. |
| `asyncio.run()` | Alembic itself is sync. We wrap the async migration runner in `asyncio.run()`. |

### Also Update: `alembic.ini`

The hardcoded URL should be treated as a fallback. `env.py` overrides it at runtime.

```ini
# Line 6 in alembic.ini — this is overridden by env.py at runtime
sqlalchemy.url = postgresql+asyncpg://localhost/mlplatform
```

### Depends On
- Subtask 2.3 (`Base`, `engine`)
- Subtask 2.5 (all models must be importable)
- Phase 1 (`settings.DATABASE_URL`)

---

## Subtask 2.7 — Generate & Run the First Migration

### What
Use Alembic to auto-generate the initial migration and apply it to the database.

### Steps

```bash
# Step 1: Generate the migration script
poetry run alembic revision --autogenerate -m "create_initial_tables"

# Step 2: Review the generated file
# Open alembic/versions/xxxx_create_initial_tables.py and verify:
# - Creates tables: users, ml_models, prediction_logs
# - Creates all columns with correct types
# - Creates indexes on email, username, created_at
# - Creates unique constraint uq_owner_model_version

# Step 3: Apply the migration
poetry run alembic upgrade head

# Step 4: Verify tables exist
poetry run python -c "
import asyncio
from sqlalchemy import text
from app.db.base import engine

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text(
            \"SELECT tablename FROM pg_tables WHERE schemaname = 'public'\"
        ))
        tables = [row[0] for row in result]
        print(f'Tables created: {tables}')
        assert 'users' in tables
        assert 'ml_models' in tables
        assert 'prediction_logs' in tables
        print('✅ All tables verified!')

asyncio.run(check())
"
```

### Review Checklist for Generated Migration

- [ ] `users` table has UUID primary key, email/username with unique indexes
- [ ] `ml_models` table has composite unique constraint `uq_owner_model_version`
- [ ] `prediction_logs` table has index on `created_at`
- [ ] All foreign keys point to correct tables
- [ ] `downgrade()` drops tables in reverse order (respecting FK dependencies)

### Depends On
- Subtask 2.6 (`env.py` configured)
- Subtask 2.2 (PostgreSQL running)

---

## Subtask 2.8 — Implement the Repository Pattern

### What
Create the generic `BaseRepository` and entity-specific repositories for `User`, `MLModel`, and `PredictionLog`.

### 2.8.1 — `app/repositories/base.py` (Generic CRUD)

```python
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing basic CRUD operations.

    All entity repositories inherit from this and add
    entity-specific query methods.

    Design notes:
    - Uses flush() not commit() — the session dependency handles commits.
    - refresh() reloads the object after flush to get DB-generated values
      (e.g., server_default timestamps, UUIDs).
    """

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Fetch a single record by primary key."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Fetch paginated records."""
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        """Add a new record. Uses flush() to get the ID without committing."""
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        """Persist changes to an existing record."""
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """Remove a record."""
        await self.db.delete(obj)
        await self.db.flush()
```

### 2.8.2 — `app/repositories/user_repo.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User-specific database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """Find a user by their email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Find a user by their username."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
```

### 2.8.3 — `app/repositories/model_repo.py`

```python
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_model import MLModel, ModelStatus
from app.repositories.base import BaseRepository


class ModelRepository(BaseRepository[MLModel]):
    """Repository for MLModel-specific database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(MLModel, db)

    async def get_active_by_id(self, model_id: UUID) -> MLModel | None:
        """Fetch a model only if its status is ACTIVE."""
        result = await self.db.execute(
            select(MLModel).where(
                MLModel.id == model_id,
                MLModel.status == ModelStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_owner(
        self, owner_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[MLModel]:
        """Fetch all models belonging to a specific user."""
        result = await self.db.execute(
            select(MLModel)
            .where(MLModel.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_name_version(
        self, owner_id: UUID, name: str, version: str
    ) -> MLModel | None:
        """Check if a model with the same name+version exists for this owner."""
        result = await self.db.execute(
            select(MLModel).where(
                MLModel.owner_id == owner_id,
                MLModel.name == name,
                MLModel.version == version,
            )
        )
        return result.scalar_one_or_none()
```

### 2.8.4 — `app/repositories/prediction_repo.py`

```python
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction_log import PredictionLog
from app.repositories.base import BaseRepository


class PredictionRepository(BaseRepository[PredictionLog]):
    """Repository for PredictionLog-specific database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(PredictionLog, db)

    async def get_by_model(
        self, model_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[PredictionLog]:
        """Fetch prediction logs for a specific model (most recent first)."""
        result = await self.db.execute(
            select(PredictionLog)
            .where(PredictionLog.model_id == model_id)
            .order_by(PredictionLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[PredictionLog]:
        """Fetch prediction logs for a specific user (most recent first)."""
        result = await self.db.execute(
            select(PredictionLog)
            .where(PredictionLog.user_id == user_id)
            .order_by(PredictionLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
```

### Depends On
- Subtask 2.3 (`Base` from `base.py`)
- Subtask 2.5 (ORM models)

---

## Subtask 2.9 — Create `app/db/init_db.py` (Optional Seed Script)

### What
An optional utility script for seeding the database with initial data (e.g., a default superuser).

### Why
- Useful for local development — ensures you always have a user to test with.
- Can be called from the app lifespan or run manually via CLI.

### File: `app/db/init_db.py`

```python
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


async def create_superuser_if_not_exists(
    email: str = "admin@mlplatform.com",
    username: str = "admin",
    hashed_password: str = "",
) -> None:
    """
    Create a default superuser if one doesn't exist.
    Called during app startup in development only.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Superuser '{email}' already exists, skipping.")
            return

        superuser = User(
            email=email,
            username=username,
            hashed_password=hashed_password,  # Will be set properly in Phase 3
            is_active=True,
            is_superuser=True,
        )
        session.add(superuser)
        await session.commit()
        logger.info(f"✅ Superuser '{email}' created successfully.")
```

### Depends On
- Subtask 2.3 (`AsyncSessionLocal`)
- Subtask 2.5 (`User` model)

---

## Subtask 2.10 — Wire Database into App Lifespan (`app/main.py`)

### What
Update `app/main.py` to import the database engine and dispose of it on shutdown.

### Why
- The engine manages connection pools. On shutdown, `engine.dispose()` cleanly closes all pooled connections.
- Without this, database connections leak on server restart.

### Changes to `app/main.py`

```python
# Add this import at the top
from app.db.base import engine

# Update the lifespan function:
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup and shutdown logic.
    Lifespan replaces the deprecated @app.on_event("startup").
    """
    # Startup: Future phases will add model registry loading, etc.
    yield
    # Shutdown: Cleanly close all database connections
    await engine.dispose()
```

### Depends On
- Subtask 2.3 (`engine` from `base.py`)

---

## Subtask 2.11 — Write Tests for the Database Layer

### What
Write tests for the database session lifecycle, ORM models, and repositories.

### Why
- Tests ensure the async session correctly commits, rolls back, and closes.
- Repository tests validate that CRUD operations work with a real (test) database.

### File: `tests/conftest.py` — Shared Test Fixtures

```python
import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base


# Use a separate test database or SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test session that rolls back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
```

> **Note:** For SQLite-based tests you'll need to add `aiosqlite` as a dev dependency:
> `poetry add --group dev aiosqlite`

### File: `tests/unit/test_models.py`

```python
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.ml_model import MLModel, ModelStatus


class TestUserModel:
    """Tests for the User ORM model."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """A user can be created and persisted."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="fakehash123",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_superuser is False

    @pytest.mark.asyncio
    async def test_user_email_unique(self, db_session: AsyncSession):
        """Duplicate emails should raise an IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        user1 = User(email="dup@test.com", username="user1", hashed_password="hash1")
        user2 = User(email="dup@test.com", username="user2", hashed_password="hash2")
        db_session.add(user1)
        await db_session.flush()

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestMLModelModel:
    """Tests for the MLModel ORM model."""

    @pytest.mark.asyncio
    async def test_create_ml_model(self, db_session: AsyncSession):
        """An ML model can be created with all required fields."""
        owner = User(
            email="owner@test.com", username="owner", hashed_password="hash"
        )
        db_session.add(owner)
        await db_session.flush()

        model = MLModel(
            name="test-model",
            version="1.0.0",
            framework="sklearn",
            file_path="/models/test.pkl",
            file_size_bytes=1024,
            owner_id=owner.id,
        )
        db_session.add(model)
        await db_session.flush()
        await db_session.refresh(model)

        assert model.id is not None
        assert model.status == ModelStatus.UPLOADING
```

### File: `tests/unit/test_repositories.py`

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repo import UserRepository


class TestUserRepository:
    """Tests for UserRepository query methods."""

    @pytest.mark.asyncio
    async def test_create_and_get_by_id(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        user = User(
            email="repo@test.com", username="repouser", hashed_password="hash"
        )
        created = await repo.create(user)
        fetched = await repo.get_by_id(created.id)

        assert fetched is not None
        assert fetched.email == "repo@test.com"

    @pytest.mark.asyncio
    async def test_get_by_email(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        user = User(
            email="find@test.com", username="finduser", hashed_password="hash"
        )
        await repo.create(user)
        found = await repo.get_by_email("find@test.com")

        assert found is not None
        assert found.username == "finduser"

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        result = await repo.get_by_email("nonexistent@test.com")
        assert result is None
```

### How to Run
```bash
poetry add --group dev aiosqlite
poetry run pytest tests/ -v
```

### Depends On
- Subtask 2.5 (ORM models)
- Subtask 2.8 (repositories)

---

## Subtask 2.12 — Verification & Smoke Test

### What
After all files are created, run a full end-to-end verification.

### Steps

#### Step 1: Verify PostgreSQL is Running
```bash
psql postgresql://mluser:mlpassword@localhost:5432/mlplatform -c "SELECT 1;"
```

#### Step 2: Generate and Apply Migration
```bash
poetry run alembic revision --autogenerate -m "create_initial_tables"
poetry run alembic upgrade head
```

#### Step 3: Verify Tables
```bash
psql postgresql://mluser:mlpassword@localhost:5432/mlplatform -c "\dt"
```
Expected: `users`, `ml_models`, `prediction_logs` tables listed.

#### Step 4: Run All Tests
```bash
poetry run pytest tests/ -v
```
Expected: All tests pass (Phase 1 config tests + Phase 2 DB tests).

#### Step 5: Start the Application
```bash
poetry run uvicorn app.main:app --reload --port 8000
```
Expected: Server starts without import errors.

#### Step 6: Hit Health Endpoint
```bash
curl http://localhost:8000/health
```

#### Step 7: Linting
```bash
poetry run ruff check app/
poetry run mypy app/
```

---

## Summary of Files Created/Modified

| File | Action | Description |
|---|---|---|
| `app/db/base.py` | **CREATE** | Async engine, session factory, and ORM base class |
| `app/api/deps.py` | **CREATE** | `get_db()` dependency with commit/rollback lifecycle |
| `app/models/user.py` | **CREATE** | User ORM model with UUID PK and relationships |
| `app/models/ml_model.py` | **CREATE** | MLModel ORM model with status enum and composite unique constraint |
| `app/models/prediction_log.py` | **CREATE** | PredictionLog ORM model for audit logging |
| `app/models/__init__.py` | **MODIFY** | Import all models for Alembic autogenerate |
| `alembic/env.py` | **CREATE** | Async-compatible Alembic configuration |
| `alembic.ini` | **MODIFY** | URL override note (runtime override from env.py) |
| `app/repositories/base.py` | **CREATE** | Generic BaseRepository with CRUD operations |
| `app/repositories/user_repo.py` | **CREATE** | User-specific queries (by email, username) |
| `app/repositories/model_repo.py` | **CREATE** | MLModel-specific queries (active, by owner) |
| `app/repositories/prediction_repo.py` | **CREATE** | PredictionLog-specific queries |
| `app/db/init_db.py` | **CREATE** | Optional seed script for dev superuser |
| `app/main.py` | **MODIFY** | Add engine.dispose() on shutdown |
| `tests/conftest.py` | **CREATE** | Shared test fixtures (test DB, session) |
| `tests/unit/test_models.py` | **CREATE** | ORM model unit tests |
| `tests/unit/test_repositories.py` | **CREATE** | Repository unit tests |

## Dependency Graph

```
Subtask 2.1 (verify deps)  ──→  Subtask 2.3 (db/base.py)  ──→  Subtask 2.4 (deps.py)
                                        │
Subtask 2.2 (PostgreSQL)  ─────────────┤
                                        │
                                        ├──→  Subtask 2.5 (ORM models)
                                        │           │
                                        │           ├──→  Subtask 2.6 (alembic/env.py)
                                        │           │           │
                                        │           │           └──→  Subtask 2.7 (run migrations)
                                        │           │
                                        │           └──→  Subtask 2.8 (repositories)
                                        │                       │
                                        │                       └──→  Subtask 2.9 (init_db.py)
                                        │
                                        └──→  Subtask 2.10 (wire main.py)

Subtask 2.11 (tests) depends on: 2.5, 2.8
Subtask 2.12 (verification) is the final gate
```

> Independent subtasks: 2.1 and 2.2 can run in parallel.
> Subtask 2.3 depends on 2.1. Subtask 2.7 depends on 2.2, 2.5, and 2.6.
> Subtask 2.12 is the final verification gate — run it after everything else.
