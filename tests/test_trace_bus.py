import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient

from app.db.models import AgentRun
from app.main import app
from app.trace.bus import trace_bus


@pytest.mark.asyncio
async def test_trace_bus_publish_step(db_session: AsyncSession):
    run_id = await trace_bus.publish_step(
        case_id="case_settlement_001",
        agent="diagnostician",
        tool="run_checkup_diagnostics",
        input_data={"merchant_id": "m_ramesh", "gap": 1800.0},
        output_data={"refund_adjustment": 1200.0, "fees": 600.0},
        confidence=0.98,
        db=db_session,
    )

    assert run_id.startswith("run_")

    result = await db_session.execute(
        select(AgentRun).where(AgentRun.run_id == run_id)
    )
    saved_run = result.scalar_one_or_none()
    assert saved_run is not None
    assert saved_run.case_id == "case_settlement_001"
    assert saved_run.agent == "diagnostician"
    assert saved_run.tool == "run_checkup_diagnostics"
    assert saved_run.output == {"refund_adjustment": 1200.0, "fees": 600.0}
    assert saved_run.confidence == 0.98


@pytest.mark.asyncio
async def test_trace_bus_rejects_denied_tools_at_runtime(db_session: AsyncSession):
    """R3 is enforced in code: a financial tool can never be executed by any agent."""
    from app.core.security import ToolNotAllowed
    for tool in ("confirm_payment", "approve_loan", "issue_refund", "confirm_booking"):
        with pytest.raises(ToolNotAllowed):
            await trace_bus.publish_step(case_id="c1", agent="action", tool=tool, db=db_session)
    with pytest.raises(ToolNotAllowed):  # tools outside an agent's allow-list are denied too
        await trace_bus.publish_step(case_id="c1", agent="listener", tool="render_explanation", db=db_session)


@pytest.mark.asyncio
async def test_trace_bus_masks_pii_before_persisting(db_session: AsyncSession):
    run_id = await trace_bus.publish_step(case_id="c2", agent="listener", tool="classify_intent_and_extract_slots",
                                          input_data={"message": "call me on 9876543210"}, db=db_session)
    row = (await db_session.execute(select(AgentRun).where(AgentRun.run_id == run_id))).scalar_one()
    assert "9876543210" not in str(row.input)


def test_websocket_trace_connection():
    from app.core.security import create_access_token
    admin_token = create_access_token({"sub": "usr_admin", "username": "admin_user", "role": "admin"})

    with TestClient(app) as test_client:
        with test_client.websocket_connect(f"/ws/trace?token={admin_token}") as websocket:
            websocket.send_text("ping")
            response = websocket.receive_text()
            assert response == "pong"
