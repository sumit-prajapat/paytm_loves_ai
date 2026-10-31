# Assumptions log

Safest-choice assumptions made while working. Each one can be overridden; tell us if any is wrong.

| Date | Step | Assumption | Why it is the safe choice |
|---|---|---|---|
| 2026-10-31 | A | The audit ran offline (`GEMINI_API_KEY`, `SARVAM_API_KEY` blanked via env, `TTS_PROVIDER=mock`) against a scratch SQLite DB, not `./saarthi.db`. | No cost or data sent to third parties; the user's DB is untouched; results are reproducible. |
| 2026-10-31 | A | One probe call each to Gemini and Sarvam was acceptable, to verify the "operational" claim in `NEEDS_FROM_USER.md`. | Minimal non-sensitive payload; key never printed; needed to report the true status. |
| 2026-10-31 | A | Travel shortlists stay allowed while the kill switch is on. | They are read-only and end in a human review; nothing moves money. |
| 2026-10-31 | A | `eval/report.md` is a generated artifact; regenerating it during the audit is acceptable. | It is rewritten by every eval run; the previous numbers are quoted in `AUDIT_REPORT.md`. |
| 2026-10-31 | B | "go and build it" was taken as GO for Step B, including `git init` (requested in my Step A list) and the four P0 security fixes I proposed. | Needed for the requested small commits; local and reversible. |
| 2026-10-31 | B | Placeholder costs: Tier 1 ₹0.01 / 1K tokens, Tier 2 ₹0.08 / 1K tokens, support ticket ₹180 (config: `LLM_TIER1_INR_PER_1K_TOKENS`, `LLM_TIER2_INR_PER_1K_TOKENS`, `SUPPORT_COST_PER_TICKET_INR`). MockLLM calls cost ₹0 but still count as LLM calls. | Clearly labelled, configurable, replaced when real prices are given. |
| 2026-10-31 | B | Quotas: 30 check-ups / merchant / day, 60 s cooldown for identical re-checks, 10 min result cache, 40 LLM calls and 40K tokens / user / day, 15 LLM calls / session, ₹2000 global LLM budget / day. | Generous for a demo, cheap at scale; all configurable. |
| 2026-10-31 | B | A Soundbox answer never includes a loan offer (spoken upsell on a shop speaker is intrusive). Offers appear only in app/chat/voice after a resolved check-up. | Safest reading of consent-first selling. |
| 2026-10-31 | B | Under the kill switch, explanations/check-ups (reads) and ticket creation continue; playbook auto-resolutions and loan applications escalate to a human. Travel shortlists continue (read-only). | Matches R5 "reads allowed, actions escalate". |
| 2026-10-31 | B | Reply language: explicit request language, else the language of the user's message, else profile language. Marathi profile falls back to Hindi templates until `mr.json` exists. | Users get answers in the language they spoke. |
| 2026-10-31 | B | Learned playbooks may only use safe actions that never move money (`explain_breakdown`, `guide_charger`, `guide_restart`, `request_evidence_upload`). Overdue refunds always go to a human. | R3; prevents a learned rule from issuing refunds. |
| 2026-10-31 | B | Old eval labels were kept unchanged even where they contradict the spec (overdue refund, missing travel slots); they will be relabelled with justification in Step D. | Never edit labels to make numbers look better without saying so. |
