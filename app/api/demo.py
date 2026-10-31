"""Demo support (DEMO_MODE only, ops/admin).

- POST /demo/scenario/{name}: ONLY mutates simulated data (creates the anomaly). Nothing runs.
- POST /demo/trigger/{name}: simulates the USER pressing the button / speaking, by calling the
  exact same functions the production endpoints use, as the hero user.
- POST /demo/reset: restores hero data.
"""
import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat import ChatRequest, execute_chat
from app.api.checkups import CheckupRequest, execute_checkup
from app.api.soundbox import SoundboxAsk, execute_soundbox_ask
from app.config import get_settings
from app.core.cache import cache
from app.core.deps import require_roles
from app.db.heroes import reset_hero_data, seed_ramesh_settlement
from app.db.models import (
    Checkup,
    Device,
    Dispute,
    Festival,
    Merchant,
    Refund,
    Transaction,
    TravelBooking,
    User,
)
from app.db.session import get_db
from app.services.audit import record_audit_log
from app.services.pulse_service import booking_status, build_advice

router = APIRouter(prefix="/demo", tags=["Demo (DEMO_MODE only)"])

ScenarioName = Literal["settlement_short", "soundbox_offline", "low_battery", "refund_overdue", "payment_failed",
                       "chargeback", "festival_low_battery", "flight_delay", "travel_search"]

SCENARIO_SUBJECT = {
    "settlement_short": "usr_ramesh", "soundbox_offline": "usr_ramesh", "low_battery": "usr_ramesh",
    "refund_overdue": "usr_sunita", "payment_failed": "usr_ramesh", "chargeback": "usr_gupta",
    "festival_low_battery": "usr_ramesh", "flight_delay": "usr_arjun", "travel_search": "usr_arjun",
}


def _require_demo() -> None:
    if not get_settings().DEMO_MODE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


async def _invalidate_checkups(db: AsyncSession, merchant_id: str) -> None:
    """New data arrived: cached check-up results for this merchant are stale."""
    await db.execute(update(Checkup).where(Checkup.merchant_id == merchant_id).values(cache_valid=False))
    cache.clear()


async def _mutate(name: str, db: AsyncSession) -> dict[str, Any]:
    now = _now()
    if name == "settlement_short":
        await seed_ramesh_settlement(db, (1200.0, 600.0))
        await _invalidate_checkups(db, "m_ramesh")
        return {"merchant_id": "m_ramesh", "changed": "settlement set_ramesh_today gap 1800 (1200 refund + 600 fee)"}
    if name == "soundbox_offline":
        await db.execute(update(Device).where(Device.id == "soundbox_ramesh_01")
                         .values(battery=64, last_seen=now - datetime.timedelta(minutes=180)))
        await _invalidate_checkups(db, "m_ramesh")
        return {"merchant_id": "m_ramesh", "changed": "soundbox_ramesh_01 last seen 180 minutes ago"}
    if name in ("low_battery", "festival_low_battery"):
        await db.execute(update(Device).where(Device.id == "soundbox_ramesh_01").values(battery=12, last_seen=now))
        changed = "soundbox_ramesh_01 battery 12%"
        if name == "festival_low_battery":
            soon = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
            exists = (await db.execute(select(Festival).where(Festival.name == "Diwali (demo)"))).scalars().first()
            if exists is None:
                db.add(Festival(date=soon, name="Diwali (demo)", region="National"))
            changed += f"; festival 'Diwali (demo)' on {soon}"
        await _invalidate_checkups(db, "m_ramesh")
        return {"merchant_id": "m_ramesh", "changed": changed}
    if name == "refund_overdue":
        await db.execute(update(Refund).where(Refund.id == "ref_sunita_overdue_01")
                         .values(status="overdue", expected_by=now - datetime.timedelta(days=2)))
        await _invalidate_checkups(db, "m_sunita")
        return {"merchant_id": "m_sunita", "changed": "refund ref_sunita_overdue_01 overdue"}
    if name == "payment_failed":
        await db.execute(delete(Refund).where(Refund.txn_id == "txn_demo_failed_01"))
        await db.merge(Transaction(txn_id="txn_demo_failed_01", merchant_id="m_ramesh", amount=850.0, status="failed",
                                   mode="upi", failure_reason="bank_timeout", ts=now - datetime.timedelta(hours=2)))
        db.add(Refund(id="ref_demo_failed_01", txn_id="txn_demo_failed_01", status="pending", initiated_at=now,
                      expected_by=now + datetime.timedelta(days=5), bank_ref="REF5550001112IN"))
        await _invalidate_checkups(db, "m_ramesh")
        return {"merchant_id": "m_ramesh", "changed": "failed payment txn_demo_failed_01 with pending refund"}
    if name == "chargeback":
        await db.execute(update(Dispute).where(Dispute.id == "disp_case_7701")
                         .values(status="open", deadline=now + datetime.timedelta(days=4)))
        await _invalidate_checkups(db, "m_disputed")
        return {"merchant_id": "m_disputed", "changed": "dispute disp_case_7701 open"}
    if name == "flight_delay":
        await db.execute(update(TravelBooking).where(TravelBooking.booking_ref == "BK-ARJ-1001")
                         .values(status="delayed", delay_minutes=45))
        return {"customer_id": "c_arjun", "changed": "booking BK-ARJ-1001 delayed 45 minutes"}
    if name == "travel_search":
        return {"customer_id": "c_arjun", "changed": "nothing (inventory is already seeded)"}
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown scenario")


@router.post("/scenario/{name}")
async def setup_scenario(name: ScenarioName, current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                         db: AsyncSession = Depends(get_db)):
    """Set up the world. Does NOT start any processing (R11)."""
    _require_demo()
    changed = await _mutate(name, db)
    await record_audit_log(db, case_id=f"demo_{name}", actor=current_user.username, action="DEMO_SCENARIO_SETUP",
                           detail=changed)
    await db.commit()
    return {"scenario": name, "mutated": changed, "processing_started": False,
            "next": f"POST /api/v1/demo/trigger/{name}"}


class DemoTrigger(BaseModel):
    channel: Literal["app", "chat", "voice", "soundbox"] = "app"
    language: str | None = None
    message: str | None = None


DEFAULT_MESSAGES = {
    "travel_search": "Delhi se Mumbai kal shaam ka flight, sasta aur jaldi",
}
SCENARIO_SCOPE = {"settlement_short": "settlement", "soundbox_offline": "device", "low_battery": "device",
                  "refund_overdue": "refunds", "payment_failed": "payments", "chargeback": "payments"}


@router.post("/trigger/{name}")
async def trigger_scenario(name: ScenarioName, body: DemoTrigger | None = None,
                           current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                           db: AsyncSession = Depends(get_db)):
    """Simulate the hero USER pressing the button / speaking. Same code path as production."""
    _require_demo()
    body = body or DemoTrigger()
    hero = (await db.execute(select(User).where(User.id == SCENARIO_SUBJECT[name]))).scalar_one_or_none()
    if hero is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hero user missing; run /demo/reset")
    await record_audit_log(db, case_id=f"demo_{name}", actor=current_user.username, action="DEMO_TRIGGER",
                           detail={"as_user": hero.username, "channel": body.channel})
    if name in SCENARIO_SCOPE:
        if body.channel == "soundbox":
            device = (await db.execute(select(Device).where(Device.merchant_id == hero.merchant_id))).scalars().first()
            return await execute_soundbox_ask(hero, device.id, SoundboxAsk(button=SCENARIO_SCOPE[name],
                                                                           language=body.language), db)
        if body.message:
            return await execute_chat(hero, ChatRequest(message=body.message, language=body.language), db,
                                      channel=body.channel if body.channel in ("chat", "voice") else "chat")
        return await execute_checkup(hero, CheckupRequest(scope=SCENARIO_SCOPE[name], channel=body.channel,
                                                          language=body.language), db)
    if name == "festival_low_battery":
        m = (await db.execute(select(Merchant).where(Merchant.id == hero.merchant_id))).scalar_one()
        a = await build_advice(db, m, body.language or m.language)
        await db.commit()
        return {"status": "resolved", "reply_text": a["text"], "facts": a["facts"], "tier": 0}
    if name == "flight_delay":
        st = await booking_status(db, hero.customer_id, "BK-ARJ-1001", body.language or "en")
        await db.commit()
        return {"status": "resolved", "reply_text": st["text"], "booking": st["booking"], "tier": 0}
    return await execute_chat(hero, ChatRequest(message=body.message or DEFAULT_MESSAGES[name],
                                                language=body.language), db)


@router.post("/reset")
async def reset(current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                db: AsyncSession = Depends(get_db)):
    _require_demo()
    counts = await reset_hero_data(db)
    await record_audit_log(db, case_id="demo_reset", actor=current_user.username, action="DEMO_RESET",
                           detail=counts)
    await db.commit()
    return {"status": "reset", "cleared": counts}
