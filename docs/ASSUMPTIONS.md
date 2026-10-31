# Assumptions log

Safest-choice assumptions made while working. Each one can be overridden; tell us if any is wrong.

| Date | Step | Assumption | Why it is the safe choice |
|---|---|---|---|
| 2026-10-31 | A | The audit ran offline (`GEMINI_API_KEY`, `SARVAM_API_KEY` blanked via env, `TTS_PROVIDER=mock`) against a scratch SQLite DB, not `./saarthi.db`. | No cost or data sent to third parties; the user's DB is untouched; results are reproducible. |
| 2026-10-31 | A | One probe call each to Gemini and Sarvam was acceptable, to verify the "operational" claim in `NEEDS_FROM_USER.md`. | Minimal non-sensitive payload; key never printed; needed to report the true status. |
| 2026-10-31 | A | Travel shortlists stay allowed while the kill switch is on. | They are read-only and end in a human review; nothing moves money. |
| 2026-10-31 | A | `eval/report.md` is a generated artifact; regenerating it during the audit is acceptable. | It is rewritten by every eval run; the previous numbers are quoted in `AUDIT_REPORT.md`. |
