# Saarthi: Multi-Agent AI Teammate for Bharat
**Paytm AI Hackathon (Track 3: Autonomous AI Teammates)**

> *"A chatbot answers questions. A teammate closes the loop."*

Saarthi is an autonomous, multi-agent AI teammate designed for Indian merchants and consumers:
1. **Saarthi Care (Merchant Side):** Proactive zero-ticket support, Soundbox diagnostics, and consent-first loan offers. Hero: *Ramesh*, Kirana owner in Delhi.
2. **Saarthi Travel (Consumer Side):** Multi-agent concierge that builds visible roadmaps, searches flights in parallel, applies transparent scoring, and hands over to the human to review and pay. Hero: *Arjun* & *Meena Aunty*.

---

## Architecture

```mermaid
graph TD
    User([User: Hindi / Hinglish / Voice]) --> Gateway[FastAPI Gateway]
    Gateway --> Listener[Listener Agent: Language & Intent]
    Listener --> Guardian{Guardian Safety & Policy Engine}
    
    subgraph Multi-Agent Crew
        Guardian -->|Care Flow| Context[Context Agent]
        Context --> Diagnostician[Diagnostician + RAG + Playbooks]
        Diagnostician --> Action[Action Agent: Safe Zero-Ticket Fix]
        Action --> Offer[Offer Agent: Consent-First Loan]
        
        Guardian -->|Travel Flow| Planner[Planner: Roadmap Agent]
        Planner --> Search[Search Agent: Parallel Inventory]
        Search --> Ranker[Ranker & Recommender]
        Ranker --> HandoffUser[Human Review & Pay Handoff]
        
        Guardian -->|Risky / Dispute / Kill Switch| HandoffOps[Handoff Agent: Ops Console]
    end
    
    Action --> TraceBus[Trace Bus & Observability]
    HandoffOps --> TraceBus
    TraceBus --> GlassBox[Glass-Box Trace: /ws/trace]
    TraceBus --> DB[(SQLite Database)]
    
    OpsConsole[Human Ops Console] -->|Resolve & Save Rule| Learner[Learner: Continuous Playbooks]
    Learner --> Diagnostician
```

---

## Non-Negotiable Safety Rules (Enforced in Code)
- **R1: Strict Number Grounding:** All financial figures (amounts, fees, dates, prices, EMI) come strictly from deterministic tools. Response text is validated; responses with ungrounded numbers are rejected.
- **R2: Pre-Execution Guardian:** Every proposed agent action is inspected by the Guardian before execution.
- **R3: Human-in-the-Loop Financials:** Payments, loan approvals, and refunds are human-only. The travel concierge ends at a pre-filled Review & Pay link; the agent never confirms payments or enters PINs.
- **R4: Complete Traceability:** Every step is written to `agent_runs` and `audit_log`, and streamed over WebSocket.
- **R5: Instant Kill Switch:** Global kill switch pauses autonomous mutations and downgrades actions to human escalation.
- **R6: Consent-First Offers:** At most ONE loan offer per interaction, only after resolution, and stops immediately if declined.
- **R7: Zero PIN/OTP Tolerance:** Saarthi never requests or accepts PINs, passwords, or OTPs.

---

## Quickstart (Under 10 Commands)

```bash
# 1. Clone & Enter directory
cd saarthi

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Seed database (Merchants, 121 Indian airports, Kaggle flights, policies)
python scripts/seed.py

# 6. Run test suite (18 unit and golden tests)
pytest -v

# 7. Run evaluation suite (40 labeled cases across all scenarios)
python eval/run_eval.py

# 8. Start development server
uvicorn app.main:app --reload --port 8000
```

---

## Running Offline vs Real Providers

- **Offline Mode (Default, Zero Config):**
  Runs 100% locally with `DEMO_MODE=true` in `.env`. Uses `MockLLM` with scripted deterministic scenarios, local `edge-tts` Hindi neural voice, seeded SQLite flight inventories, and local BM25 RAG. No external accounts or paid API keys needed.
- **Live Provider Mode:**
  Set `DEMO_MODE=false` in `.env` and add:
  - `GEMINI_API_KEY`: Enables live Google Gemini 1.5 Flash reasoning.
  - `SARVAM_API_KEY`: Enables live Sarvam AI Indic STT.

Check active adapter status anytime at:
```bash
curl http://localhost:8000/health/adapters
```

---

## API Catalog (Every Endpoint)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | System health check and database probe |
| `GET` | `/health/adapters` | Adapter status (active provider vs fallback) |
| `GET` | `/control/state` | Current autonomy state and safety thresholds |
| `POST` | `/control/kill-switch` | Pause or resume global autonomous mutations |
| `POST` | `/chat` | Main conversational endpoint (merchants & travellers) |
| `POST` | `/voice/stt` | Transcribe speech audio to text |
| `POST` | `/voice/tts` | Synthesize text to spoken Indic audio |
| `POST` | `/voice/turn` | Full audio voice turn: STT -> Captain -> TTS |
| `GET` | `/pulse/{merchant_id}` | 20-second Morning Business Pulse (text + audio) |
| `POST` | `/events/inject` | Chaos demo injector (settlement, battery, dispute) |
| `GET` | `/events` | History of injected and scheduled events |
| `GET` | `/merchants/{id}` | Merchant profile, language, and KYC status |
| `GET` | `/transactions` | Filter transaction history by merchant, date, status |
| `GET` | `/settlements/{id}` | Expected vs actual reconciliation & deduction items |
| `GET` | `/refunds/{txn_id}` | Refund status, SLA dates, and bank reference UTR |
| `GET` | `/devices/{id}/status`| Soundbox battery, network, and heartbeat health |
| `POST` | `/tickets` | Raise support or replacement ticket with SLA |
| `POST` | `/notifications` | Dispatch notification to Soundbox, WhatsApp UI, or Push |
| `GET` | `/loans/eligibility/{id}`| Loan eligibility check and limit pre-approval |
| `POST` | `/loans/emi` | Mathematical reducing-balance EMI calculator |
| `POST` | `/loans/requests` | Create loan application (status: `awaiting_approval`) |
| `POST` | `/loans/requests/{id}/approve` | Human operator approves loan in console |
| `POST` | `/loans/requests/{id}/reject` | Human operator rejects loan in console |
| `GET` | `/disputes/{id}` | Chargeback claim details and evidence requirement |
| `POST` | `/playbooks` | Save a resolved escalation as a learned rule |
| `GET` | `/playbooks/match` | Match incoming issue to stored playbooks |
| `GET` | `/escalations` | List open human escalation dossiers |
| `POST` | `/escalations/{id}/resolve` | Resolve escalation and optionally save as playbook |
| `GET` | `/travel/flights/search` | Search domestic flights with multi-agent ranking |
| `GET` | `/travel/airports` | Indian airport lookup by city name or IATA code |
| `POST` | `/travel/booking-summary`| Generate human review & pay handoff object |
| `GET` | `/travel/status/{flight_no}`| Simulated flight delays, gate status, weather |
| `GET` | `/audit` | Immutable audit trail records |
| `GET` | `/metrics` | Live counters: deflection, tickets prevented, savings |
| `WS` | `/ws/trace` | Live glass-box multi-agent execution step stream |
| `WS` | `/ws/merchant/{id}` | Live Soundbox chime broadcasts & merchant chat stream |
| `WS` | `/ws/console` | Live Ops console stream for escalations and metrics |
