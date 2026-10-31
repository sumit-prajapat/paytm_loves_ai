"""Diagnostician: deterministic check-up for ONE merchant + learned playbooks."""
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.config import get_settings
from app.db.models import Merchant
from app.services.checkup_service import run_diagnostics
from app.services.playbook_service import playbook_service


class DiagnosticianAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="diagnostician")

    async def diagnose(self, case_id: str, merchant: Merchant, scope: str, db: AsyncSession) -> list[dict[str, Any]]:
        start = time.perf_counter()
        findings = await run_diagnostics(db, merchant, scope)
        await self.emit_step(
            case_id=case_id, tool="run_checkup_diagnostics",
            input_data={"merchant_id": merchant.id, "scope": scope},
            output_data={"findings": [{"code": f["code"], "resolution": f["resolution"],
                                       "evidence": f["evidence"]} for f in findings]},
            confidence=min((f["confidence"] for f in findings), default=1.0), db=db,
            latency_ms=(time.perf_counter() - start) * 1000,
        )
        threshold = get_settings().PLAYBOOK_MATCH_THRESHOLD
        for f in findings:
            if not f["is_issue"] or not f["issue_type"]:
                continue
            pb, score = await playbook_service.match_playbook(db, f["issue_type"], f["conditions"])
            if pb is None:
                continue
            usable = score >= threshold and playbook_service.is_safe(pb)
            await self.emit_step(
                case_id=case_id, tool="match_playbook",
                input_data={"issue_type": f["issue_type"], "conditions": f["conditions"]},
                output_data={"playbook_id": pb.id, "action": pb.action, "score": score, "usable": usable},
                confidence=score, db=db,
            )
            if not usable:
                continue
            f["evidence"].append(f"playbook:{pb.id}")
            f["playbook"] = {"id": pb.id, "action": pb.action, "score": score, "root_cause": pb.root_cause}
            if f["resolution"] == "escalate":
                # A human taught us how to handle this kind of case: resolve with safe guidance.
                f["resolution"] = "playbook"
                f["confidence"] = max(f["confidence"], score)
            await playbook_service.increment_usage(db, pb)
        return findings


diagnostician_agent = DiagnosticianAgent()
