"""Business metrics computed from the database (no hardcoded baselines, no proactive counters)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.action import validator_stats
from app.config import get_settings
from app.db.models import Checkup, LoanRequest, OfferConsent, UsageEvent


async def get_business_metrics(db: AsyncSession) -> dict[str, Any]:
    s = get_settings()

    async def scalar(stmt) -> Any:
        return (await db.execute(stmt)).scalar_one()

    by_status = dict((await db.execute(select(Checkup.status, func.count(Checkup.id)).group_by(Checkup.status))).all())
    checkups_run = sum(by_status.values())
    resolved = by_status.get("resolved", 0)
    no_issue = by_status.get("no_issue", 0)
    escalated = by_status.get("escalated", 0)
    deflected = resolved + no_issue
    avg_res_ms = await scalar(select(func.avg(Checkup.duration_ms)).where(Checkup.status == "resolved"))

    usage = dict((await db.execute(select(UsageEvent.kind, func.count(UsageEvent.id)).group_by(UsageEvent.kind))).all())
    tier_rows = (await db.execute(
        select(UsageEvent.tier, func.count(UsageEvent.id)).where(UsageEvent.kind == "request").group_by(UsageEvent.tier)
    )).all()
    requests = sum(c for _, c in tier_rows)
    tier_mix = {f"tier{tier}": {"requests": c, "pct": round(100.0 * c / requests, 1) if requests else 0.0}
                for tier, c in sorted(tier_rows)}
    llm_cost = float(await scalar(select(func.coalesce(func.sum(UsageEvent.cost_inr), 0.0))
                                  .where(UsageEvent.kind == "llm_call")))
    llm_tokens = int(await scalar(select(func.coalesce(func.sum(UsageEvent.tokens), 0))
                                  .where(UsageEvent.kind == "llm_call")))
    tier0_requests = next((c for t, c in tier_rows if t == 0), 0)
    travel_ms = await scalar(select(func.avg(UsageEvent.duration_ms)).where(
        UsageEvent.kind == "request", UsageEvent.outcome == "ready_for_review_and_pay"))

    loan_leads = await scalar(select(func.count(LoanRequest.id)))
    offered = await scalar(select(func.count(OfferConsent.merchant_id)).where(OfferConsent.offers_shown > 0))
    accepted = await scalar(select(func.count(OfferConsent.merchant_id)).where(OfferConsent.status == "accepted"))
    declined = await scalar(select(func.count(OfferConsent.merchant_id)).where(OfferConsent.status == "declined"))

    return {
        "checkups_run": checkups_run,
        "checkup_cache_hits": usage.get("checkup_cache_hit", 0),
        "auto_resolved": resolved,
        "no_issue_found": no_issue,
        "escalated": escalated,
        "escalation_rate_pct": round(100.0 * escalated / checkups_run, 1) if checkups_run else 0.0,
        "tickets_deflected": deflected,
        "support_cost_saved_inr": round(deflected * s.SUPPORT_COST_PER_TICKET_INR, 2),
        "support_cost_per_ticket_inr": s.SUPPORT_COST_PER_TICKET_INR,
        "avg_resolution_seconds": round((avg_res_ms or 0.0) / 1000.0, 3),
        "loan_leads": loan_leads,
        "offers_shown_merchants": offered,
        "offers_declined_merchants": declined,
        "offer_conversion_pct": round(100.0 * accepted / offered, 1) if offered else 0.0,
        "requests_total": requests,
        "tier_mix": tier_mix,
        "llm_calls": usage.get("llm_call", 0),
        "llm_cache_hits": usage.get("llm_cache_hit", 0),
        "llm_calls_avoided": tier0_requests + usage.get("checkup_cache_hit", 0) + usage.get("llm_cache_hit", 0),
        "llm_tokens": llm_tokens,
        "llm_cost_inr": round(llm_cost, 4),
        "cost_per_resolution_inr": round(llm_cost / deflected, 4) if deflected else 0.0,
        "travel_shortlist_avg_ms": round(travel_ms or 0.0, 1),
        "validator_violations_since_start": validator_stats.get("violations", 0),
        "disclaimer": "ALL FIGURES ARE MEASURED ON SIMULATED DATA",
    }
