from logging import config as logging_config

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logger import LOGGING_CONFIG

logging_config.dictConfig(LOGGING_CONFIG)


class ProjectSettings(BaseSettings):
    # FastAPI
    project_name: str
    project_summary: str
    project_version: str
    project_terms_of_service: str
    project_tags: list = Field(
        default=[
            {
                "name": "tests",
                "description": "Operations with tests.",
            },
        ]
    )
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class PostgresSettings(BaseSettings):
    """Настройки Postgres."""

    db: str
    host: str
    port: int
    user: str
    password: str
    dsn: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_prefix="POSTGRES_"
    )

    def model_post_init(self, __context):
        """Формируем DSN после загрузки переменных"""

        self.dsn = f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    """Настройки Redis."""

    host: str
    port: int
    user: str
    password: str
    db_index: int
    dsn: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_prefix="REDIS_"
    )

    def model_post_init(self, __context):
        """Формируем DSN после загрузки переменных."""

        self.dsn = f"redis://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_index}"


class DeribitSettings(BaseSettings):
    """Настройки Deribit API."""

    base_url: str = "https://www.deribit.com/api/v2"
    api_key: str = ""
    api_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_prefix="DERIBIT_"
    )


class CelerySettings(BaseSettings):
    """Настройки Celery."""

    broker_url: str = ""
    result_backend: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_prefix="CELERY_"
    )

    def model_post_init(self, __context):
        """Формируем URLs после загрузки переменных."""
        if not self.broker_url:
            self.broker_url = redis_settings.dsn
        if not self.result_backend:
            self.result_backend = redis_settings.dsn


postgres_settings = PostgresSettings()  # type: ignore
project_settings = ProjectSettings()  # type: ignore
redis_settings = RedisSettings()  # type: ignore
deribit_settings = DeribitSettings()  # type: ignore
celery_settings = CelerySettings()  # type: ignore
