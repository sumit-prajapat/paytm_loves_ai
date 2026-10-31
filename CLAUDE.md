# CLAUDE.md — Saarthi backend (project memory)

Saarthi = multi-agent AI teammate for Indian users (Hindi / Hinglish / English, voice-first).
Paytm AI Hackathon, Track 3. Backend only; a teammate builds the frontend.
- **Saarthi Care** (merchant): user-triggered check-ups for settlement gap, Soundbox, payments/refunds,
  chargebacks (escalate), consent-first loans, playbook learning. Hero: Ramesh (m_ramesh), gap 1800 = 1200 + 600.
- **Saarthi Travel** (traveller): planner → search (±1 day) → deterministic ranker → Guardian → HUMAN review & pay.

## Architecture map
| Path | Responsibility |
|---|---|
| `app/main.py` | App, middleware, error handlers; routers under `/api/v1`, probes `/health*`, WS `/ws/*` |
| `app/agents/captain.py` | **Only orchestrator entry point.** `CaptainAgent.handle(Trigger, db)`; no event/proactive path |
| `app/agents/*` | listener (Tier 0→1), context, diagnostician (+playbooks), guardian (action classes), action (templates + R1), handoff (dossier, Tier 2 summary), offer (consent), planner/search/ranker (travel) |
| `app/nlu/rules.py` | Tier 0 intent + slots (Devanagari, Hinglish, English, typos, word-boundary matching) |
| `app/llm/gateway.py` | The ONLY path to an LLM: budgets, classification cache, cost accounting, visible degrade |
| `app/i18n/` | `locales/<lang>.json` templates (hi, hinglish, en; add a file for more), `numbers.py` (₹ format, paise, spoken numbers) |
| `app/services/` | checkup_service (per-merchant diagnostics), usage_service (quotas/budget), metrics_service (DB-derived), pulse_service, travel_service, loan, playbook, audit (hash chain), kill_switch, voice_service, audio_store (signed URLs) |
| `app/api/` | checkups, issues, soundbox, pulse/advice, chat, voice, travel, loans, escalations, playbooks, demo, audio, … |
| `app/ops/housekeeping.py` | The ONLY scheduler: expire audio files, prune memory cache. Must never touch user data |
| `app/db/` | models (incl. checkups, usage_events, offer_consents, conversation_states, travel_bookings), seed, heroes (idempotent + reset) |
| `app/trace/bus.py` | agent_runs + `/ws/trace`; enforces R3 tool allow-list + per-turn tool budget; masks PII |
| `tests/` | 108 tests: golden scenarios from user triggers, R11, R12, NLU/validator, security P0s |
| `eval/run_eval.py` | 40 cases through the real Captain on a temp DB; computed PASS/FAIL |

## Rules (verify in CODE)
R1 numbers only from tools; validator checks replies vs tool facts (never vs the reply). R2 Guardian on every action.
R3 payment / loan approval / refund issuance / booking confirm = human-only (runtime allow-list + Guardian block).
R4 every step → agent_runs + audit (chained) + `/ws/trace`. R5 kill switch: reads continue, mutations escalate.
R6 max one offer per interaction, cooldown, decline persisted forever. R7 never accept PIN/OTP/password/card.
R8 simulated data. R9 adapters + offline fallback; failures are visible, never silent. R10 stop-and-ask → NEEDS_FROM_USER.md.
**R11** nothing runs until the user (or audited ops agent) triggers it; no per-user/fleet jobs, watchers or pushes.
**R12** Tier 0 (rules + templates) → Tier 1 (cheap LLM: intent/slots) → Tier 2 (summaries); quotas, cooldown,
caches, global budget, cost in agent_runs/usage_events/metrics.

## How to run (Windows Git Bash; venv `.venv`, Python 3.14)
```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/seed.py --reset        # required after schema changes (simulated data)
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
.venv/Scripts/python.exe -m pytest -q                   # offline by design (conftest blanks keys)
.venv/Scripts/python.exe eval/run_eval.py               # offline, temp DB, writes eval/report.md
```
Offline server: prefix `GEMINI_API_KEY= SARVAM_API_KEY= LLM_PROVIDER=mock TTS_PROVIDER=mock`.
Scratch DB: `DATABASE_URL=sqlite+aiosqlite:///<path>/x.db`. Windows console: `PYTHONIOENCODING=utf-8`.
Demo tokens: `POST /api/v1/auth/demo-token {"role": merchant|traveller|ops_agent|admin, "target_id"?}` (DEMO_MODE).
Users: merchant_ramesh, merchant_sunita, merchant_gupta (m_disputed), traveller_arjun, traveller_meena,
ops_agent_1 (`DemoPass@123`), admin_user (`AdminPass@123`). Demo: `/api/v1/demo/scenario/{name}` → `/demo/trigger/{name}`.

## Conventions
- New user-facing text = a template key in ALL locale files (test enforces identical keys); numbers only via placeholders.
- Agents emit steps with allow-listed tool names (`AGENT_ALLOW_LISTS` in `app/core/security.py`).
- Services flush; the Captain/route commits. Audit writes only via `record_audit_log`.
- Never print `.env` values (it holds real keys). Commits end with the Co-Authored-By line.

## Phase status
- Step 0/A audit: done (`AUDIT_REPORT.md`). **Step B: DONE** (R11 refactor + R12 + P0 security, 108 tests green,
  eval 82.5%, see "Before / after: Step B"). Waiting for user "GO" for Step C.
- Next: Step C (strengthen + red-team), D (features, eval 50+ relabelled), E (contract), F (ops/scale), G (handoff).
