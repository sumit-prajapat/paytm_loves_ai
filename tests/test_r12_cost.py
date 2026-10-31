"""R12: cost scales with requests. Tier 0 for hero cases, quotas, cooldowns, caching, budgets."""
import pytest
from sqlalchemy import select

from app.adapters.llm.base import BaseLLMAdapter, LLMUnavailable
from app.config import get_settings
from app.db.models import AgentRun, UsageEvent
from app.llm.gateway import llm_gateway
from tests.conftest import auth

P = "/api/v1"
pytestmark = pytest.mark.usefixtures("seeded")


@pytest.mark.parametrize("body", [
    {"scope": "settlement"}, {"scope": "device"}, {"scope": "refunds"}, {"scope": "all", "channel": "soundbox"},
])
async def test_hero_checkups_resolve_at_tier0(client, body):
    b = (await client.post(f"{P}/checkups", headers=auth("ramesh"), json=body)).json()
    assert b["cost"]["tier"] == 0 and b["cost"]["llm_calls"] == 0 and b["cost"]["tokens"] == 0
    assert llm_gateway.stats.get("calls", 0) == 0


async def test_hero_chat_phrases_resolve_at_tier0(client):
    for msg in ("Aaj ka settlement kam kyun aaya?", "Soundbox band ho gaya", "Mera payment fail ho gaya",
                "Delhi se Mumbai kal shaam ka flight"):
        who = "arjun" if "flight" in msg else "ramesh"
        b = (await client.post(f"{P}/chat", headers=auth(who), json={"message": msg})).json()
        assert b["cost"]["llm_calls"] == 0, (msg, b)
    assert llm_gateway.stats.get("calls", 0) == 0


async def test_cache_hit_skips_work_and_llm(client):
    first = (await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "settlement"})).json()
    second = (await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "settlement"})).json()
    assert second["checkup"]["cached"] is True and second["checkup"]["id"] == first["checkup"]["id"]
    assert "minutes ago" in second["reply_text"] or "मिनट पहले" in second["reply_text"]
    assert second["checkup"]["recheck_available_in_seconds"] >= 0
    assert llm_gateway.stats.get("calls", 0) == 0


async def test_cooldown_blocks_identical_recheck(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "CHECKUP_COOLDOWN_SECONDS", 300)
    first = (await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "device"})).json()
    again = (await client.post(f"{P}/checkups", headers=auth("ramesh"),
                               json={"scope": "device", "force_refresh": True, "language": "en"})).json()
    assert again["checkup"]["cached"] is True and again["checkup"]["id"] == first["checkup"]["id"]
    assert "re-check in" in again["reply_text"]


async def test_daily_checkup_quota(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "CHECKUPS_PER_USER_PER_DAY", 2)
    monkeypatch.setattr(get_settings(), "CHECKUP_COOLDOWN_SECONDS", 0)
    for scope in ("settlement", "device"):
        assert (await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": scope})).status_code == 200
    r = await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "refunds"})
    assert r.status_code == 429
    # Other merchants are unaffected (quota is per user)
    assert (await client.post(f"{P}/checkups", headers=auth("sunita"), json={"scope": "device"})).status_code == 200


async def test_llm_classification_cache_hit_skips_llm(client):
    msg = "mere dukaan ka hisaab kitaab samjhao zara"  # free-form: Tier 0 unsure -> Tier 1
    await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": msg})
    calls_after_first = llm_gateway.stats.get("calls", 0)
    assert calls_after_first == 1
    await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": msg})
    assert llm_gateway.stats.get("calls", 0) == calls_after_first
    assert llm_gateway.stats.get("cache_hits", 0) == 1


async def test_per_user_llm_quota_degrades_visibly(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "LLM_CALLS_PER_USER_PER_DAY", 0)
    b = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "kuch samajh nahi aa raha bhai"})).json()
    assert b["degraded"] is True and "user_llm_calls_per_day" in b["degrade_reasons"]
    assert b["status"] in ("needs_input", "escalated") and b["reply_text"]
    assert llm_gateway.stats.get("calls", 0) == 0


async def test_global_budget_exhausted_falls_back_then_human_queue(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "GLOBAL_LLM_BUDGET_INR_PER_DAY", 0.0)
    first = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "yeh kya ho raha hai"})).json()
    assert first["status"] == "needs_input" and first["degraded"] is True
    second = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "kuch bhi samjhao"})).json()
    assert second["status"] == "escalated" and second["escalation"]["ticket_id"]


class _BrokenLLM(BaseLLMAdapter):
    provider = "broken"

    async def complete(self, **kwargs):
        raise LLMUnavailable("simulated outage")


async def test_provider_outage_never_fails_silently(client):
    llm_gateway.set_adapter(_BrokenLLM())
    b = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "hmm samjhao zara"})).json()
    assert b["degraded"] is True and "llm_unavailable" in b["degrade_reasons"]
    assert b["llm_error"].startswith("gemini") or "simulated outage" in b["llm_error"]


async def test_cost_accounting_in_agent_runs_usage_and_metrics(client, db_session):
    await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "settlement"})
    await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "hmm zara samjhao"})
    finals = (await db_session.execute(select(AgentRun).where(AgentRun.tool == "finalize_response",
                                                              AgentRun.agent == "captain"))).scalars().all()
    assert {r.tier for r in finals} == {0, 1}
    assert any(r.tokens > 0 for r in finals)
    llm_rows = (await db_session.execute(select(UsageEvent).where(UsageEvent.kind == "llm_call"))).scalars().all()
    assert len(llm_rows) == 1 and llm_rows[0].tier == 1 and llm_rows[0].tokens > 0
    m = (await client.get(f"{P}/metrics", headers=auth("ops"))).json()
    assert m["tier_mix"]["tier0"]["requests"] >= 1 and m["tier_mix"]["tier1"]["requests"] == 1
    assert m["llm_calls"] == 1 and m["llm_calls_avoided"] >= 1
    assert m["checkups_run"] >= 1 and m["tickets_deflected"] >= 1
    assert m["support_cost_saved_inr"] == m["tickets_deflected"] * get_settings().SUPPORT_COST_PER_TICKET_INR
    assert "tickets_prevented" not in m
    assert m["disclaimer"].startswith("ALL FIGURES")


async def test_max_tool_calls_per_turn_escalates_safely(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "MAX_TOOL_CALLS_PER_TURN", 3)
    b = (await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "all"})).json()
    assert b["status"] == "escalated"
