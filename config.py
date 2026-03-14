"""Runtime configuration for the multi-agent clinical evaluation system."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", os.getenv("TAVILY_API_KEY"))
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder-32b:free")
    max_batch_size: int = int(os.getenv("MAX_BATCH_SIZE", "20"))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
    retries: int = int(os.getenv("LLM_RETRIES", "3"))

    # Free-tier friendly default for sequential fallbacks.
    rpm_soft_limit: int = int(os.getenv("RPM_SOFT_LIMIT", "12"))


SETTINGS = Settings()


def has_llm_provider() -> bool:
    return bool(SETTINGS.gemini_api_key or SETTINGS.openrouter_api_key)


def has_web_search() -> bool:
    return bool(SETTINGS.tavily_api_key)
