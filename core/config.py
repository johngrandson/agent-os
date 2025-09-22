import os

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    WRITER_DB_URL: str = "postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi"
    READER_DB_URL: str = "postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi"

    # Database configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "fastapi"
    POSTGRES_USER: str = "fastapi"
    POSTGRES_PASSWORD: str = "fastapi"
    JWT_SECRET_KEY: str = "fastapi"
    JWT_ALGORITHM: str = "HS256"
    SENTRY_SDN: str = ""

    # Encryption key for sensitive data
    ENCRYPTION_KEY: str = ""

    HOST_API: str = ""
    API_KEY: str = ""

    @property
    def database_url(self) -> str:
        """Construct database URL from components"""
        if self.WRITER_DB_URL:
            return self.WRITER_DB_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"


class TestConfig(Config):
    DEBUG: bool = False

    class Config:
        extra = "ignore"  # Ignore extra fields from environment


class E2EConfig(Config):
    DEBUG: bool = False
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433  # Different port for E2E
    POSTGRES_DB: str = "fastapi_e2e"
    POSTGRES_USER: str = "fastapi_e2e"
    POSTGRES_PASSWORD: str = "fastapi_e2e_test"

    class Config:
        extra = "ignore"  # Ignore extra fields from environment


class LocalConfig(Config):
    class Config:
        extra = "ignore"  # Ignore extra fields from environment


class ProductionConfig(Config):
    DEBUG: bool = False

    class Config:
        extra = "ignore"  # Ignore extra fields from environment


def get_config():
    env = os.getenv("ENV", "local")
    config_type = {
        "test": TestConfig(),
        "e2e": E2EConfig(),
        "local": LocalConfig(),
        "dev": LocalConfig(),  # Map 'dev' to LocalConfig for Docker Compose
        "prod": ProductionConfig(),
    }
    return config_type.get(env, LocalConfig())


config: Config = get_config()
