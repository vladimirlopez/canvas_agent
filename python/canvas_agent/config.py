"""Unified configuration loader for CanvasAgent.

Order of precedence for sensitive values:
1. Explicit function arguments (future use)
2. Environment variables / .env
3. (Optionally) Streamlit secrets when running app
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # pragma: no cover
    pass


@dataclass(frozen=True)
class CanvasSettings:
    base_url: str
    token: str


@dataclass(frozen=True)
class OllamaSettings:
    enabled: bool
    host: str


@dataclass(frozen=True)
class AppSettings:
    canvas: CanvasSettings
    ollama: OllamaSettings
    debug: bool = False


@lru_cache(maxsize=1)
def load_settings(streamlit_secrets: Optional[dict] = None) -> AppSettings:
    def pick(key: str, default: str = "") -> str:
        if streamlit_secrets and key in streamlit_secrets:
            return str(streamlit_secrets[key])
        return os.getenv(key, default)

    base_url = pick("CANVAS_BASE_URL", "https://canvas.instructure.com")
    token = pick("CANVAS_TOKEN") or pick("CANVAS_API_TOKEN")
    ollama_host = pick("OLLAMA_HOST", "http://localhost:11434")
    ollama_enabled = bool(pick("OLLAMA_ENABLED", "1") != "0")
    debug = pick("CANVAS_AGENT_DEBUG", "0") == "1"

    return AppSettings(
        canvas=CanvasSettings(base_url=base_url, token=token),
        ollama=OllamaSettings(enabled=ollama_enabled, host=ollama_host),
        debug=debug,
    )


__all__ = ["load_settings", "AppSettings", "CanvasSettings", "OllamaSettings"]
