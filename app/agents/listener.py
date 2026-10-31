"""Listener: language + intent + slots. Tier 0 rules first; Tier 1 LLM only when unsure (R12)."""
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.config import get_settings
from app.llm.gateway import llm_gateway
from app.nlu.rules import classify


class ListenerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="listener")

    async def understand(self, case_id: str, text: str, db: AsyncSession) -> dict[str, Any]:
        start = time.perf_counter()
        s = get_settings()
        rule = classify(text)
        result: dict[str, Any] = {
            "intent": rule.intent, "confidence": rule.confidence, "slots": dict(rule.slots),
            "language": rule.language, "flags": rule.flags, "tier": 0, "matched": rule.matched,
            "llm_error": None,
        }
        if rule.confidence < s.TIER0_MIN_CONFIDENCE:
            llm = await llm_gateway.classify(db, text)
            if llm.ok and llm.data.get("intent") != "unknown" and llm.data.get("confidence", 0) >= 0.6:
                result.update(
                    intent=llm.data["intent"], confidence=float(llm.data["confidence"]), tier=1,
                    slots={**llm.data.get("slots", {}), **rule.slots},  # rule slots win (deterministic)
                )
            if not llm.ok:
                result["llm_error"] = llm.error
            budget_denied = bool(llm.error and llm.error.startswith("budget"))
            if not budget_denied:
                result["tier"] = 1  # the Tier 1 path was used (call or cache hit)
            result["llm_cached"] = llm.cached
        await self.emit_step(
            case_id=case_id, tool="classify_intent_and_extract_slots",
            input_data={"message": text, "chars": len(text)},
            output_data={k: result[k] for k in ("intent", "confidence", "slots", "language", "tier", "llm_error")},
            confidence=result["confidence"], db=db, latency_ms=(time.perf_counter() - start) * 1000,
        )
        return result


listener_agent = ListenerAgent()
