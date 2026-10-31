import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import AuditLog, User


@pytest.mark.asyncio
async def test_control_state_and_kill_switch_toggle(
    client: AsyncClient, db_session: AsyncSession
):
    # Ensure an admin user exists for RBAC check
    admin_user = User(
        id="usr_admin_test",
        username="admin_test",
        password_hash=hash_password("AdminPass@123"),
        role="admin",
        is_active=True,
    )
    await db_session.merge(admin_user)
    await db_session.commit()

    admin_token = create_access_token({
        "sub": "usr_admin_test",
        "username": "admin_test",
        "role": "admin",
    })
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get initial control state
    res = await client.get("/control/state", headers=auth_headers)
    assert res.status_code == 200
    state = res.json()
    assert state["kill_switch_active"] is False
    assert state["financial_impact_threshold_inr"] == 5000.0

    # 2. Engage kill switch
    engage_payload = {
        "active": True,
        "reason": "Emergency halt triggered by safety supervisor",
        "actor": "admin_test",
    }
    toggle_res = await client.post("/control/kill-switch", json=engage_payload, headers=auth_headers)
    assert toggle_res.status_code == 200
    updated_state = toggle_res.json()
    assert updated_state["kill_switch_active"] is True
    assert updated_state["reason"] == "Emergency halt triggered by safety supervisor"
    assert updated_state["updated_by"] == "admin_test"

    # 3. Verify audit log entry was created
    audit_res = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "KILL_SWITCH_ENGAGED")
    )
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.actor == "admin_test"
    assert audit_entry.case_id == "system_control"

    # 4. Disengage kill switch to leave clean state
    disengage_payload = {
        "active": False,
        "reason": "Resuming normal operations",
        "actor": "admin_test",
    }
    resume_res = await client.post("/control/kill-switch", json=disengage_payload, headers=auth_headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["kill_switch_active"] is False
