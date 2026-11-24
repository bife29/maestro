"""Typed settings loaded from `maestro.toml` + environment (MAESTRO_<SECTION>__<KEY>).

No secrets live here: tokens are read from the environment by the adapters that need them.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class DevOpsSettings(BaseModel):
    provider: str = "local"
    data_dir: Path = Path("data/local")


class LLMSettings(BaseModel):
    provider: str = "dry"
    timeout_s: int = 60
    max_retries: int = 2
    max_tokens: int = 4000


class ReviewSettings(BaseModel):
    max_files: int = 50
    max_lines: int = 3000
    cost_limit_usd: float = 0.50
    kb_top_k: int = 6


class KBSettings(BaseModel):
    path: Path = Path("data/local/kb.sqlite")
    sources: list[Path] = Field(default_factory=lambda: [Path("data/sample/docs")])


class AuditSettings(BaseModel):
    dir: Path = Path("audit")


class SeedSettings(BaseModel):
    default: int = 42
    repositories: int = 6
    months: int = 12


class Settings(BaseSettings):
    """Precedence (highest first): explicit kwargs → environment → TOML file → defaults."""

    model_config = SettingsConfigDict(env_prefix="MAESTRO_", env_nested_delimiter="__", extra="ignore")

    devops: DevOpsSettings = DevOpsSettings()
    llm: LLMSettings = LLMSettings()
    review: ReviewSettings = ReviewSettings()
    kb: KBSettings = KBSettings()
    audit: AuditSettings = AuditSettings()
    seed: SeedSettings = SeedSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, env_settings, TomlConfigSettingsSource(settings_cls))


def read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from `config_path` (default `maestro.toml`); environment variables override the file."""
    path = config_path or Path("maestro.toml")

    class _FileBoundSettings(Settings):
        model_config = SettingsConfigDict(**{**Settings.model_config, "toml_file": path})

    return _FileBoundSettings()
