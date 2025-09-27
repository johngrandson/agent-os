import os

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Simplified application configuration"""

    # Application Settings
    ENV: str = "development"
    DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    HOST_API: str = ""
    API_KEY: str = ""
    SENTRY_SDN: str = ""

    # Database Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "fastapi"
    POSTGRES_USER: str = "fastapi"
    POSTGRES_PASSWORD: str = "fastapi"
    WRITER_DB_URL: str = "postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi"
    READER_DB_URL: str = "postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi"
    AGNO_DB_URL: str = ""

    # Security Configuration
    JWT_SECRET_KEY: str = "fastapi"
    JWT_ALGORITHM: str = "HS256"
    ENCRYPTION_KEY: str = ""

    # Agent Configuration
    AGNO_DEFAULT_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str | None = None

    # AI Services Configuration (HuggingFace)
    HUGGINGFACE_API_TOKEN: str = ""
    HUGGINGFACE_CACHE_DIR: str = "/tmp/hf_cache"

    # Specialized AI Service Models
    HUGGINGFACE_FRAUD_MODEL: str = "distilbert-base-uncased"
    HUGGINGFACE_SENTIMENT_MODEL: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    HUGGINGFACE_MODERATION_MODEL: str = "unitary/toxic-bert"
    HUGGINGFACE_CLASSIFICATION_MODEL: str = "facebook/bart-large-mnli"

    # WAHA (WhatsApp API) Configuration
    WAHA_API_URL: str = "http://waha:3000/api"
    WAHA_BASE_URL: str = "http://waha:3000"
    WAHA_API_KEY: str = ""
    WAHA_SESSION_NAME: str = "default"
    WAHA_LOG_FORMAT: str = "JSON"

    # Webhook Configuration
    WHATSAPP_HOOK_URL: str = "http://api:8000/api/v1/waha/webhook"
    WHATSAPP_HOOK_EVENTS: str = "message,session.status"
    WHATSAPP_HOOK_RETRIES_ATTEMPTS: int = 4
    WHATSAPP_HOOK_RETRIES_DELAY_SECONDS: int = 3

    # Webhook Processing Timeouts (seconds)
    AGENT_PROCESSING_TIMEOUT: int = 30
    AGENT_GET_TIMEOUT: int = 5
    AGENT_INIT_TIMEOUT: int = 10
    WEBHOOK_MAX_RETRIES: int = 3

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_URL: str = ""
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_CONNECTION_POOL_SIZE: int = 10
    REDIS_CONNECTION_TIMEOUT: int = 5
    REDIS_RETRY_ATTEMPTS: int = 3
    REDIS_RETRY_DELAY: float = 1.0

    # Event System Configuration
    USE_REDIS_EVENTS: bool = False
    REDIS_EVENT_CHANNEL_PREFIX: str = "agent_os_events"
    REDIS_EVENT_HISTORY_TTL: int = 604800  # 7 days in seconds
    REDIS_EVENT_MAX_HISTORY: int = 10000

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v):
        if v and not v.startswith("sk-"):
            msg = "OpenAI API key must start with sk-"
            raise ValueError(msg)
        return v

    @property
    def database_url(self) -> str:
        """Construct database URL from components"""
        if self.WRITER_DB_URL:
            return self.WRITER_DB_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def writer_db_url(self) -> str:
        """Writer database URL - use WRITER_DB_URL or construct from components"""
        if self.WRITER_DB_URL:
            return self.WRITER_DB_URL
        return self.database_url

    @property
    def reader_db_url(self) -> str:
        """Reader database URL - use READER_DB_URL or construct from components"""
        if self.READER_DB_URL:
            return self.READER_DB_URL
        return self.database_url

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components"""
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


# Environment-specific overrides
_env_overrides: dict[str, dict[str, str | int | bool]] = {
    "test": {"DEBUG": False},
    "e2e": {
        "DEBUG": False,
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": 5433,
        "POSTGRES_DB": "fastapi_e2e",
        "POSTGRES_USER": "fastapi_e2e",
        "POSTGRES_PASSWORD": "fastapi_e2e_test",
    },
    "prod": {"DEBUG": False},
}


def get_config() -> Config:
    """Get configuration with environment-specific overrides"""
    env = os.getenv("ENV", "local")
    config = Config()

    # Apply environment-specific overrides
    if env in _env_overrides:
        overrides = _env_overrides[env]
        if isinstance(overrides, dict):
            for key, value in overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    return config


config: Config = get_config()
