# Saarthi frontend

React 18 + Vite + TypeScript + Tailwind + Zustand + lucide-react + recharts. Integrates with the
existing Saarthi backend (`/api/v1`, `/ws/*`) as-is. All money, EMI, scores and dates are displayed
exactly as the backend returns them.

## Run (Windows, from the repo root)

```bash
# 1. Backend (existing app, unchanged). Use a DB created with the current schema:
set DATABASE_URL=sqlite+aiosqlite:///./saarthi_v1.db
.venv\Scripts\python.exe scripts\seed.py --reset          # once (SIMULATED data)
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Frontend
cd frontend
npm install
npm run dev                                                # http://localhost:5173
```

Optional: `npm run eval:export` refreshes `public/eval-results.json` for `/eval` by running the
backend's own `eval/run_eval.py` offline (backend files are not modified).

## Environment (`frontend/.env`)

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL |
| `VITE_WS_URL` | `ws://localhost:8000` | Backend WebSocket base |
| `VITE_USE_MOCKS` | `false` | `true` = fully offline demo (no backend); tabs share state |
| `VITE_DEMO_MODE` | `true` | Presenter shortcuts on `/stage` |

The backend's CORS allows `http://localhost:5173`. For a phone/tablet on the LAN, open
`http://<laptop-ip>:5173` and set `VITE_API_URL`/`VITE_WS_URL` to the laptop IP, and add that
origin to the backend's `ALLOWED_CORS_ORIGINS` env var.

## Routes

| Route | Screen |
|---|---|
| `/` | Launcher, connection status, reset demo |
| `/stage` | Demo stage: phone (Ramesh ⇄ Arjun) + Soundbox + crew/trace/escalations. Keys 1–8, K, R, T |
| `/merchant` | Ramesh's chat: check-up buttons, chat, voice, cards, consent-first offer, EMI → human approval |
| `/soundbox` | Soundbox simulator: buttons, chime + spoken answer, LED/waveform, status |
| `/console` | Ops console: cases, glass-box trace, escalation queue + drawer (save as playbook), loan approvals, kill switch, charts, playbooks, ranking formula, audit |
| `/inject` | Tablet panel: set up a scenario then simulate the user's own trigger |
| `/travel` | Arjun / Meena Aunty (elder mode) / Priya: slots, one question at a time, roadmap, 3 labelled options, summary, sandbox payment |
| `/eval` | Eval dashboard from the backend's eval output |

## Notes on backend differences from the frontend spec

The spec proposed some endpoints that the backend does not have; the UI adapts instead of
inventing them:

- No `/events/inject`: inject buttons call `/demo/scenario/{name}` then `/demo/trigger/{name}` (on-demand by design).
- No `/cases` or `/cases/{id}/trace`: the case feed and trace are built live from `/ws/trace` events.
- No `/eval/results`: `/eval` reads `public/eval-results.json` exported from the backend's eval.
- No escalation-rate series endpoint: the learning chart plots real repeat-case outcomes observed in the session.
- Chat replies are returned synchronously by `POST /chat` (not streamed); cross-tab sync uses `BroadcastChannel`.
- Booking summary exists only for the recommended option (backend design); the payment screen is a sandbox.
