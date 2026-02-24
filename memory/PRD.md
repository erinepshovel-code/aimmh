# Multi-AI Hub - Product Requirements Document

## Original Problem Statement
Build a user interface for prompting multiple AI models simultaneously. Support GPT, Gemini, Claude (universal key), Grok, DeepSeek, and Perplexity (user keys). Minimalist dark theme optimized for mobile. Advanced research features for EDCM analysis including synthesis, batch prompting, auto-cascade, and Agent Zero integration.

## Architecture

### Backend (FastAPI + MongoDB)
```
/app/backend/
  server.py          # App entry, middleware, router registration
  db.py              # MongoDB connection
  config.py          # JWT config
  models/
    auth.py          # Auth Pydantic models
    chat.py          # Chat/keys Pydantic models
    agent_zero.py    # A0 request models
    edcm.py          # EDCM metrics + A0Config models
  routes/
    auth.py          # Register, login, Google OAuth, logout, /me
    keys.py          # API key CRUD
    chat.py          # Chat streaming (with response_time_ms), feedback, conversations, catchup
    export.py        # JSON/TXT/PDF export
    agent_zero.py    # A0 config CRUD, ingest, route, health (per-user config)
    edcm.py          # EDCM metrics ingest/query, response times, feedback stats, dashboard
  services/
    auth.py          # Password hashing, JWT, get_current_user
    llm.py           # LLM streaming (Emergent + OpenAI-compatible)
  tests/
    test_api_endpoints.py      # Core API regression
    test_a0_edcm_features.py   # A0 + EDCM feature tests
```

### Frontend (React + Tailwind + Shadcn)
```
/app/frontend/src/
  App.js             # Routes: /auth, /chat, /settings, /dashboard
  contexts/AuthContext.js
  pages/
    AuthPage.js, AuthCallback.js
    ChatPage.js      # Core chat UI (Dashboard link in menu)
    SettingsPage.js  # API keys + A0 Integration + Dashboard link
    DashboardPage.js # EDCM metrics, response times, feedback stats
  components/
    ModelSelector.js
    A0Settings.js    # A0 config with Local Device / Google Cloud tabs
    ui/
```

## What's Been Implemented
- Multi-model AI chat (GPT, Claude, Gemini via Emergent; Grok/DeepSeek/Perplexity via OpenAI-compatible)
- Dual auth (JWT + Google OAuth via Emergent)
- API key management with universal key toggle
- Mobile-optimized dark theme UI with carousel view
- Synthesis, batch prompting, global context, role assignment
- Sequential cascade orchestration with customizable order + context window (include last N responses)
- EDCM ingest now captures full conversation transcript + context (global context, roles, context mode)
- Auth service URL moved to AUTH_SERVICE_URL env var for deployment safety
- Universal key congruency check (live ping + missing key warnings in Settings + Chat banner)
- Rotated Emergent LLM key in backend env (operational update)
- Feedback submission now supports JWT auth header (thumbs up/down fixed)
- Auto-export toggle
- Export to JSON/TXT/PDF
- **Backend refactoring** from monolithic server.py to modular routes/services/models (Feb 12, 2026)
- **Agent Zero Plugin** — Per-user A0 config with two connection modes: Local Device (Samsung Galaxy A16u, configurable IP+port) and Google Cloud (stub). Health check, routing toggle, auto-ingest toggle. (Feb 12, 2026)
- **EDCM Dashboard** — Stub endpoints to receive 5 EDCM metrics from A0 (Constraint Mismatch Density, Fixation Coefficient, Escalation Gradient, Context Drift Index, Load Saturation Index). Real response time tracking per model. Thumbs up/down feedback aggregation per model. Dashboard page at /dashboard. (Feb 12, 2026)

## DB Collections
- `users`: id/user_id, username/email, password, api_keys
- `messages`: id, conversation_id, user_id, role, content, model, timestamp, feedback, response_time_ms
- `conversations`: id, user_id, title, created_at, updated_at
- `user_sessions`: user_id, session_token, expires_at
- `a0_config`: user_id, mode, local_url, local_port, cloud_url, api_key, route_via_a0, auto_ingest
- `edcm_metrics`: user_id, conversation_id, 5 metric fields, source, metadata, timestamp

## Pending Tasks

### P1
- Implement shared-room parallel modes (parallel-all + parallel-paired response sharing)
- Verify Enter key = newline, Ctrl+Enter = send
- Verify session persistence across reloads
- Verify export functionality
- Verify multi-turn context retention

### P2
- Integrate Grok/DeepSeek/Perplexity APIs (currently placeholders)
- Google Cloud A0 deployment (currently stub)
- Audio output improvements

## MOCKED
- EDCM metrics are stubs — they receive data from Agent Zero but no real A0 is running on this server
- Google Cloud A0 connection is a stub placeholder
- Grok/DeepSeek/Perplexity: UI placeholders only, no actual API integration
