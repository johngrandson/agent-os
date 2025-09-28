# Optimized multi-stage build for FastAPI app
FROM python:3.11-slim-bullseye as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry temporarily
RUN pip install poetry

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Builder stage
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install CPU-only PyTorch first to avoid CUDA version
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install all dependencies via Poetry
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Production stage
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY . .

# Create non-root user and fix permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /usr/local/bin/ \
    && chown -R appuser:appuser /usr/local/lib/python3.11/site-packages/ \
    && chmod -R 755 /usr/local/bin/ \
    && chmod -R 755 /usr/local/lib/python3.11/site-packages/ \
    && chmod -R 755 /app/app/domains/ \
    && chmod -R 755 /app/app/shared/ \
    && chmod -R 755 /app/app/infrastructure/ \
    && chmod -R 755 /app/app/events/ \
    && chmod -R 755 /app/core/

USER appuser

# Expose port
EXPOSE 8000

# Production command
CMD ["python", "-m", "uvicorn", "app.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM builder AS development

# Copy application code
COPY . .

# Create non-root user and fix permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /usr/local/bin/ \
    && chown -R appuser:appuser /usr/local/lib/python3.11/site-packages/ \
    && chmod -R 755 /usr/local/bin/ \
    && chmod -R 755 /usr/local/lib/python3.11/site-packages/ \
    && chmod -R 755 /app/app/domains/ \
    && chmod -R 755 /app/app/shared/ \
    && chmod -R 755 /app/app/infrastructure/ \
    && chmod -R 755 /app/app/events/ \
    && chmod -R 755 /app/core/

USER appuser

# Expose port
EXPOSE 8000

# Development command
CMD ["python", "-m", "uvicorn", "app.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]
