"""Captain: the ONLY orchestrator entry point, and it starts ONLY from a user trigger (R11).

Triggers: app button / chat message / voice / Soundbox button or voice / "raise an issue".
There is no event, schedule or proactive path into the agents.

Per turn: plan -> context -> (security) -> listener (Tier 0, Tier 1 if unsure) -> route ->
diagnostics / offer / travel -> Guardian on every action -> handoff if needed -> validated reply.
Cost (tier, tokens, INR) is accumulated in a TurnContext and written to agent_runs + usage.
"""
from __future__ import annotations

import datetime
import logging
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.action import action_agent
from app.agents.base import BaseAgent
from app.agents.context import context_agent
from app.agents.diagnostician import diagnostician_agent
from app.agents.guardian import guardian_agent
from app.agents.handoff import handoff_agent
from app.agents.listener import listener_agent
from app.agents.offer import offer_agent
from app.agents.planner import planner_agent
from app.agents.ranker import ranker_agent
from app.agents.search import search_agent
from app.config import get_settings
from app.core.security import detect_prompt_injection, detect_sensitive_credential
from app.core.turn import ToolBudgetExceeded, TurnContext, reset_turn, set_turn
from app.db.models import Checkup
from app.i18n import resolve_language, t
from app.i18n.numbers import money
from app.nlu.rules import extract_travel_slots, normalize
from app.services.audit import record_audit_log
from app.services.checkup_service import expand_scope
from app.services.conversation_service import load_state, save_state
from app.services.number_validator import number_validator
from app.services.pulse_service import booking_status, build_advice, build_pulse
from app.services.usage_service import QuotaExceeded, enforce_checkup_quota, record_usage
from app.trace.bus import trace_bus

logger = logging.getLogger(__name__)

Channel = Literal["app", "chat", "voice", "soundbox"]
INTENT_TO_SCOPE = {
    "settlement_short": "settlement",
    "soundbox_offline": "device",
    "refund_status": "refunds",
    "payment_failed": "payments,refunds",
    "chargeback_dispute": "payments",
}
MONEY_KEYS = {"gap", "expected", "actual", "amount", "refund_adjustment", "fees", "chargeback_hold",
              "explained_total", "other_deductions"}


class SubjectNotFound(Exception):
    pass


class Trigger(BaseModel):
    """A user action that starts a turn. Nothing else can start one."""

    channel: Channel
    request_type: Literal["checkup", "chat", "voice", "soundbox", "issue"]
    actor_id: str
    actor_role: str
    subject_type: Literal["merchant", "traveller"]
    subject_id: str
    message: str | None = None
    scope: str | None = None
    language: str | None = None
    session_id: str | None = None
    force_refresh: bool = False
    elder_mode: bool = False
    insist_ticket: bool = False
    description: str | None = Field(None, max_length=2000)


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _public_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for f in findings:
        facts = dict(f["facts"])
        for k in list(facts):
            if k in MONEY_KEYS and isinstance(facts[k], (int, float)):
                facts[f"{k}_money"] = money(facts[k])
        if isinstance(facts.get("items"), list):
            facts["items"] = [{**i, "amount_money": money(i["amount"])} for i in facts["items"]]
        out.append({k: f[k] for k in ("scope", "code", "issue_type", "resolution", "is_issue", "confidence",
                                      "evidence")} | {"facts": facts, "playbook": f.get("playbook")})
    return out


class CaptainAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="captain")

    # ------------------------------------------------------------------ entry point
    async def handle(self, trigger: Trigger, db: AsyncSession) -> dict[str, Any]:
        s = get_settings()
        case_id = f"case_{uuid.uuid4().hex[:12]}"
        ctx = TurnContext(case_id=case_id, subject_id=trigger.subject_id, actor_id=trigger.actor_id,
                          channel=trigger.channel, session_id=trigger.session_id,
                          max_tool_calls=s.MAX_TOOL_CALLS_PER_TURN)
        token = set_turn(ctx)
        start = time.perf_counter()
        facts_pool: list[Any] = []
        try:
            await self.emit_step(
                case_id=case_id, tool="captain_plan",
                input_data={"trigger": trigger.model_dump(exclude={"message", "description"}),
                            "has_message": bool(trigger.message)},
                output_data={"plan": self._plan(trigger)}, confidence=1.0, db=db,
            )
            bundle = await context_agent.load(case_id, trigger.subject_type, trigger.subject_id, db)
            if "merchant" not in bundle and "customer" not in bundle:
                raise SubjectNotFound(trigger.subject_id)
            try:
                result = await self._dispatch(trigger, bundle, ctx, db, facts_pool)
            except ToolBudgetExceeded:
                ctx.max_tool_calls += 10  # room to hand off safely
                result = await self._human_queue(trigger, bundle, ctx, db, "tool_budget_exceeded", ctx.language)
            result = await self._finalize(trigger, ctx, db, result, facts_pool, start)
            await db.commit()
            return result
        finally:
            reset_turn(token)

    @staticmethod
    def _plan(trigger: Trigger) -> list[str]:
        if trigger.message is None:
            return ["context", "diagnostician", "guardian", "action|handoff", "offer?"]
        return ["context", "security", "listener(tier0->tier1?)", "route", "guardian", "reply"]

    # ------------------------------------------------------------------ routing
    async def _dispatch(self, trigger: Trigger, bundle: dict[str, Any], ctx: TurnContext, db: AsyncSession,
                        facts_pool: list[Any]) -> dict[str, Any]:
        lang = resolve_language(trigger.language or bundle.get("language"))
        ctx.language = lang
        if trigger.message is None:
            if trigger.subject_type != "merchant":
                raise ValueError("Check-ups are for merchants")
            if trigger.request_type == "issue":
                return await self._raise_issue(trigger, bundle, ctx, db, lang, facts_pool)
            return await self._checkup(trigger, bundle, ctx, db, trigger.scope or "all", lang, facts_pool)

        text = trigger.message.strip()
        is_cred, cred_kind = detect_sensitive_credential(text)
        is_inj, inj_reason = detect_prompt_injection(text)
        if is_cred or is_inj:
            lang = resolve_language(trigger.language or listener_lang(text) or bundle.get("language"))
            ctx.language = lang
            action = "SENSITIVE_CREDENTIAL_BLOCKED" if is_cred else "PROMPT_INJECTION_BLOCKED"
            await record_audit_log(db, case_id=ctx.case_id, actor=trigger.actor_id, action=action,
                                   detail={"kind": cred_kind or inj_reason, "channel": trigger.channel})
            await self.emit_step(case_id=ctx.case_id, tool="security_refusal", input_data={"chars": len(text)},
                                 output_data={"blocked": action}, confidence=1.0, db=db)
            return {"status": "refused", "intent": "unsafe_request",
                    "reply_text": t("security.credential" if is_cred else "security.injection", lang),
                    "sensitive_data_blocked": is_cred, "prompt_injection_blocked": is_inj}

        state = await load_state(db, trigger.subject_id)
        pending = (state.get("travel") or {}).get("pending")
        if trigger.subject_type == "traveller" and pending:
            # Answer to our one pending question ("Hyderabad", "kal"): fill it at Tier 0, no LLM.
            filled = extract_travel_slots(text)
            if pending in filled or (pending in ("origin", "destination") and "destination" in filled):
                lang = resolve_language(trigger.language or listener_lang(text) or bundle.get("language"))
                ctx.language = lang
                nlu = {"intent": "travel_flight_request", "confidence": 0.9, "slots": filled, "flags": {},
                       "tier": 0, "language": lang}
                await self.emit_step(case_id=ctx.case_id, tool="captain_plan", input_data={"slot_fill": pending},
                                     output_data={"filled": filled}, confidence=0.9, db=db)
                return {"intent": "travel_flight_request", "nlu_tier": 0} | await self._travel(
                    trigger, bundle, ctx, db, lang, nlu, state, text, facts_pool)

        nlu = await listener_agent.understand(ctx.case_id, text, db)
        lang = resolve_language(trigger.language or nlu["language"] or bundle.get("language"))
        ctx.language = lang
        intent = nlu["intent"]
        if nlu["confidence"] < get_settings().CLARIFY_CONFIDENCE_THRESHOLD and intent != "decline_offer":
            intent = "unknown"
        base = {"intent": intent, "nlu_tier": nlu["tier"]}
        if nlu.get("llm_error"):
            base["llm_error"] = nlu["llm_error"]

        if trigger.subject_type == "traveller":
            return base | await self._traveller_turn(trigger, bundle, ctx, db, lang, intent, nlu, state, text, facts_pool)
        return base | await self._merchant_turn(trigger, bundle, ctx, db, lang, intent, nlu, state, facts_pool)

    async def _merchant_turn(self, trigger, bundle, ctx, db, lang, intent, nlu, state, facts_pool) -> dict[str, Any]:
        merchant = bundle["merchant"]
        if intent == "payment_request":
            await guardian_agent.review(ctx.case_id, db, action_class="payment", subject=merchant.id)
            return {"status": "refused", "reply_text": t("payment.refused", lang)}
        if intent == "loan_approve_request":
            await guardian_agent.review(ctx.case_id, db, action_class="loan_approval", subject=merchant.id)
            return {"status": "refused", "reply_text": t("loan.approve_refused", lang)}
        if intent in INTENT_TO_SCOPE:
            prefix = None
            if nlu["flags"].get("refund_demand"):
                await guardian_agent.review(ctx.case_id, db, action_class="refund_issue", subject=merchant.id)
                prefix = t("refunds.demand_prefix", lang)
            res = await self._checkup(trigger, bundle, ctx, db, INTENT_TO_SCOPE[intent], lang, facts_pool)
            if prefix:
                res["reply_text"] = f"{prefix} {res['reply_text']}"
            return res
        if intent == "loan_emi_query":
            amount = nlu["slots"].get("amount")
            quote = await offer_agent.emi_quote(ctx.case_id, db, merchant_id=merchant.id, lang=lang,
                                                amount=amount, tenure=nlu["slots"].get("tenure_months"))
            facts_pool.append({"quote": quote["quote"], "slots": nlu["slots"]})
            if quote["quote"]:
                state["loan_quote"] = {"amount": amount, "tenure": quote["quote"]["tenure_months"]}
                await save_state(db, merchant.id, state)
            return {"status": "resolved", "reply_text": quote["text"],
                    "loan_quote": quote["quote"] and {**quote["quote"],
                                                      "monthly_emi_money": money(quote["quote"]["monthly_emi"])}}
        if intent == "loan_apply":
            last = state.get("loan_quote", {})
            amount = nlu["slots"].get("amount") or last.get("amount")
            if not amount:
                return {"status": "needs_input", "reply_text": t("loan.ask_amount", lang)}
            res = await offer_agent.apply(ctx.case_id, db, merchant_id=merchant.id, actor_id=trigger.actor_id,
                                          lang=lang, amount=float(amount),
                                          tenure=nlu["slots"].get("tenure_months") or last.get("tenure"))
            if res["status"] == "escalate":
                return await self._human_queue(trigger, bundle, ctx, db, "kill_switch_loan_request", lang,
                                               key="escalation.killswitch")
            facts_pool.append(res["request"] | {"amount_raw": amount, "request_id": res["request_id"]})
            return {"status": "awaiting_human_approval", "reply_text": res["text"], "loan_request": res["request"]}
        if intent == "decline_offer":
            if nlu["flags"].get("bare_negation") and not await offer_agent.offer_pending(db, merchant.id):
                return await self._unknown(trigger, bundle, ctx, db, lang, state)
            text = await offer_agent.decline(ctx.case_id, db, merchant_id=merchant.id, actor_id=trigger.actor_id,
                                             lang=lang)
            return {"status": "resolved", "reply_text": text, "offer_declined": True}
        if intent == "pulse_request":
            p = await build_pulse(db, merchant, lang)
            await self._step_pulse(ctx, db, "build_pulse", p)
            facts_pool.append(p["facts"])
            return {"status": "resolved", "reply_text": p["text"]}
        if intent == "advice_request":
            a = await build_advice(db, merchant, lang)
            await self._step_pulse(ctx, db, "build_advice", a)
            facts_pool.append(a["facts"])
            return {"status": "resolved", "reply_text": a["text"]}
        if intent == "raise_issue":
            return await self._raise_issue(trigger, bundle, ctx, db, lang, facts_pool)
        if intent == "greeting":
            return {"status": "resolved", "reply_text": t("smalltalk.greeting", lang)}
        return await self._unknown(trigger, bundle, ctx, db, lang, state)

    async def _traveller_turn(self, trigger, bundle, ctx, db, lang, intent, nlu, state, text, facts_pool):
        customer = bundle["customer"]
        prefix = None
        if intent == "payment_request":
            await guardian_agent.review(ctx.case_id, db, action_class="payment", subject=customer.id)
            prefix = t("payment.refused", lang)
            slots = extract_travel_slots(text)
            if not ({"origin", "destination"} & set(slots)) and "travel" not in state:
                return {"status": "refused", "reply_text": prefix}
            intent, nlu = "travel_flight_request", {**nlu, "slots": slots}
        if intent == "travel_status":
            st = await booking_status(db, customer.id, nlu["slots"].get("booking_ref"), lang)
            await self._step_pulse(ctx, db, "travel_booking_status", st)
            facts_pool.append(st["facts"])
            return {"status": "resolved" if st["booking"] else "needs_input", "reply_text": st["text"],
                    "booking": st["booking"]}
        travel_state = state.get("travel")
        if intent == "travel_flight_request" or (travel_state and intent in ("unknown", "greeting")):
            res = await self._travel(trigger, bundle, ctx, db, lang, nlu, state, text, facts_pool)
            if prefix:
                res["reply_text"] = f"{prefix} {res['reply_text']}"
            return res
        if intent == "greeting":
            return {"status": "resolved", "reply_text": t("smalltalk.greeting", lang)}
        return {"status": "needs_input", "reply_text": t("travel.ask_destination", lang)}

    # ------------------------------------------------------------------ check-up
    async def _checkup(self, trigger: Trigger, bundle, ctx: TurnContext, db: AsyncSession, scope: str, lang: str,
                       facts_pool: list[Any]) -> dict[str, Any]:
        s = get_settings()
        merchant = bundle["merchant"]
        scope = ",".join(expand_scope(scope)) if scope != "all" else "all"
        now = _utcnow()
        cached = (await db.execute(
            select(Checkup).where(Checkup.merchant_id == merchant.id, Checkup.scope == scope,
                                  Checkup.cache_valid.is_(True),
                                  Checkup.created_at >= now - datetime.timedelta(seconds=s.CHECKUP_CACHE_TTL_SECONDS))
            .order_by(Checkup.created_at.desc()).limit(1)
        )).scalars().first()
        if cached is not None:
            age = (now - cached.created_at.replace(tzinfo=None)).total_seconds()
            in_cooldown = age < s.CHECKUP_COOLDOWN_SECONDS
            if not trigger.force_refresh or in_cooldown:
                return await self._cached_result(trigger, ctx, db, cached, lang, age, in_cooldown, facts_pool)

        try:
            await enforce_checkup_quota(db, merchant.id)
        except QuotaExceeded as exc:
            return {"status": "quota_exceeded", "reply_text": t("checkup.quota_exceeded", lang),
                    "quota": {"kind": exc.kind, "limit": exc.limit}}

        findings = await diagnostician_agent.diagnose(ctx.case_id, merchant, scope, db)
        to_escalate, killswitch_hit = [], False
        for f in findings:
            res = f["resolution"]
            action_class = {"explain": "explain", "guide": "guide", "info": "read", "playbook": "playbook_resolution",
                            "escalate": "create_ticket"}[res]
            decision = await guardian_agent.review(
                ctx.case_id, db, action_class=action_class, subject=merchant.id, confidence=f["confidence"],
                financial_impact=f["financial_impact_inr"], detail={"finding": f["code"]})
            f["guardian"] = {"decision": decision.decision, "reason": decision.reason}
            if res == "escalate" or decision.decision in ("escalate", "needs_input", "block"):
                if res == "playbook" and decision.decision == "escalate":
                    killswitch_hit = True
                    f["resolution"] = "escalate"
                    f.pop("playbook", None)
                if f["is_issue"]:
                    to_escalate.append(f)

        ticket_id, reused = None, False
        if to_escalate:
            reason = "; ".join(f["guardian"]["reason"] if f["guardian"]["decision"] != "allow"
                               else f"{f['code']} needs a specialist" for f in to_escalate)
            h = await handoff_agent.escalate(
                ctx.case_id, db, merchant_id=merchant.id, findings=to_escalate, reason=reason,
                reason_code="kill_switch" if killswitch_hit else to_escalate[0]["code"], language=lang,
                actor_id=trigger.actor_id, user_message=trigger.message)
            ticket_id, reused = h["ticket_id"], h["reused"]

        rendered = await action_agent.explain(ctx.case_id, findings, lang=lang, name=bundle["name"], scope=scope,
                                              ticket_id=ticket_id, db=db)
        reply = rendered["text"]
        if killswitch_hit:
            reply += "\n" + t("escalation.killswitch", lang, ticket_id=ticket_id)
        status = "escalated" if ticket_id else ("resolved" if any(f["is_issue"] for f in findings) else "no_issue")
        facts_pool.extend([f["facts"] for f in findings] + [{"ticket_id": ticket_id}])

        offer = None
        if status == "resolved" and trigger.channel != "soundbox":
            offer = await offer_agent.maybe_offer(ctx.case_id, db, merchant_id=merchant.id, lang=lang)
            if offer:
                facts_pool.append({"offer": offer})

        checkup = Checkup(
            id=f"chk_{uuid.uuid4().hex[:12]}", merchant_id=merchant.id, scope=scope, channel=trigger.channel,
            language=lang, triggered_by=trigger.actor_id, on_behalf=trigger.actor_role in ("ops_agent", "admin"),
            case_id=ctx.case_id, status=status, findings_json=_public_findings(findings), reply_text=reply,
            ticket_id=ticket_id, cache_valid=True, created_at=now,
        )
        db.add(checkup)
        await db.flush()
        return {"status": status, "reply_text": reply, "spoken_text": rendered["spoken_text"],
                "checkup": {"id": checkup.id, "scope": scope, "status": status, "cached": False,
                            "checked_at": now.isoformat() + "Z", "findings": checkup.findings_json},
                "escalation": {"ticket_id": ticket_id, "reused": reused} if ticket_id else None,
                "offer": offer, "validator_violations": rendered["violations"], "_checkup_row": checkup}

    async def _cached_result(self, trigger, ctx, db, cached: Checkup, lang, age, in_cooldown, facts_pool):
        s = get_settings()
        minutes_ago = int(age // 60)
        note = (t("checkup.cooldown_note", lang, wait_seconds=int(s.CHECKUP_COOLDOWN_SECONDS - age))
                if trigger.force_refresh and in_cooldown else t("checkup.cached_note", lang, minutes_ago=minutes_ago))
        await record_usage(db, user_id=trigger.subject_id, actor_id=trigger.actor_id, case_id=ctx.case_id,
                           session_id=trigger.session_id, kind="checkup_cache_hit", channel=trigger.channel)
        facts_pool.extend([f.get("facts", {}) for f in (cached.findings_json or [])])
        facts_pool.append({"minutes_ago": minutes_ago, "wait": int(s.CHECKUP_COOLDOWN_SECONDS - age),
                           "ticket_id": cached.ticket_id})
        reply = cached.reply_text
        if cached.language != lang and cached.findings_json:
            # Same facts, re-rendered in the language the user is using now (Tier 0, no re-run).
            profile = await context_agent.load(ctx.case_id, "merchant", cached.merchant_id, db)
            rendered = await action_agent.explain(ctx.case_id, cached.findings_json, lang=lang,
                                                  name=profile.get("name", ""), scope=cached.scope,
                                                  ticket_id=cached.ticket_id, db=db)
            reply = rendered["text"]
        return {"status": cached.status, "reply_text": f"{reply}\n{note}",
                "checkup": {"id": cached.id, "scope": cached.scope, "status": cached.status, "cached": True,
                            "checked_at": cached.created_at.isoformat() + "Z", "minutes_ago": minutes_ago,
                            "recheck_available_in_seconds": max(0, int(s.CHECKUP_COOLDOWN_SECONDS - age)),
                            "findings": cached.findings_json},
                "escalation": {"ticket_id": cached.ticket_id, "reused": True} if cached.ticket_id else None,
                "offer": None, "cache_hit": True}

    async def _raise_issue(self, trigger, bundle, ctx, db, lang, facts_pool) -> dict[str, Any]:
        """'Raise an issue': check-up first; ticket only if unresolved or the user insists."""
        res = await self._checkup(trigger, bundle, ctx, db, trigger.scope or "all", lang, facts_pool)
        if res["status"] in ("escalated", "quota_exceeded") or not trigger.insist_ticket:
            res["ticket_created"] = res["status"] == "escalated"
            res["can_insist"] = res["status"] in ("resolved", "no_issue")
            return res
        h = await handoff_agent.escalate(
            ctx.case_id, db, merchant_id=bundle["merchant"].id, findings=[], reason="Merchant insisted on a ticket",
            reason_code="user_insisted", language=lang, actor_id=trigger.actor_id,
            user_message=trigger.description or trigger.message)
        facts_pool.append({"ticket_id": h["ticket_id"]})
        res.update(status="escalated", ticket_created=True, escalation={"ticket_id": h["ticket_id"], "reused": h["reused"]},
                   reply_text=res["reply_text"] + "\n" + t("escalation.generic", lang, ticket_id=h["ticket_id"]))
        return res

    # ------------------------------------------------------------------ travel
    async def _travel(self, trigger, bundle, ctx, db, lang, nlu, state, text, facts_pool) -> dict[str, Any]:
        customer = bundle["customer"]
        travel_state = state.get("travel", {})
        slots = dict(travel_state.get("slots", {}))
        new_slots = dict(nlu.get("slots", {}))
        pending = travel_state.get("pending")
        if pending in ("origin", "destination") and pending not in new_slots:
            only_dest = new_slots.pop("destination", None)
            if only_dest and only_dest != slots.get("origin" if pending == "destination" else "destination"):
                new_slots[pending] = only_dest
        slots.update({k: v for k, v in new_slots.items() if k != "booking_ref"})
        plan = await planner_agent.plan(ctx.case_id, slots, home_city=customer.home_city, lang=lang, db=db)
        if plan["missing"]:
            state["travel"] = {"slots": plan["slots"], "pending": plan["missing"]}
            await save_state(db, customer.id, state)
            return {"status": "needs_input", "reply_text": plan["question"], "missing_slot": plan["missing"],
                    "slots": plan["slots"]}
        flights = await search_agent.search(ctx.case_id, plan["slots"], db)
        ranked = await ranker_agent.rank_and_handoff(
            ctx.case_id, flights, plan["slots"], lang=lang, passenger_name=customer.name,
            elder=trigger.elder_mode, db=db)
        state.pop("travel", None)
        await save_state(db, customer.id, state)
        facts_pool.append(ranked["facts"])
        return {"status": ranked["status"], "reply_text": ranked["text"], "roadmap": plan["roadmap"],
                "slots": plan["slots"], "top_options": ranked.get("options", []),
                "recommended": ranked.get("recommended"), "booking_summary": ranked.get("booking_summary"),
                "handoff_ready": ranked.get("booking_summary") is not None}

    # ------------------------------------------------------------------ fallbacks
    async def _unknown(self, trigger, bundle, ctx, db, lang, state) -> dict[str, Any]:
        """Templates first; after repeated misunderstanding hand to the human queue (never silent)."""
        state["unknown_count"] = int(state.get("unknown_count", 0)) + 1
        await save_state(db, trigger.subject_id, state)
        if trigger.subject_type == "merchant" and state["unknown_count"] >= get_settings().UNKNOWN_TURNS_BEFORE_HUMAN:
            state["unknown_count"] = 0
            await save_state(db, trigger.subject_id, state)
            return await self._human_queue(trigger, bundle, ctx, db, "not_understood", lang)
        return {"status": "needs_input", "reply_text": t("clarify.care", lang)}

    async def _human_queue(self, trigger, bundle, ctx, db, reason_code, lang, key="degraded.human_queue"):
        if trigger.subject_type != "merchant":
            return {"status": "needs_input", "reply_text": t("travel.ask_destination", lang)}
        h = await handoff_agent.escalate(ctx.case_id, db, merchant_id=trigger.subject_id, findings=[],
                                         reason=reason_code, reason_code=reason_code, language=lang,
                                         actor_id=trigger.actor_id, user_message=trigger.message)
        return {"status": "escalated", "reply_text": t(key, lang, ticket_id=h["ticket_id"]),
                "escalation": {"ticket_id": h["ticket_id"], "reused": h["reused"]}}

    async def _step_pulse(self, ctx, db, tool, payload) -> None:
        await trace_bus.publish_step(case_id=ctx.case_id, agent="pulse", tool=tool, input_data={},
                                     output_data={"chars": len(payload["text"])}, confidence=1.0, db=db)

    # ------------------------------------------------------------------ finalize
    async def _finalize(self, trigger, ctx, db, result, facts_pool, start) -> dict[str, Any]:
        reply = result.get("reply_text", "")
        for key in ("escalation", "loan_request", "booking", "booking_summary"):
            if isinstance(result.get(key), dict):
                facts_pool.append(result[key])  # ids created by tools in this turn are facts too
        if not result.get("cache_hit"):
            ok, bad = number_validator.validate(reply, facts_pool)
            if not ok:  # R1 last line of defence
                logger.error("R1 violation in final reply (case %s): %s", ctx.case_id, bad)
                result["validator_violations"] = list(result.get("validator_violations", [])) + [
                    {"code": "final_reply", "numbers": sorted(bad)}]
                result["reply_text"] = t("clarify.care", ctx.language)
        duration = (time.perf_counter() - start) * 1000
        checkup_row = result.pop("_checkup_row", None)
        if checkup_row is not None:
            checkup_row.tier, checkup_row.llm_calls = ctx.tier, ctx.llm_calls
            checkup_row.tokens, checkup_row.cost_inr, checkup_row.duration_ms = ctx.tokens, ctx.cost_inr, duration
        await record_usage(db, user_id=trigger.subject_id, actor_id=trigger.actor_id, session_id=trigger.session_id,
                           case_id=ctx.case_id, kind="request", request_type=trigger.request_type,
                           channel=trigger.channel, tier=ctx.tier, tokens=ctx.tokens, cost_inr=ctx.cost_inr,
                           duration_ms=duration, outcome=result.get("status"))
        await trace_bus.publish_step(
            case_id=ctx.case_id, agent="captain", tool="finalize_response",
            input_data={"intent": result.get("intent"), "channel": trigger.channel,
                        "request_type": trigger.request_type},
            output_data={"status": result.get("status"), "chars": len(result.get("reply_text", ""))},
            confidence=1.0, db=db, tier=ctx.tier, tokens=ctx.tokens, cost_inr=round(ctx.cost_inr, 6),
            latency_ms=duration,
        )
        result["language"] = ctx.language
        return {"case_id": ctx.case_id, "channel": trigger.channel, **result,
                "degraded": ctx.degraded, "degrade_reasons": ctx.degrade_reasons,
                "cost": ctx.cost_summary() | {"duration_ms": round(duration, 1)}}


def listener_lang(text: str) -> str | None:
    from app.nlu.rules import detect_language
    return detect_language(text) if normalize(text) else None


captain_agent = CaptainAgent()
