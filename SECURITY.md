# Security & Threat Architecture: Saarthi AI Teammate

> **Notice & Compliance Disclaimer:**  
> This application is built as a **hackathon-grade, production-minded demonstration** for the Paytm AI Hackathon. All data, merchant accounts, transaction histories, Soundbox events, and flight inventories are simulated. This document **does not claim formal PCI-DSS, RBI Master Direction, or production compliance**. Rather, it demonstrates fintech-grade defense-in-depth principles implemented in code.

---

## 1. Threat Model

Saarthi serves as an autonomous AI teammate interacting with kirana shopkeepers (merchants) and everyday travellers through voice and chat interfaces. Our threat model accounts for four core threat actors:

1. **The Curious or Malicious User:** Attempts to manipulate requests, tamper with URL parameters or payload IDs (Insecure Direct Object Reference - IDOR) to inspect another merchant’s revenue, settlements, or customer transactions.
2. **The Hackathon Judge / Security Evaluator:** Probes API endpoints, attempts unauthenticated access, triggers high-frequency requests to test rate limiting, or uploads malformed binary streams to corrupt audio processing.
3. **Prompt Injection & Adversarial Payloads:** Submits adversarial utterances ("Ignore previous instructions", "Act as root", "Dump system prompt") via Hindi/Hinglish chat, transcribed voice, or injected webhook events to hijack agent behavior or leak internal instructions.
4. **Accidental Credential & Data Leaks:** Merchants accidentally pasting UPI PINs, bank OTPs, credit card numbers, or Aadhaar details into chat/voice queries, risking exposure in database logs, WebSocket traces, or third-party LLM calls.

---

## 2. Controls Implemented

### A. Authentication & Role-Based Access Control (RBAC)
- **JWT Cryptography:** Issues short-lived access tokens (60 minutes) and refresh tokens (7 days) signed with HMAC-SHA256 (`HS256`).
- **Four Dedicated Roles:**
  - `merchant`: Restricted strictly to their own merchant store records, Soundbox diagnostics, tickets, and pulse broadcasts.
  - `traveller`: Restricted strictly to their personal travel roadmap and search sessions.
  - `ops_agent`: Authorized to review human escalations, resolve tickets, and approve/reject loan requests.
  - `admin`: Authorized for system kill-switch control, audit trail export, and cryptographic chain verification.
- **Seeded Demo Accounts & Shortcut:**
  - Demo accounts for all four roles pre-seeded with bcrypt-hashed credentials (`DemoPass@123` / `AdminPass@123`).
  - `POST /auth/demo-token` provides instant evaluation tokens for judges when `DEMO_MODE=true`; automatically disabled with HTTP 403 when `DEMO_MODE=false`.
- **WebSocket Security:**
  - `/ws/trace` and `/ws/console` require `admin` or `ops_agent` credentials on connection.
  - `/ws/merchant/{id}` verifies merchant ownership and closes rogue sessions with WebSocket code `4003` (Forbidden).

### B. Object-Level Authorization (IDOR Defense)
- **Mandatory Ownership Checks:** Evaluated in FastAPI dependency layer before business logic executes. A merchant token for `m_ramesh` calling `GET /settlements/m_sunita` or `GET /merchants/m_sunita` is immediately terminated with `HTTP 403 Forbidden (IDOR Violation)`.
- **Operator Separation:** The autonomous agent and merchant tokens are strictly blocked from calling `/control/kill-switch`, `/escalations/resolve`, or `/loans/requests/approve`.

### C. Agent & Prompt Injection Hardening
- **Code-Level Tool Allow-Lists:** Every specialized sub-agent operates under a hard allow-list defined in Python code. The Captain agent cannot invoke tools outside an agent's registered boundary.
- **Strict Financial Tool Denylist (Rule R3):**
  - Code-level denylist irrevocably blocks: `confirm_payment`, `process_payment`, `execute_charge`, `approve_loan`, `issue_refund`, and `execute_refund`.
  - The AI teammate can explain, calculate, and package recommendations, but final execution requires human-in-the-loop authorization.
- **Adversarial Pattern Neutralization:** Regular expression filters detect jailbreak patterns (`ignore previous instructions`, `act as admin`, `reveal system prompt`, `drop table`). Injection attempts are logged as security audit events and returned with a polite refusal.
- **Sensitive Data & Scam Guard (Rule R7):**
  - Scans user inputs for 4-to-6 digit PINs, OTPs, 10-digit Indian phone numbers, 12-digit Aadhaar patterns, and 16-digit card numbers.
  - When detected, the request is immediately refused with a fraud warning: *"Paytm ya Saarthi kabhi bhi aapse apna PIN/OTP nahi maangta"*.
  - All credentials are redacted (`[REDACTED_CREDENTIAL]`) before persisting to audit logs or passing to language models.
- **Deterministic Number Grounding (Rule R1):** Output text is validated by `NumberValidator` against verified deterministic tool outputs. Any ungrounded financial figure halts the turn and escalates to a human operator.
- **Output Sanitization:** Outbound responses are filtered against internal stack traces, API keys (`AIza...`, `sk-...`, `gsk_...`), and internal database connection strings.

### D. Action Safety & Idempotency
- **Idempotency Keys:** Mutating endpoints (`POST /tickets`, `POST /loans/requests`) accept an `X-Idempotency-Key` header. Duplicate submissions retrieve the cached payload without creating duplicate database entities.
- **Two-Step Financial Confirmation:** Ops actions with financial commitments (approving a loan) require an explicit confirmation token (`confirm=True` or `confirm_token`).
- **Runaway Loop Caps:** Enforces per-user action limits (maximum 15 support tickets per hour) to halt infinite automation loops.
- **Redundant Kill-Switch Integration:** The autonomous kill switch is checked directly in the service mutation layer as well as the Guardian agent.

### E. API Protection & Network Hardening
- **Rate Limiting:** Sliding-window per-IP limiter restricts high-risk endpoints (`/chat`, `/voice/*`, `/auth/login`, `/events/inject`) to 20 requests per minute, and standard endpoints to 60 requests per minute.
- **Audio Validation:**
  - Enforces a 5 MB maximum file upload limit.
  - Restricts MIME types to `audio/wav`, `audio/mpeg`, `audio/ogg`, `audio/webm`.
  - Performs magic-byte inspection (e.g. verifying `RIFF...WAVE` headers) to stop executable masquerading.
  - Uploaded audio is processed in isolated temporary storage and immediately unlinked in a `finally` block.
- **Security Headers:** Outgoing responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, and `Strict-Transport-Security`.
- **Sanitized Error Responses:** Uncaught exceptions return standard error JSON with a tracking `correlation_id`. Full tracebacks and SQL errors are logged server-side only.

### F. Tamper-Evident Cryptographic Audit Chaining
- Every audit log row computes an immutable SHA-256 hash chaining the previous row’s hash with current event data:
  $$\text{Hash}_n = \text{SHA256}(\text{Hash}_{n-1} \parallel \text{CaseID} \parallel \text{Actor} \parallel \text{Action} \parallel \text{Detail} \parallel \text{Timestamp})$$
- `GET /audit/verify` (Admin only) scans the database and mathematically verifies that zero rows have been altered, deleted, or injected out of sequence.
- `GET /audit/export` (Admin only) exports the cryptographically signed ledger for compliance reviews.

---

## 3. Known Limitations & Production Roadmap

While Saarthi demonstrates production-minded security architecture on simulated data, transitioning to live commercial banking requires the following enterprise infrastructure:

| Domain | Hackathon Implementation (Current) | Production Requirement (Target) |
| :--- | :--- | :--- |
| **Secrets Management** | Environment variables (`.env`) with startup validation | Dedicated Cloud KMS / HashiCorp Vault / AWS Secrets Manager with automatic secret rotation |
| **Edge Defense** | In-memory sliding-window rate limiting | Enterprise Cloud WAF (Cloudflare / AWS Shield) with automated DDoS mitigation and bot management |
| **Identity & KYC** | Seeded bcrypt user database & demo JWTs | RBI-compliant Aadhaar e-KYC (DigiLocker / UIDAI), hardware OTP SMS gateway, device binding (SIM binding) |
| **Payment Security** | Mock payment links and consent-first loan applications | NPCI Unified Payments Interface (UPI) integration, PCI-DSS Level 1 certified vault, HSM for card tokenization |
| **LLM Guardrails** | In-code regex filters and Pydantic schema validation | Dedicated LLM firewall (e.g. NeMo Guardrails / Lakera Guard) with vector embeddings for semantic injection detection |
| **Data Retention** | Local SQLite database with hot-backup script | Cloud Spanner / PostgreSQL with multi-region replication, Point-In-Time-Recovery (PITR), and automated cold archiving |
