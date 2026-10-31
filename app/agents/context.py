import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.db.models import Customer, Device, Merchant
from app.schemas.envelope import AgentEnvelope
from app.services.settlement_service import settlement_service


class ContextAgent(BaseAgent):
    """Pulls merchant profile, device health, recent settlement, and user context before decision-making."""

    def __init__(self) -> None:
        super().__init__(name="context")

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        user_id = input_data.get("user_id") or input_data.get("merchant_id", "m_ramesh")
        role = input_data.get("role", "merchant")
        language = input_data.get("language", "hi")

        bundle: dict[str, Any] = {"user_id": user_id, "role": role}

        if role == "merchant":
            # 1. Fetch merchant profile
            m_res = await db.execute(select(Merchant).where(Merchant.id == user_id))
            merchant = m_res.scalar_one_or_none()
            if merchant:
                bundle["merchant"] = {
                    "id": merchant.id,
                    "name": merchant.name,
                    "city": merchant.city,
                    "business_type": merchant.business_type,
                    "language": merchant.language,
                    "risk_tier": merchant.risk_tier,
                }
                language = merchant.language

                # 2. Fetch Soundbox device status
                if merchant.device_id:
                    d_res = await db.execute(select(Device).where(Device.id == merchant.device_id))
                    device = d_res.scalar_one_or_none()
                    if device:
                        bundle["device"] = {
                            "id": device.id,
                            "battery": device.battery,
                            "network": device.network,
                            "last_seen": device.last_seen.isoformat(),
                        }

                # 3. Fetch latest settlement
                settlement = await settlement_service.get_settlement(db, merchant.id)
                if settlement:
                    bundle["settlement"] = settlement
        else:
            # Consumer traveller profile
            c_res = await db.execute(select(Customer).where(Customer.id == user_id))
            customer = c_res.scalar_one_or_none()
            if customer:
                bundle["customer"] = {
                    "id": customer.id,
                    "name": customer.name,
                    "home_city": customer.home_city,
                    "language": customer.language,
                    "travel_history": customer.travel_history,
                }
                language = customer.language

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="fetch_context_bundle",
            input_data={"user_id": user_id, "role": role},
            output_data={"keys_fetched": list(bundle.keys())},
            confidence=1.0,
            db=db,
        )

        return AgentEnvelope(
            agent=self.name,
            status="done",
            result=bundle,
            confidence=1.0,
            evidence=["db_profile_fetch", "db_settlement_fetch"],
            next="diagnostician",
            language=language,
            latency_ms=latency_ms,
        )


context_agent = ContextAgent()
