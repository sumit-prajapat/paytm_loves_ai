"""Saarthi evaluation (SIMULATED DATA).

Runs every labelled case through the real Captain entry point as a user-triggered chat turn,
on an isolated temporary database, fully offline by default (MockLLM). PASS/FAIL is computed
against targets, never hardcoded. R1 violations come from the runtime validator, which checks
replies against tool facts only.

    python eval/run_eval.py            # offline, deterministic
    python eval/run_eval.py --live     # use the configured LLM provider (costs money)
"""
import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from collections import Counter

sys.path.insert(0, os.path.abspath("."))

SUBJECTS = {  # scenario -> (actor user id, role, subject type, subject id)
    "settlement_short": ("usr_ramesh", "merchant", "merchant", "m_ramesh"),
    "soundbox_offline": ("usr_ramesh", "merchant", "merchant", "m_ramesh"),
    "payment_failed_refund": ("usr_sunita", "merchant", "merchant", "m_sunita"),
    "chargeback_dispute": ("usr_gupta", "merchant", "merchant", "m_disputed"),
    "loan_flow": ("usr_ramesh", "merchant", "merchant", "m_ramesh"),
    "travel_concierge": ("usr_arjun", "traveller", "traveller", "c_arjun"),
    "adversarial_trick": ("usr_ramesh", "merchant", "merchant", "m_ramesh"),
    "ambiguous_query": ("usr_ramesh", "merchant", "merchant", "m_ramesh"),
    "smalltalk": ("usr_ramesh", "merchant", "merchant", "m_ramesh"),
}
OUTCOME_STATUSES = {
    "auto_resolve": {"resolved", "no_issue", "ready_for_review_and_pay", "awaiting_human_approval"},
    "escalate": {"escalated"},
    "refuse": {"refused"},
    "ask_clarification": {"needs_input"},
}
TARGETS = {"accuracy": 80.0, "escalation_precision": 95.0, "escalation_recall": 95.0, "validator_violations": 0}


def configure_env(live: bool) -> str:
    db_path = os.path.join(tempfile.mkdtemp(prefix="saarthi_eval_"), "eval.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["HOUSEKEEPING_ENABLED"] = "false"
    os.environ["TTS_PROVIDER"] = "mock"
    if not live:
        os.environ.update({"LLM_PROVIDER": "mock", "GEMINI_API_KEY": "", "SARVAM_API_KEY": ""})
    return db_path


async def run(dataset_path: str, report_path: str) -> dict:
    from sqlalchemy import delete

    from app.agents.captain import Trigger, captain_agent
    from app.db.models import Base, ConversationState
    from app.db.seed import seed_database
    from app.db.session import AsyncSessionLocal, engine
    from app.logging import setup_logging

    setup_logging("WARNING")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_database(db, merchant_count=5)

    cases = [json.loads(line) for line in open(dataset_path, encoding="utf-8") if line.strip()]
    rows, tiers, latencies = [], Counter(), []
    tp = fp = fn = violations = llm_calls = 0
    cost = 0.0
    travel_picks: dict[str, set] = {}
    for case in cases:
        actor, role, stype, sid = SUBJECTS[case["scenario"]]
        async with AsyncSessionLocal() as db:
            await db.execute(delete(ConversationState).where(ConversationState.subject_id == sid))
            await db.commit()
            t0 = time.perf_counter()
            res = await captain_agent.handle(Trigger(
                channel="chat", request_type="chat", actor_id=actor, actor_role=role, subject_type=stype,
                subject_id=sid, message=case["input"]), db)
            latencies.append((time.perf_counter() - t0) * 1000)
        status, expected = res.get("status"), case["expected_outcome"]
        passed = status in OUTCOME_STATUSES[expected]
        if expected == "escalate":
            tp, fn = tp + (status == "escalated"), fn + (status != "escalated")
        elif status == "escalated":
            fp += 1
        v = len(res.get("validator_violations") or [])
        violations += v
        tiers[res["cost"]["tier"]] += 1
        llm_calls += res["cost"]["llm_calls"]
        cost += res["cost"]["cost_inr"]
        if res.get("recommended"):
            travel_picks.setdefault(case["input"], set()).add(res["recommended"]["flight_id"])
        rows.append({"id": case["id"], "scenario": case["scenario"], "language": case["language"],
                     "expected": expected, "actual": status, "passed": passed, "tier": res["cost"]["tier"],
                     "violations": v, "reply": res.get("reply_text", "")[:90].replace("\n", " ")})

    # Travel recommendation consistency: run each travel case a second time
    async with AsyncSessionLocal() as db:
        for q in list(travel_picks):
            await db.execute(delete(ConversationState).where(ConversationState.subject_id == "c_arjun"))
            res = await captain_agent.handle(Trigger(channel="chat", request_type="chat", actor_id="usr_arjun",
                                                     actor_role="traveller", subject_type="traveller",
                                                     subject_id="c_arjun", message=q), db)
            if res.get("recommended"):
                travel_picks[q].add(res["recommended"]["flight_id"])
    consistent = sum(1 for picks in travel_picks.values() if len(picks) == 1)

    n = len(rows)
    resolved = sum(1 for r in rows if r["actual"] in OUTCOME_STATUSES["auto_resolve"])
    summary = {
        "cases": n,
        "hinglish_pct": round(100 * sum(r["language"] == "hinglish" for r in rows) / n, 1),
        "accuracy": round(100 * sum(r["passed"] for r in rows) / n, 1),
        "deflection_pct": round(100 * resolved / n, 1),
        "escalation_precision": round(100 * tp / max(tp + fp, 1), 1),
        "escalation_recall": round(100 * tp / max(tp + fn, 1), 1),
        "validator_violations": violations,
        "tier_mix": {f"tier{k}": v for k, v in sorted(tiers.items())},
        "llm_calls": llm_calls,
        "cost_inr_total": round(cost, 4),
        "cost_per_resolution_inr": round(cost / resolved, 4) if resolved else 0.0,
        "avg_latency_ms": round(sum(latencies) / n, 1),
        "travel_consistency": f"{consistent}/{len(travel_picks)}",
    }
    verdict = {
        "accuracy": summary["accuracy"] >= TARGETS["accuracy"],
        "escalation_precision": summary["escalation_precision"] >= TARGETS["escalation_precision"],
        "escalation_recall": summary["escalation_recall"] >= TARGETS["escalation_recall"],
        "validator_violations": violations == TARGETS["validator_violations"],
    }
    lines = ["# Saarthi Evaluation Report", "", "> **SIMULATED DATA.** Generated by `eval/run_eval.py`; "
             "PASS/FAIL is computed, not hardcoded.", "", "| Metric | Target | Measured | Result |",
             "| --- | --- | --- | --- |"]
    for key, target in (("accuracy", "≥ 80%"), ("escalation_precision", "≥ 95%"),
                        ("escalation_recall", "≥ 95%"), ("validator_violations", "0")):
        lines.append(f"| {key} | {target} | {summary[key]} | {'PASS' if verdict[key] else 'FAIL'} |")
    for key in ("cases", "hinglish_pct", "deflection_pct", "tier_mix", "llm_calls", "cost_inr_total",
                "cost_per_resolution_inr", "avg_latency_ms", "travel_consistency"):
        lines.append(f"| {key} | - | {summary[key]} | info |")
    lines += ["", "## Mismatches", "", "| id | scenario | lang | expected | actual | reply |", "| --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {r['id']} | {r['scenario']} | {r['language']} | {r['expected']} | {r['actual']} | {r['reply']} |"
              for r in rows if not r["passed"]]
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return {"summary": summary, "verdict": verdict, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="use the configured LLM provider (costs money)")
    parser.add_argument("--dataset", default="eval/cases.jsonl")
    parser.add_argument("--report", default="eval/report.md")
    args = parser.parse_args()
    configure_env(args.live)
    out = asyncio.run(run(args.dataset, args.report))
    print(json.dumps(out["summary"], indent=1, ensure_ascii=False))
    print("verdict:", out["verdict"])
    for r in out["rows"]:
        if not r["passed"]:
            print(f"  MISMATCH {r['id']} {r['scenario']} expected={r['expected']} actual={r['actual']} :: {r['reply']}")
