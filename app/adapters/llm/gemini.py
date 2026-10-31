"""Google Gemini adapter. Key goes in a header (never the URL, which may be logged)."""
import logging
from typing import Any

import httpx

from app.adapters.llm.base import BaseLLMAdapter, LLMUnavailable
from app.config import get_settings

logger = logging.getLogger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLM(BaseLLMAdapter):
    provider = "gemini"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        tier: int,
        json_mode: bool,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        s = get_settings()
        model = s.GEMINI_MODEL_TIER2 if tier >= 2 else s.GEMINI_MODEL_TIER1
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 512},
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        try:
            async with httpx.AsyncClient(timeout=s.LLM_TIMEOUT_SECONDS) as client:
                res = await client.post(
                    f"{_BASE}/{model}:generateContent",
                    json=payload,
                    headers={"x-goog-api-key": self._api_key},
                )
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"gemini network error: {type(exc).__name__}") from exc
        if res.status_code != 200:
            raise LLMUnavailable(f"gemini HTTP {res.status_code} for model {model}")
        try:
            data = res.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable("gemini malformed response") from exc
        return {
            "text": text,
            "input_tokens": int(usage.get("promptTokenCount", len(system + prompt) // 4)),
            "output_tokens": int(usage.get("candidatesTokenCount", len(text) // 4)),
        }
