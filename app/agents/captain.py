import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.action import action_agent
from app.agents.base import BaseAgent
from app.agents.context import context_agent
from app.agents.diagnostician import diagnostician_agent
from app.agents.guardian import guardian_agent
from app.agents.handoff import handoff_agent
from app.agents.listener import listener_agent
from app.agents.offer import offer_agent
from app.agents.planner import planner_agent
from app.agents.ranker import ranker_agent
from app.agents.search import search_agent
from app.schemas.envelope import AgentEnvelope


class CaptainAgent(BaseAgent):
    """The central orchestrator of the Saarthi multi-agent crew.

    Coordinates reactive and proactive pipelines, confidence routing, and safe completion.
    """

    def __init__(self) -> None:
        super().__init__(name="captain")

    async def run_turn(
        self,
        user_id: str,
        message: str | None = None,
        event: dict[str, Any] | None = None,
        role: str = "merchant",
        language: str = "hi",
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        case_id = f"case_{uuid.uuid4().hex[:10]}"
        start_time = time.time()

        # Step 1: Input Analysis (Reactive User Message vs Proactive Event)
        is_proactive = event is not None
        intent = event.get("type", "settlement_short") if is_proactive else "unknown"
        slots = {}

        if not is_proactive and message:
            listener_env = await listener_agent.process(
                case_id=case_id,
                input_data={"message": message, "language": language},
                db=db,
            )
            intent = listener_env.result.get("intent", "smalltalk")
            slots = listener_env.result.get("slots", {})
            language = listener_env.language

            # Immediate refusal of unsafe PIN / OTP
            if listener_env.status == "blocked":
                return {
                    "case_id": case_id,
                    "status": "blocked",
                    "reply_text": listener_env.result.get("text"),
                    "confidence": 1.0,
                    "envelope": listener_env.model_dump(),
                }

        # Step 2: Route to Concierge (Travel) vs Support (Care)
        if "travel" in intent:
            # Travel Concierge multi-agent crew: Planner -> Search -> Ranker -> Handoff
            plan_env = await planner_agent.process(
                case_id=case_id,
                input_data={"slots": slots, "language": language},
                db=db,
            )
            if plan_env.status == "needs_input":
                return {
                    "case_id": case_id,
                    "status": "needs_input",
                    "reply_text": plan_env.result.get("question"),
                    "envelope": plan_env.model_dump(),
                }

            search_env = await search_agent.process(
                case_id=case_id,
                input_data={"roadmap": plan_env.result, "language": language},
                db=db,
            )

            ranker_env = await ranker_agent.process(
                case_id=case_id,
                input_data={"search_result": search_env.result, "language": language},
                db=db,
            )

            rec_data = ranker_env.result
            return {
                "case_id": case_id,
                "status": "ready_for_review_and_pay",
                "reply_text": rec_data.get("reason_text"),
                "roadmap": plan_env.result.get("roadmap_steps"),
                "top_options": rec_data.get("top_options"),
                "recommended": rec_data.get("recommended_pick"),
                "booking_summary": rec_data.get("booking_summary"),
                "envelope": ranker_env.model_dump(),
            }

        # Step 3: Saarthi Care flow: Context -> Diagnostician -> Guardian -> Action / Handoff
        context_env = await context_agent.process(
            case_id=case_id,
            input_data={"user_id": user_id, "role": role, "language": language},
            db=db,
        )

        diag_env = await diagnostician_agent.process(
            case_id=case_id,
            input_data={
                "intent": intent,
                "context": context_env.result,
                "language": language,
            },
            db=db,
        )

        # Guardian Safety Review
        guardian_env = await guardian_agent.process(
            case_id=case_id,
            input_data={
                "action": diag_env.result.get("action"),
                "confidence": diag_env.confidence,
                "financial_impact": diag_env.result.get("financial_impact", 0.0),
                "intent": intent,
                "language": language,
            },
            db=db,
        )

        # Confidence & Policy Routing
        if guardian_env.status == "escalate":
            handoff_env = await handoff_agent.process(
                case_id=case_id,
                input_data={
                    "merchant_id": user_id,
                    "reason": guardian_env.result.get("reason"),
                    "evidence": diag_env.evidence,
                    "language": language,
                    "root_cause": diag_env.result.get("root_cause"),
                },
                db=db,
            )
            return {
                "case_id": case_id,
                "status": "escalated",
                "reply_text": handoff_env.result.get("merchant_facing_message"),
                "escalation_package": handoff_env.result,
                "envelope": handoff_env.model_dump(),
            }

        if guardian_env.status == "needs_input":
            return {
                "case_id": case_id,
                "status": "needs_input",
                "reply_text": "Kripya vistaar se batayein, aapko settlement, soundbox ya kisi transaction me sahayata chahiye?",
                "envelope": guardian_env.model_dump(),
            }

        # Safe Action Execution
        action_env = await action_agent.process(
            case_id=case_id,
            input_data={
                "action": diag_env.result.get("action"),
                "context": context_env.result,
                "language": language,
                "is_proactive": is_proactive,
            },
            db=db,
        )

        reply_text = action_env.result.get("reply_text", "Aapki samasya suljha di gayi hai.")

        # Optional Consent-First Loan Offer check
        if action_env.next == "offer":
            offer_intent = intent if intent in ["loan_emi_query", "loan_interest", "decline_offer"] else "check_offer"
            offer_env = await offer_agent.process(
                case_id=case_id,
                input_data={
                    "merchant_id": user_id,
                    "intent": offer_intent,
                    "amount": slots.get("amount", 50000.0),
                    "language": language,
                },
                db=db,
            )
            if offer_env.result.get("text"):
                if reply_text:
                    reply_text = f"{reply_text}\n\n{offer_env.result.get('text')}"
                else:
                    reply_text = offer_env.result.get("text")

        total_latency = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="finalize_response",
            input_data={"intent": intent, "is_proactive": is_proactive},
            output_data={"reply_text": reply_text, "latency_ms": total_latency},
            confidence=diag_env.confidence,
            db=db,
        )

        return {
            "case_id": case_id,
            "status": "resolved",
            "reply_text": reply_text,
            "zero_ticket": True,
            "confidence": diag_env.confidence,
            "evidence": diag_env.evidence,
            "envelope": action_env.model_dump(),
        }

    async def process(self, case_id: str, input_data: dict[str, Any], db: AsyncSession) -> AgentEnvelope:
        res = await self.run_turn(
            user_id=input_data.get("user_id", "m_ramesh"),
            message=input_data.get("message"),
            event=input_data.get("event"),
            role=input_data.get("role", "merchant"),
            language=input_data.get("language", "hi"),
            db=db,
        )
        return AgentEnvelope(
            agent=self.name,
            status="done",
            result=res,
            confidence=1.0,
            evidence=["multi_agent_captain_orchestrator"],
            next="done",
            language=input_data.get("language", "hi"),
        )


captain_agent = CaptainAgent()
