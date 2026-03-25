# ModelForge - FastAPI ML Model Serving Platform

A production-grade REST API platform for serving machine learning models built with FastAPI.

## Features

- **User Authentication** - JWT-based auth with access and refresh tokens
- **ML Model Management** - Upload, version, and manage scikit-learn, PyTorch, and ONNX models
- **Real-time Predictions** - Serve predictions via versioned API endpoints
- **Batch Predictions** - Process CSV/JSON files for bulk inference
- **Caching** - Redis-powered caching for deterministic predictions
- **Logging & Observability** - Structured logging with request tracing
- **Async Architecture** - Full async support for high concurrency
- **Docker Ready** - Containerized deployment with Docker Compose

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI |
| Database | PostgreSQL (async with SQLAlchemy 2.0) |
| ORM | SQLAlchemy 2.0 (async) |
| Cache | Redis |
| Auth | JWT (python-jose + passlib) |
| ML Serving | joblib / torch / onnx |
| Testing | pytest + httpx |
| Linting | Ruff |
| Type Checking | mypy |

## Project Structure

```
ml-platform/
├── app/
│   ├── api/
│   │   └── v1/              # API routes
│   │       ├── auth.py
│   │       ├── models.py
│   │       ├── predictions.py
│   │       └── health.py
│   ├── core/
│   │   ├── config.py        # Settings management
│   │   ├── exceptions.py     # Custom exceptions
│   │   └── security.py      # JWT utilities
│   ├── db/
│   │   ├── base.py          # SQLAlchemy setup
│   │   └── init_db.py
│   ├── models/              # ORM models
│   │   ├── user.py
│   │   ├── ml_model.py
│   │   └── prediction_log.py
│   ├── schemas/             # Pydantic schemas
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic
│   ├── ml/                 # ML utilities
│   │   ├── registry.py
│   │   ├── loader.py
│   │   └── validator.py
│   ├── middleware/          # Custom middleware
│   └── main.py              # App factory
├── tests/
│   ├── unit/
│   └── integration/
├── alembic/                 # Database migrations
├── model_store/            # ML model storage
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis

### Installation

1. Clone the repository:
```bash
git clone https://github.com/hamza-prof/ModelForge-FastAPI-platform-for-serving-ML-models.git
cd ModelForge-FastAPI-platform-for-serving-ML-models
```

2. Install dependencies with Poetry:
```bash
poetry install
```

3. Copy the environment template:
```bash
cp .env.example .env
```

4. Update `.env` with your configuration:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mlplatform
SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379
```

5. Run database migrations:
```bash
poetry run alembic upgrade head
```

6. Start the development server:
```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/redoc`

### Using Docker

```bash
docker compose up --build
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user

### Models
- `POST /api/v1/models/` - Upload ML model
- `GET /api/v1/models/` - List user's models
- `GET /api/v1/models/{id}` - Get model details

### Predictions
- `POST /api/v1/predict/{model_id}` - Run single prediction
- `POST /api/v1/predict/batch/{model_id}` - Run batch predictions

### Health
- `GET /api/v1/health` - Health check

## Testing

Run all tests:
```bash
poetry run pytest
```

Run with coverage:
```bash
poetry run pytest --cov=app
```

## Linting & Type Checking

```bash
poetry run ruff check app/
poetry run mypy app/
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | ML Platform |
| `APP_VERSION` | Application version | 1.0.0 |
| `ENVIRONMENT` | Environment (development/staging/production) | development |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | 7 |
| `REDIS_URL` | Redis connection string | redis://localhost:6379 |
| `MODEL_STORE_PATH` | Model storage directory | ./model_store |
| `MAX_MODEL_SIZE_MB` | Max model file size (MB) | 500 |
| `ALLOWED_ORIGINS` | CORS allowed origins | ["http://localhost:3000"] |

## Development

The project follows a layered architecture:

```
HTTP Request → Router → Schema → Service → Repository → Model/DB
```

- **Routers** - Handle HTTP routing, no business logic
- **Schemas** - Pydantic models for request/response validation
- **Services** - Business logic, no direct DB access
- **Repositories** - Data access layer only

## License

MIT License
