"""Process-level settings sourced from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name, default)
    return val if val not in ("", None) else default


@dataclass(frozen=True)
class Settings:
    database_url: str = _env("DATABASE_URL", "sqlite:///./github-watcher.db")  # type: ignore[assignment]
    github_token: str | None = _env("GITHUB_TOKEN")
    github_api: str = _env("GITHUB_API", "https://api.github.com")  # type: ignore[assignment]
    # Default poll interval (seconds) when a watch does not set its own.
    default_interval: int = int(_env("DEFAULT_INTERVAL", "60"))  # type: ignore[arg-type]
    # Cap on persisted seen-SHAs per watch.
    seen_cap: int = int(_env("SEEN_CAP", "1000"))  # type: ignore[arg-type]
    log_level: str = _env("LOG_LEVEL", "INFO")  # type: ignore[assignment]
    user_agent: str = _env("USER_AGENT", "github-watcher/0.1")  # type: ignore[assignment]


settings = Settings()
