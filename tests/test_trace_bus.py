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
        tool="get_settlement_breakdown",
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
    assert saved_run.tool == "get_settlement_breakdown"
    assert saved_run.output == {"refund_adjustment": 1200.0, "fees": 600.0}
    assert saved_run.confidence == 0.98


def test_websocket_trace_connection():
    from app.core.security import create_access_token
    admin_token = create_access_token({"sub": "usr_admin", "username": "admin_user", "role": "admin"})

    with TestClient(app) as test_client:
        with test_client.websocket_connect(f"/ws/trace?token={admin_token}") as websocket:
            websocket.send_text("ping")
            response = websocket.receive_text()
            assert response == "pong"
