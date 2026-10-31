"""R11: nothing runs for a user until that user (or an authorised ops agent) triggers it."""
import ast
import asyncio
import pathlib
import re

import pytest
from sqlalchemy import func, select

from app.db.models import AgentRun, Checkup, UsageEvent
from app.llm.gateway import llm_gateway
from tests.conftest import SQL_LOG, auth

APP_DIR = pathlib.Path(__file__).resolve().parents[1] / "app"
USER_TABLES = ("merchants", "customers", "transactions", "settlements", "settlement_items", "refunds", "devices",
               "device_events", "tickets", "disputes", "loan_profiles", "loan_requests", "checkups",
               "travel_bookings", "offer_consents", "conversation_states", "usage_events", "users")


def _py_files():
    return [p for p in APP_DIR.rglob("*.py") if "__pycache__" not in p.parts]


def test_no_scheduler_jobs_outside_housekeeping_module():
    offenders = []
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        if re.search(r"\.add_job\(|BackgroundScheduler|AsyncIOScheduler\(", text) and path.name != "housekeeping.py":
            offenders.append(str(path))
    assert offenders == [], f"Schedulers must live only in app/ops/housekeeping.py: {offenders}"


def test_housekeeping_module_never_touches_user_data():
    src = (APP_DIR / "ops" / "housekeeping.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    forbidden = {m for m in imported if m.startswith(("app.db", "sqlalchemy", "app.services", "app.agents"))}
    assert forbidden == set(), f"housekeeping imports data-layer modules: {forbidden}"
    for table in USER_TABLES:
        assert table not in src


def test_no_proactive_entry_points_left():
    removed = ["app/events", "app/services/anomaly_service.py", "app/api/events.py", "app/api/notifications.py"]
    for rel in removed:
        assert not (APP_DIR.parent / rel).exists(), f"{rel} should be deleted (R11)"
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        assert "while True" not in text or path.name == "ws.py", f"background loop in {path}"
        assert "asyncio.sleep(" not in text, f"polling sleep in {path}"
        assert "is_proactive" not in text, f"proactive flag in {path}"


def test_routes_have_no_injection_or_push_endpoints():
    from app.main import app
    paths = set(app.openapi()["paths"])
    assert "/api/v1/events/inject" not in paths and "/events/inject" not in paths
    assert "/api/v1/notifications" not in paths and "/notifications" not in paths


async def test_runtime_scheduler_registers_only_housekeeping_jobs(monkeypatch):
    from app.config import get_settings
    from app.ops import housekeeping
    monkeypatch.setattr(get_settings(), "HOUSEKEEPING_ENABLED", True)
    housekeeping.start_housekeeping()
    try:
        job_ids = {j.id for j in housekeeping.scheduler.get_jobs()}
        assert job_ids and job_ids <= housekeeping.HOUSEKEEPING_JOB_IDS
        for job in housekeeping.scheduler.get_jobs():
            assert job.func.__module__ == "app.ops.housekeeping"
    finally:
        housekeeping.stop_housekeeping()


async def test_zero_requests_means_zero_llm_calls_and_no_user_reads(seeded):
    """Idle system: run every housekeeping job and wait; no LLM call, no SQL at all."""
    from app.ops import housekeeping
    before_runs = (await seeded.execute(select(func.count(AgentRun.run_id)))).scalar_one()
    SQL_LOG.clear()
    for func_, _ in housekeeping.JOBS.values():
        func_()
    await asyncio.sleep(0.5)
    assert SQL_LOG == [], f"background SQL with zero user requests: {SQL_LOG[:3]}"
    assert llm_gateway.stats.get("calls", 0) == 0
    after_runs = (await seeded.execute(select(func.count(AgentRun.run_id)))).scalar_one()
    assert after_runs == before_runs


@pytest.mark.usefixtures("seeded")
async def test_demo_scenario_mutates_only_trigger_runs_processing(client, db_session):
    setup = (await client.post("/api/v1/demo/scenario/settlement_short", headers=auth("ops"))).json()
    assert setup["processing_started"] is False
    assert (await db_session.execute(select(func.count(Checkup.id)))).scalar_one() == 0
    assert (await db_session.execute(select(func.count(AgentRun.run_id)))).scalar_one() == 0
    assert (await db_session.execute(select(func.count(UsageEvent.id)))).scalar_one() == 0
    assert llm_gateway.stats.get("calls", 0) == 0

    run = (await client.post("/api/v1/demo/trigger/settlement_short", headers=auth("ops"), json={})).json()
    assert run["status"] == "resolved" and "1,800" in run["reply_text"]
    rows = (await db_session.execute(select(Checkup))).scalars().all()
    assert len(rows) == 1 and rows[0].merchant_id == "m_ramesh" and rows[0].triggered_by == "usr_ramesh"


@pytest.mark.usefixtures("seeded")
async def test_checkup_touches_only_the_triggering_merchant(client):
    SQL_LOG.clear()
    r = await client.post("/api/v1/checkups", headers=auth("ramesh"), json={"scope": "all"})
    assert r.status_code == 200
    reads = [p for sql, p in SQL_LOG if sql.lstrip().startswith("select") and
             any(f"from {t}" in sql for t in ("settlements", "devices", "refunds", "disputes"))]
    assert reads, "expected per-merchant diagnostic reads"
    assert all("m_ramesh" in p or "soundbox_ramesh_01" in p for p in reads), reads
    # no query scans merchants without a filter
    assert not [sql for sql, _ in SQL_LOG if "from merchants" in sql and "where" not in sql]


async def test_llm_gateway_refuses_calls_outside_a_user_turn(db_session):
    with pytest.raises(RuntimeError, match="outside a user-triggered turn"):
        await llm_gateway.summarize(db_session, {"issue_type": "x"})
