from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/bazaar.db"
    poll_interval: float = Field(default=30, ge=20)
    tax_rate: float = Field(default=0.01125, ge=0, lt=1)
    order_book_depth: int = Field(default=30, ge=1, le=30)
    metadata_interval: float = Field(default=3600, ge=3600)
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    collector_enabled: bool = True
    backup_directory: Path = Path("backups")
    backup_retention_days: int = Field(default=14, ge=1)

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
