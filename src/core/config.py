from urllib.parse import quote

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из окружения и файла .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
    )

    DEBUG: bool = False
    SERVICE_NAME: str = "async-payment-processing-service"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "dev"
    LOG_LEVEL_RULES: str = "uvicorn.access:WARNING,sqlalchemy.engine:WARNING"
    API_KEY: SecretStr = Field(default=SecretStr("development-only-key"), min_length=1)

    DB_HOST: str = "localhost"
    DB_PORT: int = Field(default=5432, ge=1, le=65535)
    DB_NAME: str = "payments"
    DB_USER: str = "payments"
    DB_PASSWORD: SecretStr = SecretStr("payments")

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = Field(default=5672, ge=1, le=65535)
    RABBITMQ_USER: str = "payments"
    RABBITMQ_PASSWORD: SecretStr = SecretStr("payments")
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_CONNECT_TIMEOUT: float = Field(default=5, gt=0, allow_inf_nan=False)
    RABBITMQ_PUBLISH_TIMEOUT: float = Field(default=5, gt=0, allow_inf_nan=False)

    OUTBOX_POLL_INTERVAL: float = Field(default=1, gt=0, allow_inf_nan=False)
    OUTBOX_BATCH_SIZE: int = Field(default=100, gt=0)

    WEBHOOK_TIMEOUT: float = Field(default=5, gt=0, allow_inf_nan=False)

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD.get_secret_value(),
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    @property
    def rabbitmq_url(self) -> str:
        user = quote(self.RABBITMQ_USER, safe="")
        password = quote(self.RABBITMQ_PASSWORD.get_secret_value(), safe="")
        vhost = quote(self.RABBITMQ_VHOST, safe="")
        return f"amqp://{user}:{password}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{vhost}"


settings = Settings()
