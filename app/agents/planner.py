import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.schemas.envelope import AgentEnvelope


class PlannerAgent(BaseAgent):
    """Produces the visible multi-agent Roadmap card and identifies missing slots one at a time."""

    def __init__(self) -> None:
        super().__init__(name="planner")

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        slots = input_data.get("slots", {})
        language = input_data.get("language", "hi")

        origin = slots.get("origin", "DEL")
        destination = slots.get("destination", "BOM")
        date_str = slots.get("date", "tomorrow")
        window = slots.get("window", "evening")
        preference = slots.get("preference", "sasta aur jaldi")

        # Check for missing critical slots (Ask ONE at a time)
        if not destination:
            msg = "Aapko kahan jaana hai? (Destination city)" if language in ["hi", "hinglish"] else "Where would you like to travel to?"
            return AgentEnvelope(
                agent=self.name,
                status="needs_input",
                result={"missing_slot": "destination", "question": msg},
                confidence=0.75,
                evidence=["slot_checker"],
                next="listener",
                language=language,
                latency_ms=(time.time() - start_time) * 1000.0,
            )

        # Build transparent Roadmap
        roadmap = [
            f"Step 1: Check direct non-stop flights from {origin} to {destination} for {date_str}",
            f"Step 2: Filter by preferred '{window}' departure window",
            "Step 3: Check 1-stop options if price gap exceeds 25%",
            "Step 4: Check flexible dates (+1 day) for major fare drops",
            f"Step 5: Score options deterministically (Price weight shifted for '{preference}')",
            "Step 6: Prepare Top 3 labeled recommendations and hand over Review & Pay link to human",
        ]

        roadmap_card = {
            "origin": origin,
            "destination": destination,
            "date": date_str,
            "window": window,
            "preference": preference,
            "roadmap_steps": roadmap,
        }

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="generate_travel_roadmap",
            input_data={"slots": slots},
            output_data={"steps_count": len(roadmap), "roadmap": roadmap},
            confidence=0.98,
            db=db,
        )

        return AgentEnvelope(
            agent=self.name,
            status="done",
            result=roadmap_card,
            confidence=0.98,
            evidence=["roadmap_planner"],
            next="search",
            language=language,
            latency_ms=latency_ms,
        )


planner_agent = PlannerAgent()
