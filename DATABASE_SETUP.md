# Database Setup Guide

This guide explains how to set up the Agent OS database from scratch, including all necessary extensions, schemas, and tables.

## 📋 Prerequisites

- PostgreSQL 15+ with pgvector
- Python 3.11+
- Poetry
- Docker (optional, but recommended)

## 🚀 Quick Setup (Docker)

If you're using Docker (recommended):

```bash
# 1. Start containers
docker-compose up -d postgres

# 2. Run migrations
poetry run alembic upgrade head

# Or use the setup script
poetry run python scripts/setup_database.py
```

## 🛠 Manual Setup (Local PostgreSQL)

### 1. Configure Environment Variables

Create `.env.local` with your settings:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=agent_os
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
WRITER_DB_URL=postgresql+asyncpg://your_username:your_password@localhost:5432/agent_os
READER_DB_URL=postgresql+asyncpg://your_username:your_password@localhost:5432/agent_os
AGNO_DB_URL=postgresql://your_username:your_password@localhost:5432/agent_os?options=-csearch_path=ai
```

### 2. Run Setup

```bash
# Method 1: Automated script
poetry run python scripts/setup_database.py

# Method 2: Direct Alembic
poetry run alembic upgrade head

# Check status
poetry run alembic current
poetry run python scripts/setup_database.py --status
```

## 📊 Migration Structure

The system uses an ordered sequence of migrations:

### 1. **Extensions** (`ae657b67c7e7_create_postgresql_extensions`)
- Creates necessary PostgreSQL extensions
- `uuid-ossp`: For UUID generation
- `vector`: For pgvector (embeddings)

### 2. **AI Schema** (`729532316381_create_ai_schema`)
- Creates `ai` schema for Agno integration
- Sets up appropriate permissions

### 3. **Agents Table** (`e27ee43d23db_create_agents_table`)
- Creates `agents` table with all fields
- Includes `llm_model` and `default_language`
- Adds performance indexes
- Configures automatic `updated_at` triggers

## 🏗 Agents Table Structure

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(255) NOT NULL UNIQUE,
    description VARCHAR(1000),
    instructions JSON,
    is_active BOOLEAN DEFAULT FALSE,
    llm_model VARCHAR(100),
    default_language VARCHAR(10) DEFAULT 'pt-BR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX ix_agents_is_active ON agents (is_active);
CREATE INDEX ix_agents_created_at ON agents (created_at);

-- Trigger for updated_at
CREATE TRIGGER update_agents_updated_at 
    BEFORE UPDATE ON agents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 🔧 Useful Commands

```bash
# View current status
poetry run alembic current

# View complete history
poetry run alembic history --verbose

# Apply migrations
poetry run alembic upgrade head

# Revert one migration
poetry run alembic downgrade -1

# Create new migration
poetry run alembic revision --autogenerate -m "description"
```

## 🆘 Troubleshooting

### Database already exists
```bash
# Via Docker
docker exec fastapi-postgres psql -U fastapi -d fastapi -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Or reset completely
docker-compose down -v
docker-compose up -d postgres
poetry run alembic upgrade head
```

### Extensions not found
```bash
# Check if pgvector is installed in container
docker exec fastapi-postgres psql -U fastapi -d fastapi -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

### Permissions
```bash
# Check ai schema permissions
docker exec fastapi-postgres psql -U fastapi -d fastapi -c "\\dn+"
```

## 🔄 Complete Reset

To completely reset the database:

```bash
# 1. Stop application
docker-compose down

# 2. Remove volumes (WARNING: deletes all data)
docker-compose down -v

# 3. Restart
docker-compose up -d postgres

# 4. Apply migrations
poetry run alembic upgrade head
```

## ✅ Success Verification

After setup, you should have:
- ✅ Extensions `uuid-ossp` and `vector` created
- ✅ Schema `ai` created
- ✅ Table `agents` with all fields
- ✅ Indexes and triggers working
- ✅ Clean and organized migration history