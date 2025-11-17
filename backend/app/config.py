"""Application configuration helpers."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Centralized configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8")

    app_name: str = "GaussDB Data Hub"
    environment: str = "dev"

    # Database connection pieces (fallback to local sqlite for dev/testing)
    database_url: Optional[str] = None
    gauss_host: str = "localhost"
    gauss_port: int = 15432
    gauss_db: str = "gaussdb"
    gauss_user: str = "gaussdb"
    gauss_password: str = "secret"
    gauss_sslmode: str = "prefer"

    # Flink analytics job
    flink_job_name: str = "GaussDBFlinkAnalytics"
    flink_parallelism: int = 1

    # API behavior
    allow_origins: List[str] = ["http://localhost:4173", "http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:8080", "*"]

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.gauss_user}:{self.gauss_password}"
            f"@{self.gauss_host}:{self.gauss_port}/{self.gauss_db}?sslmode={self.gauss_sslmode}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
