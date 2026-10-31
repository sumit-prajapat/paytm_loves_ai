# Saarthi Backend: Demo Beats & cURL Examples

This document provides ready-to-run copy-paste commands for every demo beat in the 3-minute hackathon pitch.

---

## Beat 1: Proactive Zero-Ticket Settlement Short (Soundbox Speaks First)
**Story:** An expected settlement is short by ₹1,800. Saarthi detects it before Ramesh notices, diagnoses ₹1,200 refund + ₹600 fee, speaks it via Soundbox, and keeps ticket count at zero.

```bash
curl -X POST "http://localhost:8000/events/inject" \
     -H "Content-Type: application/json" \
     -d '{"type": "settlement_short", "merchant_id": "m_ramesh"}'
```

---

## Beat 2: Morning Business Pulse (20-Second Audio Overview)
**Story:** Ramesh clicks or opens his store dashboard to hear his morning briefing.

```bash
curl -X GET "http://localhost:8000/pulse/m_ramesh?audio=true"
```

---

## Beat 3: Consent-First Loan Offer & EMI Query
**Story:** After resolution, Ramesh asks: "50,000 chahiye, EMI kitna?"
Saarthi calculates EMI mathematically (₹4,489/month at 14%) and logs the request as `awaiting_approval` for human verification.

```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "m_ramesh", "role": "merchant", "message": "Mujhe 50000 ka loan chahiye, EMI kitna banega?"}'
```

If Ramesh declines ("Nahi chahiye"), Saarthi immediately ceases:
```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "m_ramesh", "role": "merchant", "message": "Nahi chahiye abhi, mat do"}'
```

---

## Beat 4: Multi-Agent Travel Concierge (Consumer Side)
**Story:** Arjun says: "Delhi se Mumbai kal shaam ka flight, sasta aur jaldi".
Planner builds roadmap -> Search queries flights in parallel -> Ranker scores options -> Handoff prepares Review & Pay link (AI never pays).

```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "c_arjun", "role": "traveller", "message": "Delhi se Mumbai kal shaam ka flight, sasta aur jaldi"}'
```

---

## Beat 5: Judge-Triggered Chaos: Risky Chargeback Escalation
**Story:** Judge injects a ₹6,500 dispute. Guardian detects financial impact > ₹5,000 threshold and escalates to human console with complete context.

```bash
curl -X POST "http://localhost:8000/events/inject" \
     -H "Content-Type: application/json" \
     -d '{"type": "chargeback_dispute", "merchant_id": "m_disputed"}'
```

Inspect the Escalation Queue:
```bash
curl -X GET "http://localhost:8000/escalations"
```

---

## Beat 6: Playbook Learning Loop
**Story:** Human supervisor resolves the escalation and clicks "Save as playbook". The next similar case auto-resolves with 0 tickets!

```bash
curl -X POST "http://localhost:8000/escalations/tkt_esc_7701/resolve" \
     -H "Content-Type: application/json" \
     -d '{
       "resolution": "Verified store invoice and CCTV log.",
       "operator_id": "supervisor_priya",
       "save_as_playbook": true,
       "issue_type": "chargeback_dispute",
       "root_cause": "verified_store_slip"
     }'
```

Check matched playbooks:
```bash
curl -X GET "http://localhost:8000/playbooks/match?issue_type=chargeback_dispute"
```

---

## Beat 7: Global Kill Switch (Pause Autonomy)
**Story:** Operator engages the master kill switch to halt all autonomous mutations.

```bash
# Check current state
curl -X GET "http://localhost:8000/control/state"

# Engage Kill Switch
curl -X POST "http://localhost:8000/control/kill-switch" \
     -H "Content-Type: application/json" \
     -d '{"active": true, "reason": "Judge emergency safety drill", "actor": "demo_lead"}'
```

---

## Beat 8: Live Operational Metrics Dashboard
**Story:** Show measurable Track 3 outcomes: tickets prevented, deflection rate, support costs saved in INR.

```bash
curl -X GET "http://localhost:8000/metrics"
```
