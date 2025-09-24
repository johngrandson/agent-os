-- PostgreSQL initialization script for FastAPI development environment
-- This script sets up the database and user for the FastAPI application

-- Create the fastapi database if it doesn't exist (already handled by POSTGRES_DB env var)
-- CREATE DATABASE fastapi;

-- Create the fastapi user if it doesn't exist (already handled by POSTGRES_USER env var)
-- CREATE USER fastapi WITH PASSWORD 'fastapi';

-- Grant all privileges on the database to the user
GRANT ALL PRIVILEGES ON DATABASE fastapi TO fastapi;

-- Grant schema permissions
GRANT ALL PRIVILEGES ON SCHEMA public TO fastapi;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fastapi;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fastapi;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO fastapi;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO fastapi;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Log initialization completion
SELECT 'FastAPI database with pgvector initialization completed successfully' as status;
