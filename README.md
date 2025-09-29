# Agent OS

AI agent system with semantic caching and WhatsApp integration.

## Initial Setup

### 1. Clone and Dependencies

```bash
git clone <repository-url>
cd agent-os
poetry install
```

### 2. Environment Variables

Create `.env`:

```env
# OpenAI (required for semantic cache)
OPENAI_API_KEY=sk-...

# Redis (required for cache)
REDIS_HOST=localhost
REDIS_PORT=6379

# WhatsApp (optional)
WAHA_API_URL=http://localhost:3000/api
WAHA_API_KEY=your-api-key
WEBHOOK_ALLOWED_NUMBERS=551141059060,5511999998888
```

### 3. Initialize

```bash
# Install dependencies
make install

# Start all services (PostgreSQL, Redis, WAHA, API)
make docker-up

# Migrate database
make db-upgrade

# Seed agents
python scripts/seeders/agent_seeder.py
```

### 4. Development Mode

```bash
# For local development (without containers)
export WRITER_DB_URL="sqlite+aiosqlite:///test.db"
export READER_DB_URL="sqlite+aiosqlite:///test.db"
make dev  # Start API locally with auto-reload
```

## Endpoints

- **API**: http://localhost:8000/api/v1/
- **Health**: http://localhost:8000/api/v1/health
- **Webhook**: http://localhost:8000/api/v1/webhook/waha

## Testing

```bash
make test
```
