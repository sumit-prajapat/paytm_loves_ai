import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notify.in_app import notification_bus
from app.agents.base import BaseAgent
from app.schemas.envelope import AgentEnvelope
from app.services.metrics_service import metrics_service
from app.services.number_validator import number_validator
from app.services.templates import templates


class ActionAgent(BaseAgent):
    """Executes safe actions (explanations, Soundbox chimes, reminders, safe ticketing)."""

    def __init__(self) -> None:
        super().__init__(name="action")

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        action_name = input_data.get("action", "explain")
        context = input_data.get("context", {})
        language = input_data.get("language", "hi")
        is_proactive = bool(input_data.get("is_proactive", False))

        reply_text = ""
        soundbox_text = ""
        action_receipt: dict[str, Any] = {"action": action_name, "status": "executed"}

        # 1. Settlement short explanation
        if "settlement" in action_name or "breakdown" in action_name:
            merchant = context.get("merchant", {})
            name = merchant.get("name", "Ramesh").split()[0]
            settlement = context.get("settlement", {})
            gap = settlement.get("gap", 1800.0)
            refund_adj = settlement.get("refund_adjustment", 1200.0)
            fee = settlement.get("fees", 600.0)
            chargeback_hold = settlement.get("chargeback_hold", 0.0)

            reply_text = templates.settlement_explanation(
                name=name,
                gap=gap,
                refund_adj=refund_adj,
                fee=fee,
                chargeback_hold=chargeback_hold,
                language=language,
            )
            soundbox_text = templates.soundbox_spoken_settlement(
                name=name, gap=gap, refund_adj=refund_adj, fee=fee
            )

            # Enforce Rule R1: Validate numbers
            tool_data = {"gap": gap, "refund": refund_adj, "fee": fee, "hold": chargeback_hold}
            is_valid, unauth = number_validator.validate(reply_text, tool_data)
            if not is_valid:
                reply_text = f"{name} ji, aaj ka settlement ₹{int(gap)} kam aaya hai. Kripya app mein check karein."

            # Broadcast to Soundbox simulator & WhatsApp UI
            await notification_bus.send_notification(
                recipient_id=merchant.get("id", "m_ramesh"),
                channel="soundbox",
                text=soundbox_text,
                language="hi",
            )
            metrics_service.record_auto_resolve(is_proactive=is_proactive)
            action_receipt["zero_ticket"] = True
            action_receipt["reply_text"] = reply_text
            action_receipt["soundbox_text"] = soundbox_text

        # 2. Soundbox offline instruction
        elif "soundbox" in action_name or "charger" in action_name or "battery" in action_name:
            device = context.get("device", {})
            battery = device.get("battery", 12)
            reply_text = templates.soundbox_offline_instruction(battery=battery, language=language)
            merchant = context.get("merchant", {})

            await notification_bus.send_notification(
                recipient_id=merchant.get("id", "m_ramesh"),
                channel="whatsapp_ui",
                text=reply_text,
                language=language,
            )
            metrics_service.record_auto_resolve(is_proactive=is_proactive)
            action_receipt["reply_text"] = reply_text

        # 3. Safe refund status check
        elif "refund" in action_name or "sla" in action_name:
            reply_text = templates.refund_status_explanation(
                amount=1450.0,
                bank_ref="REF9876543210IN",
                status="overdue",
                language=language,
            )
            metrics_service.record_auto_resolve()
            action_receipt["reply_text"] = reply_text

        elif "loan" in action_name or "emi" in action_name or "decline" in action_name:
            action_receipt["reply_text"] = ""

        else:
            reply_text = input_data.get("text", "Aapka anurodh safalta-poorvak process ho gaya hai.")
            action_receipt["reply_text"] = reply_text

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="execute_safe_action",
            input_data={"action": action_name},
            output_data=action_receipt,
            confidence=1.0,
            db=db,
        )

        # After a successful fix on merchant side, check if offer agent should engage (Rule R6)
        next_agent = "offer" if (
            ("loan" in action_name or "emi" in action_name or "decline" in action_name) or
            (context.get("role") == "merchant" and ("settlement" in action_name or "breakdown" in action_name))
        ) else "done"

        return AgentEnvelope(
            agent=self.name,
            status="done",
            result=action_receipt,
            confidence=1.0,
            evidence=["deterministic_action_runner"],
            next=next_agent,
            language=language,
            latency_ms=latency_ms,
        )


action_agent = ActionAgent()
