#!/usr/bin/env bash
# Saarthi Live Chaos & Scenario Injector for Hackathon Stage Demo

BASE_URL="http://localhost:8000"

echo "============================================================"
echo "SAARTHI MULTI-AGENT DEMO SCENARIO INJECTOR"
echo "============================================================"
echo "1. Beat 1: Proactive Settlement Short (Ramesh)"
curl -s -X POST "$BASE_URL/events/inject" \
     -H "Content-Type: application/json" \
     -d '{"type": "settlement_short", "merchant_id": "m_ramesh"}' | grep -o '"reply_text":[^,]*'

echo -e "\n\n2. Beat 2: Proactive Soundbox Offline (Low Battery 12%)"
curl -s -X POST "$BASE_URL/events/inject" \
     -H "Content-Type: application/json" \
     -d '{"type": "soundbox_offline", "merchant_id": "m_ramesh"}' | grep -o '"reply_text":[^,]*'

echo -e "\n\n3. Beat 3: Consumer Travel Request (Delhi to Mumbai, fast & cheap)"
curl -s -X POST "$BASE_URL/chat" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "c_arjun", "role": "traveller", "message": "Delhi se Mumbai kal shaam ka flight, sasta aur jaldi"}' | grep -o '"status":[^,]*'

echo -e "\n\n4. Beat 4: Risky Disputed Chargeback (INR 6,500 > 5,000 threshold -> Escalation)"
curl -s -X POST "$BASE_URL/events/inject" \
     -H "Content-Type: application/json" \
     -d '{"type": "chargeback_dispute", "merchant_id": "m_disputed"}' | grep -o '"status":[^,]*'

echo -e "\n\n5. Beat 5: Live Operational Metrics Dashboard"
curl -s "$BASE_URL/metrics"

echo -e "\n============================================================"
echo "DEMO SCENARIOS INJECTED SUCCESSFULLY!"
