"""Application settings loaded from the environment.

Values are validated at access time; callers should treat the returned
``Settings`` as immutable. The settings object is intentionally separate
from the domain models — it is infrastructure configuration, not a
domain concept.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the harness.

    Settings are read from environment variables (case-insensitive). Use
    :func:`get_settings` to obtain a cached instance.
    """

    model_config = SettingsConfigDict(
        env_file=None,  # .env loading handled at package-import time
        case_sensitive=False,
        extra="ignore",
    )

    # Auth
    claude_code_oauth_token: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)

    # Model selection
    claude_model_default: str = Field(default="claude-haiku-4-5")

    # Logging
    rf_skill_eval_log_level: str = Field(default="INFO")

    def has_auth(self) -> bool:
        """Return True iff some form of Claude authentication is present."""

        return bool(self.claude_code_oauth_token or self.anthropic_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""

    return Settings()


def configure_logging(level: str | None = None) -> None:
    """Configure root logging using the harness level env var.

    The harness CLI uses ``rich`` for console UX; library modules use
    stdlib :mod:`logging` so tests can capture output easily.
    """

    resolved = (level or os.environ.get("RF_SKILL_EVAL_LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, resolved, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
