import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Base,
    Merchant,
)


def test_all_20_tables_registered():
    """Verify that all 20 tables required by Phase 1 are registered in metadata."""
    expected_tables = {
        "merchants",
        "customers",
        "transactions",
        "settlements",
        "settlement_items",
        "refunds",
        "devices",
        "device_events",
        "tickets",
        "disputes",
        "loan_profiles",
        "loan_requests",
        "policies",
        "playbooks",
        "agent_runs",
        "audit_log",
        "flights",
        "airports",
        "festivals",
        "eval_cases",
    }
    actual_tables = set(Base.metadata.tables.keys())
    missing = expected_tables - actual_tables
    assert not missing, f"Missing tables in SQLAlchemy metadata: {missing}"
    assert len(expected_tables) == 20


@pytest.mark.asyncio
async def test_table_insertion_and_query(db_session: AsyncSession):
    """Verify ORM models can be inserted and queried properly."""
    merchant = Merchant(
        id="m_ramesh_test",
        name="Ramesh Kirana Store",
        city="Delhi",
        state="Delhi",
        language="hi",
        business_type="kirana",
        device_id="soundbox_001",
        risk_tier="low",
    )
    db_session.add(merchant)
    await db_session.commit()

    result = await db_session.execute(
        select(Merchant).where(Merchant.id == "m_ramesh_test")
    )
    fetched = result.scalar_one()
    assert fetched.name == "Ramesh Kirana Store"
    assert fetched.language == "hi"
    assert fetched.city == "Delhi"
