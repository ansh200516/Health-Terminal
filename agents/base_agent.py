"""Base LLM agent with Gemini + Tavily support and robust fallback."""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from config import SETTINGS, has_web_search

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None

try:
    from tavily import TavilyClient
except Exception:  # pragma: no cover
    TavilyClient = None


@dataclass
class AgentResult:
    wrong: bool
    expected: str | None
    confidence: float
    rationale: str


class BaseLLMAgent:
    """Base class used by all evaluator agents."""

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self._last_call_ts = 0.0
        self._min_interval = 60.0 / max(1, SETTINGS.rpm_soft_limit)

        self._gemini_model = None
        if SETTINGS.gemini_api_key and genai is not None:
            genai.configure(api_key=SETTINGS.gemini_api_key)
            self._gemini_model = genai.GenerativeModel(SETTINGS.gemini_model)

        self._tavily = None
        if has_web_search() and TavilyClient is not None:
            self._tavily = TavilyClient(api_key=SETTINGS.tavily_api_key)

    async def _respect_rate_limit(self) -> None:
        elapsed = time.time() - self._last_call_ts
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_call_ts = time.time()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def call_llm_json(self, user_prompt: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        """Return JSON from model, else deterministic fallback payload."""
        if self._gemini_model is None:
            return fallback

        await self._respect_rate_limit()
        full_prompt = (
            f"{self.system_prompt}\n\n"
            "Return strict JSON only. Do not include markdown fences.\n"
            f"{user_prompt}"
        )
        try:
            # SDK is sync; wrap in thread for asyncio compatibility.
            response = await asyncio.to_thread(
                self._gemini_model.generate_content,
                full_prompt,
                generation_config={"temperature": 0.0, "response_mime_type": "application/json"},
            )
            text = getattr(response, "text", "") or ""
            return json.loads(text)
        except Exception:
            return fallback

    async def web_search(self, query: str) -> List[Dict[str, str]]:
        """Use Tavily when available; otherwise return empty evidence."""
        if not self._tavily:
            return []
        try:
            result = await asyncio.to_thread(
                self._tavily.search,
                query=query,
                search_depth="basic",
                max_results=3,
            )
            return result.get("results", []) if isinstance(result, dict) else []
        except Exception:
            return []

    async def call_openrouter_json(self, messages: List[Dict[str, str]]) -> Dict[str, Any] | None:
        """Optional OpenRouter fallback for users with API key."""
        if not SETTINGS.openrouter_api_key:
            return None
        headers = {
            "Authorization": f"Bearer {SETTINGS.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": SETTINGS.openrouter_model,
            "messages": messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=SETTINGS.llm_timeout_seconds)) as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            return None


def normalize_text(value: str) -> str:
    return (value or "").strip().lower()
