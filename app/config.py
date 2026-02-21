"""Application configuration loaded from environment variables."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings – values come from .env or environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Agent Config
    evaluator_threshold: float = 0.75
    max_revision_iterations: int = 3
    unknown_confidence_threshold: float = 0.4

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Paths
    cv_profile_path: str = "data/cv_profile.json"
    log_dir: str = "logs"


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings()


def load_cv_profile(path: str | None = None) -> dict:
    """Load CV profile JSON file and return as dict."""
    settings = get_settings()
    profile_path = Path(path or settings.cv_profile_path)
    if not profile_path.exists():
        logging.warning("CV profile not found at %s – using empty profile.", profile_path)
        return {}
    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_logging() -> None:
    """Configure root logger based on settings."""
    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
