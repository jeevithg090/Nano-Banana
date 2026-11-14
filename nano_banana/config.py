"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

DEFAULT_MODEL = "gemini-2.5-flash-image"


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value}")
    return value


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the web app."""

    gemini_api_key: str | None
    gemini_model: str = DEFAULT_MODEL
    secret_key: str = ""
    max_images: int = 5
    max_upload_mb: int = 16
    max_prompt_chars: int = 2000

    @property
    def max_content_length(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_model=os.getenv("GEMINI_MODEL") or DEFAULT_MODEL,
            # A random per-process key is acceptable: the app keeps no login sessions.
            secret_key=os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32),
            max_images=_int_env("MAX_IMAGES", 5),
            max_upload_mb=_int_env("MAX_UPLOAD_MB", 16),
            max_prompt_chars=_int_env("MAX_PROMPT_CHARS", 2000),
        )
