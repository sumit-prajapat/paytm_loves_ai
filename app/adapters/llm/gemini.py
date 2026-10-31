import json
import logging
from typing import Any

import httpx

from app.adapters.llm.base import BaseLLMAdapter
from app.adapters.llm.mock import MockLLM

logger = logging.getLogger(__name__)


class GeminiLLM(BaseLLMAdapter):
    """Google Gemini LLM adapter with fallback to MockLLM on network/api error."""

    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash-lite") -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.mock_fallback = MockLLM()
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    async def generate_response(
        self,
        prompt: str,
        system_instruction: str | None = None,
        context: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        try:
            payload: dict[str, Any] = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            }
            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(self.endpoint, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidate_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(candidate_text)
                else:
                    logger.warning(f"Gemini API returned {res.status_code}. FALLBACK USED")
                    return await self.mock_fallback.generate_response(prompt, system_instruction, context, tools)
        except Exception as e:
            logger.warning(f"Gemini API invocation error: {e}. FALLBACK USED")
            return await self.mock_fallback.generate_response(prompt, system_instruction, context, tools)
