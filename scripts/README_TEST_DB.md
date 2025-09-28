# 🗄️ Test Database Setup

## ⚠️ IMPORTANT: Test Configuration

Tests use the same database as development but with environment variable `ENV=test` to distinguish test vs development modes.

### Current Configuration:
- **Database**: `fastapi:fastapi@localhost:5432/fastapi` (same as development)
- **Environment**: Set via `ENV=test`

## 🔧 Setup Instructions

### 1. Start PostgreSQL:

```bash
# Start PostgreSQL via Docker
make docker-up

# Or start your local PostgreSQL instance
```

### 2. Run migrations:
```bash
# Run migrations
make db-upgrade
```

### 3. For CI/CD (GitHub Actions):
Already configured! The CI uses environment variables.

## 🧪 Running Tests

Tests will automatically use the test environment:

```bash
# Run all tests
poetry run pytest tests/

# Specific test types
poetry run pytest tests/integration/agents/
```

## 🛡️ Safety Features

- ✅ **Environment separation**: Tests use ENV=test
- ✅ **Simple configuration**: Same database, different environment
- ✅ **Automatic configuration**: pytest.ini sets test environment variables
- ✅ **CI compatibility**: Works with GitHub Actions

## 📋 Environment Variables

The test environment automatically sets:
```
ENV=test
DATABASE_URL=postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi
WRITER_DB_URL=postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi
READER_DB_URL=postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi
```

## 🔍 Verification

To verify your test setup is working:
```bash
# Run a simple test
poetry run pytest tests/unit/core/test_logger.py -v

# Run integration tests
poetry run pytest tests/integration/agents/ -v
```
