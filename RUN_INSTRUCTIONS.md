# How to Run and Test the Project

## Prerequisites
- PostgreSQL running (docker start mlplatform-postgres)
- Poetry installed

## Run the Project

1. **Install dependencies:**
   ```bash
   cd /mnt/c/Users/abcd/Desktop/run_any_model
   poetry install
   ```

2. **Start the FastAPI server:**
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```

3. **Test the Health Endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Access API Documentation:**
   Open in browser: http://localhost:8000/api/docs

## Run Tests

```bash
poetry run pytest tests/ -v
```

## Linting & Type Checking

```bash
poetry run ruff check app/
poetry run mypy app/
```

## Database Migrations

- Apply migrations: `poetry run alembic upgrade head`
- Create new migration: `poetry run alembic revision --autogenerate -m "your_message"`