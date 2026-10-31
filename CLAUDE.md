# CLAUDE.md — Saarthi backend (project memory)

Saarthi = multi-agent AI teammate for Indian users (Hindi / Hinglish / English, voice-first).
Paytm AI Hackathon, Track 3 (Autonomous AI Teammates). Backend only; a teammate builds the frontend.
Two faces on one agent framework:
- **Saarthi Care** (merchant): settlement gap, Soundbox offline, payment failed / refund, chargeback
  escalation, consent-first loan offers, playbook learning. Hero: Ramesh (m_ramesh), gap 1800 = 1200 refund + 600 fees.
- **Saarthi Travel** (consumer): planner → parallel search → deterministic ranker → guardian → HUMAN review & pay.

## Architecture map
| Path | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, middleware, exception handlers, router registration, lifespan |
| `app/config.py` | pydantic-settings `Settings` (reads `.env`) |
| `app/api/*` | HTTP + WS routers (chat, voice, pulse, travel, loans, escalations, control, audit, metrics, ws) |
| `app/agents/*` | Captain (orchestrator), Listener, Context, Diagnostician, Guardian, Action, Handoff, Offer, Planner, Search, Ranker; `router.py` (unused) |
| `app/services/*` | Deterministic tools: settlement, device, loan/EMI, travel scoring, playbooks, templates, number validator, audit chain, kill switch, metrics |
| `app/adapters/*` | External deps behind adapters: llm (Gemini/Mock), stt (Sarvam/Mock), tts (edge-tts/Mock), flights (seeded DB), payments (mock link), notify (in-app WS bus), weather, holidays |
| `app/rag/*` | Offline BM25 policy retriever + policy corpus |
| `app/events/*` | APScheduler fleet scan + event queue + rules (**violates R11; to be removed in Step B**) |
| `app/trace/bus.py` | Writes every agent step to `agent_runs` + broadcasts on `/ws/trace` |
| `app/core/*` | JWT auth/RBAC/IDOR deps, rate limiter, correlation IDs, PII masking, injection detection, idempotency |
| `app/db/*` | SQLAlchemy models, session, seed + dataset loaders (airports, routes, Kaggle flights, PaySim) |
| `tests/` | pytest (in-memory SQLite). `eval/` 40 labeled cases + `run_eval.py`. `scripts/` seed, backup, demo, security demo |

## Non-negotiable rules (verify in CODE, not prompts)
- R1 numbers only from deterministic tools; validator rejects any number not in that turn's tool results.
- R2 Guardian reviews every action before execution (allow / block / escalate).
- R3 payments, loan approvals, refund issuance are HUMAN-ONLY (code-level denylist).
- R4 every agent step + tool call → `agent_runs` + `audit_log` + `/ws/trace`.
- R5 global kill switch: reads allowed, actions → escalate to human.
- R6 consent-first selling: max ONE offer per interaction, stop on decline, log refusal.
- R7 never accept/store PIN / OTP / password / card numbers.
- R8 all data simulated. R9 every external dep behind an adapter with mock fallback; runs fully offline.
- R10 stop-and-ask: external needs → `/NEEDS_FROM_USER.md`; never invent keys or fake external calls.
- R11 ON-DEMAND ONLY: nothing runs for a user until that user (or an authorized ops agent) triggers it.
  No per-user schedulers/loops/watchers/pushes. Scheduler only for housekeeping that touches no user data.
- R12 cost scales with requests: Tier 0 (no LLM, templates) → Tier 1 (cheap LLM: intent/slots) → Tier 2
  (strong LLM: ambiguity, escalation summaries, travel nuance). Quotas, cooldowns, caching, budget guard,
  per-request cost accounting (tier, tokens, INR) in `agent_runs` and business metrics.

## How to run (Windows, Git Bash; venv already at `.venv`, Python 3.14)
```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/seed.py                 # seeds ./saarthi.db
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
.venv/Scripts/python.exe -m pytest -q                    # 31 tests
.venv/Scripts/python.exe eval/run_eval.py                # overwrites eval/report.md
```
**Offline / audit mode** (no external calls, no cost): prefix with
`GEMINI_API_KEY= SARVAM_API_KEY= TTS_PROVIDER=mock` (env vars override `.env`).
Use a scratch DB via `DATABASE_URL=sqlite+aiosqlite:///<path>/audit.db` to avoid mutating `saarthi.db`.
Demo creds: `POST /auth/demo-token {"role": merchant|traveller|ops_agent|admin, "target_id"?}` (DEMO_MODE only);
users `merchant_ramesh`, `merchant_sunita`, `traveller_arjun`, `ops_agent_1` (`DemoPass@123`), `admin_user` (`AdminPass@123`).

## Conventions
- Async SQLAlchemy 2.x; agents return `AgentEnvelope` (agent, status, result, confidence, evidence, next, language, latency_ms).
- All money/dates in replies come from services + `app/services/templates.py`; LLM only classifies/explains.
- Never print `.env` values. `.env` holds real GEMINI/SARVAM keys (both currently non-working, see AUDIT_REPORT).
- Windows console is cp1252: set `PYTHONIOENCODING=utf-8` when printing ₹ / Devanagari.
- Not a git repo yet (see NEEDS_FROM_USER). Commits planned per logical change once initialised.

## Phase status
- Phases 1–7: exist, but the audit (`/AUDIT_REPORT.md`, 2026-10-31) found many PARTIAL/BROKEN items.
- **Step 0 + Step A: DONE (audit only, no app code changed).** Waiting for user "GO" for Step B
  (on-demand refactor + R12 cost controls). Steps C–G pending.
