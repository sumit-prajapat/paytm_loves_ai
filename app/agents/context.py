"""Context: loads ONLY the triggering subject's profile (merchant or traveller)."""
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.db.models import Customer, Merchant


class ContextAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="context")

    async def load(self, case_id: str, subject_type: str, subject_id: str, db: AsyncSession) -> dict[str, Any]:
        start = time.perf_counter()
        bundle: dict[str, Any] = {"subject_type": subject_type, "subject_id": subject_id}
        if subject_type == "merchant":
            m = (await db.execute(select(Merchant).where(Merchant.id == subject_id))).scalar_one_or_none()
            if m:
                bundle.update(merchant=m, name=m.name.split()[0], language=m.language)
        else:
            c = (await db.execute(select(Customer).where(Customer.id == subject_id))).scalar_one_or_none()
            if c:
                bundle.update(customer=c, name=c.name.split()[0], language=c.language)
        await self.emit_step(
            case_id=case_id, tool="fetch_context_bundle",
            input_data={"subject_type": subject_type, "subject_id": subject_id},
            output_data={"found": ("merchant" in bundle) or ("customer" in bundle),
                         "profile_language": bundle.get("language")},
            confidence=1.0, db=db, latency_ms=(time.perf_counter() - start) * 1000,
        )
        return bundle


context_agent = ContextAgent()
