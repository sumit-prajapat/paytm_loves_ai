# Saarthi on-demand API: curl examples (SIMULATED DATA)

Every call below is a USER trigger (R11). Base URL `http://localhost:8000/api/v1`.

```bash
B=http://localhost:8000/api/v1
TOKEN=$(curl -s -X POST $B/auth/demo-token -H 'Content-Type: application/json' -d '{"role":"merchant"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
OPS=$(curl -s -X POST $B/auth/demo-token -H 'Content-Type: application/json' -d '{"role":"ops_agent"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Ramesh presses "Check my settlement" (Tier 0, no LLM)
curl -s -X POST $B/checkups -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"scope":"settlement"}'

# Same question by chat (Hinglish)
curl -s -X POST $B/chat -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"message":"Aaj ka settlement kam kyun aaya?"}'

# Soundbox button press -> spoken answer (audio_url) + push on /ws/merchant/m_ramesh
curl -s -X POST $B/soundbox/soundbox_ramesh_01/ask -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"button":"settlement"}'

# "Raise an issue": check-up first, ticket only if unresolved or insist=true
curl -s -X POST $B/issues -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"scope":"all","insist":false}'

# Morning pulse / festival advice (on request only)
curl -s "$B/pulse/m_ramesh?audio=true" -H "Authorization: Bearer $TOKEN"
curl -s "$B/advice/m_ramesh?topic=festival" -H "Authorization: Bearer $TOKEN"

# Demo: set up the world (data only), then simulate the user's button press
curl -s -X POST $B/demo/scenario/soundbox_offline -H "Authorization: Bearer $OPS"
curl -s -X POST $B/demo/trigger/soundbox_offline -H "Authorization: Bearer $OPS" -H 'Content-Type: application/json' -d '{"channel":"soundbox"}'
curl -s -X POST $B/demo/reset -H "Authorization: Bearer $OPS"

# Ops console
curl -s $B/escalations -H "Authorization: Bearer $OPS"
curl -s $B/metrics -H "Authorization: Bearer $OPS"
```
