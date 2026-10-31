"""Hero personas (SIMULATED DATA). Idempotent: safe to run on every seed and on /demo/reset.

Ramesh (m_ramesh): Hindi kirana owner, Soundbox, settlement short by 1800 = 1200 refund + 600 fees.
Sunita (m_sunita): Marathi tailor with an overdue refund.
Gupta Electronics (m_disputed): open chargeback dispute (risky -> human).
Arjun (c_arjun) and Meena Aunty (c_meena): travellers with simulated bookings.
"""
from __future__ import annotations

import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.security import hash_password
from app.db.models import (
    Checkup,
    ConversationState,
    Customer,
    Device,
    Dispute,
    LoanProfile,
    LoanRequest,
    Merchant,
    OfferConsent,
    Playbook,
    Refund,
    Settlement,
    SettlementItem,
    Ticket,
    Transaction,
    TravelBooking,
    UsageEvent,
    User,
)

HERO_MERCHANTS = ("m_ramesh", "m_sunita", "m_disputed")
HERO_CUSTOMERS = ("c_arjun", "c_meena")
DEMO_PASSWORD = "DemoPass@123"  # simulated demo accounts only (DEMO_MODE)
ADMIN_DEMO_PASSWORD = "AdminPass@123"

SEED_PLAYBOOKS = [
    Playbook(id="pb_settlement_reconciled", issue_type="settlement_short", root_cause="refund_adjustment_and_fee",
             action="explain_breakdown", conditions_json={"settlement_gap_matches_items": True},
             created_from_case="historical_resolution", times_used=14),
    Playbook(id="pb_soundbox_low_battery", issue_type="soundbox_offline", root_cause="battery_depleted",
             action="guide_charger", conditions_json={"battery_below_pct": 20},
             created_from_case="historical_resolution", times_used=8),
]


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


async def seed_ramesh_settlement(db: AsyncSession, gap_items: tuple[float, float] = (1200.0, 600.0)) -> None:
    today = datetime.date.today().isoformat()
    refund_adj, fee = gap_items
    gap = refund_adj + fee
    await db.execute(delete(SettlementItem).where(SettlementItem.settlement_id == "set_ramesh_today"))
    await db.merge(Settlement(id="set_ramesh_today", merchant_id="m_ramesh", date=today,
                              expected=24500.0, actual=24500.0 - gap, gap=gap))
    if refund_adj:
        db.add(SettlementItem(settlement_id="set_ramesh_today", type="refund_adjustment", amount=refund_adj))
    if fee:
        db.add(SettlementItem(settlement_id="set_ramesh_today", type="fee", amount=fee))


async def seed_heroes(db: AsyncSession) -> None:
    now = _now()
    for pb in SEED_PLAYBOOKS:
        await db.merge(Playbook(**{c.name: getattr(pb, c.name) for c in Playbook.__table__.columns
                                   if c.name != "created_at"}))

    # Ramesh
    await db.merge(Merchant(id="m_ramesh", name="Ramesh Kirana Store", city="Delhi", state="Delhi", language="hi",
                            business_type="kirana", device_id="soundbox_ramesh_01",
                            joined_on=now - datetime.timedelta(days=365), risk_tier="low", kyc_status="verified"))
    await db.merge(Device(id="soundbox_ramesh_01", merchant_id="m_ramesh", model="Soundbox v3 4G", battery=12,
                          network="4G Airtel", last_seen=now - datetime.timedelta(minutes=15), firmware="v2.4.1"))
    await seed_ramesh_settlement(db)
    await db.merge(LoanProfile(merchant_id="m_ramesh", monthly_volume=185000.0, vintage_months=14, score=780,
                               eligible_limit=100000.0))

    # Sunita: failed payment 9 days ago, refund overdue
    await db.merge(Merchant(id="m_sunita", name="Sunita Tailors", city="Mumbai", state="Maharashtra", language="mr",
                            business_type="tailor", device_id="soundbox_sunita_01",
                            joined_on=now - datetime.timedelta(days=200), risk_tier="low", kyc_status="verified"))
    await db.merge(Device(id="soundbox_sunita_01", merchant_id="m_sunita", model="Soundbox v3", battery=85,
                          network="4G Jio", last_seen=now - datetime.timedelta(minutes=2), firmware="v2.4.1"))
    await db.merge(Transaction(txn_id="txn_sunita_refund_01", merchant_id="m_sunita", amount=1450.0, status="failed",
                               mode="upi", failure_reason="bank_timeout", ts=now - datetime.timedelta(days=9)))
    await db.merge(Refund(id="ref_sunita_overdue_01", txn_id="txn_sunita_refund_01", status="overdue",
                          initiated_at=now - datetime.timedelta(days=9), expected_by=now - datetime.timedelta(days=2),
                          bank_ref="REF9876543210IN"))

    # Gupta Electronics: open chargeback
    await db.merge(Merchant(id="m_disputed", name="Gupta Electronics", city="Lucknow", state="Uttar Pradesh",
                            language="hi", business_type="electronics", device_id="soundbox_gupta_01",
                            joined_on=now - datetime.timedelta(days=120), risk_tier="medium", kyc_status="verified"))
    await db.merge(Device(id="soundbox_gupta_01", merchant_id="m_disputed", model="Soundbox v3", battery=64,
                          network="4G Vi", last_seen=now - datetime.timedelta(minutes=5), firmware="v2.4.1"))
    await db.merge(Transaction(txn_id="txn_chargeback_99", merchant_id="m_disputed", amount=6500.0, status="success",
                               mode="card", ts=now - datetime.timedelta(days=3)))
    await db.merge(Dispute(id="disp_case_7701", txn_id="txn_chargeback_99", amount=6500.0,
                           reason="Cardholder claims card was stolen and unauthorized transaction occurred at store",
                           status="open", deadline=now + datetime.timedelta(days=4),
                           evidence_json={"invoice_required": True, "cctv_allowed": True}))

    # Travellers
    await db.merge(Customer(id="c_arjun", name="Arjun Sharma", home_city="Delhi", language="en",
                            travel_history=[{"from": "DEL", "to": "BOM", "airline": "IndiGo"}]))
    await db.merge(Customer(id="c_meena", name="Meena Devi (Meena Aunty)", home_city="Delhi", language="hi",
                            travel_history=[{"from": "DEL", "to": "VNS", "airline": "Air India"}]))
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    in_three = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    await db.merge(TravelBooking(booking_ref="BK-ARJ-1001", customer_id="c_arjun", flight_no="AI-865",
                                 airline="Air India", from_iata="DEL", to_iata="BOM", date=tomorrow, dep_time="19:00",
                                 status="on_time", delay_minutes=0, terminal="T3", gate="32B"))
    await db.merge(TravelBooking(booking_ref="BK-MEE-2001", customer_id="c_meena", flight_no="6E-2135",
                                 airline="IndiGo", from_iata="DEL", to_iata="VNS", date=in_three, dep_time="10:15",
                                 status="on_time", delay_minutes=0, terminal="T1", gate="12"))

    # Demo users (simulated credentials, DEMO_MODE only)
    users = [
        ("usr_ramesh", "merchant_ramesh", "merchant", "m_ramesh", None, DEMO_PASSWORD),
        ("usr_sunita", "merchant_sunita", "merchant", "m_sunita", None, DEMO_PASSWORD),
        ("usr_gupta", "merchant_gupta", "merchant", "m_disputed", None, DEMO_PASSWORD),
        ("usr_arjun", "traveller_arjun", "traveller", None, "c_arjun", DEMO_PASSWORD),
        ("usr_meena", "traveller_meena", "traveller", None, "c_meena", DEMO_PASSWORD),
        ("usr_ops", "ops_agent_1", "ops_agent", None, None, DEMO_PASSWORD),
        ("usr_admin", "admin_user", "admin", None, None, ADMIN_DEMO_PASSWORD),
    ]
    for uid, username, role, mid, cid, pwd in users:
        existing = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
        if existing is None:
            db.add(User(id=uid, username=username, password_hash=hash_password(pwd), role=role,
                        merchant_id=mid, customer_id=cid, is_active=True))
    await db.flush()


async def reset_hero_data(db: AsyncSession) -> dict:
    """Restore hero data to the seeded state and clear their interaction history (demo only)."""
    subjects = HERO_MERCHANTS + HERO_CUSTOMERS
    counts = {}
    for model, col in ((Checkup, Checkup.merchant_id), (Ticket, Ticket.merchant_id),
                       (LoanRequest, LoanRequest.merchant_id), (OfferConsent, OfferConsent.merchant_id),
                       (ConversationState, ConversationState.subject_id), (UsageEvent, UsageEvent.user_id)):
        res = await db.execute(delete(model).where(col.in_(subjects)))
        counts[model.__tablename__] = res.rowcount
    learned = await db.execute(delete(Playbook).where(Playbook.created_from_case != "historical_resolution"))
    counts["learned_playbooks"] = learned.rowcount
    await db.execute(delete(Transaction).where(Transaction.merchant_id.in_(HERO_MERCHANTS),
                                               Transaction.txn_id.like("txn_demo_%")))
    await seed_heroes(db)
    cache.clear()
    return counts
