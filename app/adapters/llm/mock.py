"""Deterministic offline stand-in for the LLM (DEMO_MODE / no key / tests).

It never invents numbers: classification reuses the Tier 0 lexicon with relaxed thresholds,
and summaries are assembled from the facts it is given.
"""
import json
import logging
from typing import Any

from app.adapters.llm.base import BaseLLMAdapter
from app.nlu.rules import classify

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MockLLM(BaseLLMAdapter):
    provider = "mock"

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
        context = context or {}
        if task == "classify":
            user_text = context.get("user_text", prompt)
            r = classify(user_text)
            payload = {
                "intent": r.intent if r.confidence >= 0.5 else "unknown",
                "confidence": 0.8 if r.intent != "unknown" and r.confidence >= 0.5 else 0.3,
                "slots": r.slots,
                "language": r.language,
            }
            text = json.dumps(payload, ensure_ascii=False)
        elif task == "summarize":
            facts = context.get("facts", {})
            parts = [f"Issue: {facts.get('issue_type', 'unknown')}"]
            if facts.get("root_cause"):
                parts.append(f"likely cause: {facts['root_cause']}")
            if facts.get("evidence"):
                parts.append("evidence: " + ", ".join(map(str, facts["evidence"][:5])))
            parts.append("suggested next step: " + str(facts.get("suggested_next_step", "review evidence")))
            text = "; ".join(parts) + "."
        else:
            text = ""
        return {
            "text": text,
            "input_tokens": _estimate_tokens(system + prompt),
            "output_tokens": _estimate_tokens(text),
        }
