"""Runtime settings for the SupplyIQ backend."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource

BACKEND_DIR = Path(__file__).resolve().parent


class _RawCorsOriginsMixin:
    """Preserves raw CORS origin values for custom parsing."""

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        """Skips automatic JSON parsing for CORS origins."""

        if field_name == "cors_origins" and isinstance(value, str):
            return value
        return super().prepare_field_value(field_name, field, value, value_is_complex)  # type: ignore[misc]


class SupplyIQEnvSettingsSource(_RawCorsOriginsMixin, EnvSettingsSource):
    pass


class SupplyIQDotEnvSettingsSource(_RawCorsOriginsMixin, DotEnvSettingsSource):
    pass


class Settings(BaseSettings):
    """Loads backend configuration from the local .env file and container env."""

    app_name: str = "SupplyIQ API"
    api_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+psycopg://supplyiq:supplyiq@localhost:5432/supplyiq",
        validation_alias=AliasChoices("BACKEND_DATABASE_URL", "DATABASE_URL"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("BACKEND_REDIS_URL", "REDIS_URL"),
    )
    cache_ttl_seconds: int = 300
    request_timeout_seconds: int = 30
    max_page_size: int = 200
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    auto_bootstrap: bool = Field(
        default=True,
        validation_alias=AliasChoices("BACKEND_AUTO_BOOTSTRAP", "AUTO_BOOTSTRAP"),
    )

    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=("settings_",),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Overrides settings sources to preserve raw CORS values for parsing."""

        return (
            init_settings,
            SupplyIQEnvSettingsSource(settings_cls),
            SupplyIQDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """Accepts comma-separated CORS origins from environment variables."""

        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                    raise ValueError("CORS origins JSON must be an array of strings.")
                return parsed
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Returns cached backend settings."""

    return Settings()
