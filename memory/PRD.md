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
    payments.py      # Stripe checkout/catalog/summary response models
    context.py       # Console context + cost limit request models
  routes/
    auth.py          # Register, login, Google OAuth, logout, /me
    keys.py          # API key CRUD
    chat.py          # Chat streaming (with response_time_ms), feedback, conversations, catchup
    export.py        # JSON/TXT/PDF export
    agent_zero.py    # A0 config CRUD, ingest, route, health (per-user config)
    edcm.py          # EDCM metrics ingest/query, response times, feedback stats, dashboard
    payments.py      # Stripe checkout sessions, status polling, webhook, catalog, payment summary
    console.py       # Console preferences + editable prompt context logs
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
  App.js             # Routes: /auth, /chat, /settings, /dashboard, /console, /pricing
  contexts/AuthContext.js
  pages/
    AuthPage.js, AuthCallback.js
    ChatPage.js      # Core chat UI (Dashboard link in menu)
    SettingsPage.js  # API keys + A0 Integration + Dashboard link
    DashboardPage.js # EDCM metrics, response times, feedback stats
    ConsolePage.js   # Token/cost controls, EDCM view, editable prompt context, donations vs costs
    PricingPage.js   # Core/support/founder/credits tabs with Stripe checkout wiring
  components/
    ModelSelector.js
    A0Settings.js    # A0 config with Local Device / Google Cloud tabs
    HmmmDoctrineBar.jsx
    chat/ResponseMessageContent.jsx
    chat/PromptHistoryItem.jsx
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
- Re-keyed EMERGENT_LLM_KEY in backend env and validated universal status (Feb 25, 2026)
- Feedback submission now supports JWT auth header (thumbs up/down fixed)
- Per-model header customization button opens model-specific prompt tuning dialog (role/modifier/verbosity/alignment)
- Endless carousel behavior via looped navigation + swipe gestures on model panel container
- Markdown/GFM response rendering enabled (lists, tables, links, code blocks)
- File/image attachment composer with routing controls (send to all models or selected models)
- Backend attachment-aware chat payload handling (targeted attachments injected per model prompt)
- Agent Zero non-UI API surface added: options, conversations list, transcript retrieval, non-UI chat stream alias
- Iteration 4 regression/testing pass completed (backend + frontend feature verification)
- Shared-room orchestration modes added: `parallel_all` and `parallel_paired` (Scene tab + backend context routing)
- Shared-room auto pair map preview added in Scene tab for paired mode
- Reload resilience fix: assistant responses are now progressively persisted during streaming in backend
- Conversation re-sync on reload added in frontend to recover latest server-side transcript
- Chat persistence storage moved to localStorage for stronger cross-reload/cross-tab continuity until logout
- Iteration 5 regression/testing pass completed (shared-room + reload persistence verification)
- Added explicit "Refresh from logs" action in chat top bar for manual transcript recovery
- Prompt history entries now include per-item copy actions
- Response panels now support per-panel copy-thread + per-message copy actions across visible responses
- Synthesis is now panel-scoped (triggered from model header), no longer a global top action
- Response renderer modularized with dedicated Markdown/JSON component (`components/chat/ResponseMessageContent.jsx`)
- Prompt history item modularized (`components/chat/PromptHistoryItem.jsx`)
- Vertical dual-panel UX updated: smooth motion indicators, resizable split when unlocked, lock-to-50/50 via button and two-touch gesture hint
- Iteration 6 frontend testing pass completed (refresh recovery + copyability + panel-scoped synthesis + lock/resizing)
- Console page added at `/console` with tabbed windows:
  - Token + cost telemetry and editable slider/toggle limits
  - EDCM brain connection metrics display
  - Editable context payload inspector for prompt packets
  - Donations vs costs financial panel + OAuth identity state
- Stripe wiring added:
  - Catalog seeding endpoint + founder cap tracking
  - Checkout session creation endpoint
  - Checkout status polling endpoint
  - Webhook handler endpoint
  - Pricing UI at `/pricing` with Core/Support/Founder/Credits tabs and real checkout redirects
- Founder cap hard enforcement implemented (53 slots) with remaining-slot badge in UI
- Chat route now records prompt context logs and assistant token/cost telemetry fields
- Global bottom footer added: dynamic `hmmm doctrine` bar (route/state/signal aware)
- Iteration 7 backend+frontend testing pass completed (all checks passed)
- Current-thread persistence hardening: ChatPage now re-syncs only the active conversation from backend on auth-ready mount and window-focus; manual refresh no longer auto-switches to latest thread.
- Pricing page polish pass: Added billing hero, auth-required indicator, live payment summary cards (paid/support/usage/compute), and clearer checkout cancel/status UX.
- Stripe checkout session now prefers `stripe_price_id` when catalog has one (fallback to fixed amount remains), improving subscription-ready compatibility.
- Iteration 8 backend+frontend regression/testing pass completed (chat persistence, pricing tabs, support toggle, checkout redirect/status, feedback all verified)
- Added explicit opt-in "Restore Latest Thread" action in Chat menu to manually switch to latest conversation when desired (default behavior remains current-thread scoped).
- Verified restore-latest flow + existing refresh-from-logs regression via frontend testing agent.
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
- `context_logs`: id, user_id, conversation_id, prompt message, context packet fields (global context, roles, per-model messages, shared config), attachments, timestamps
- `console_preferences`: user_id, enforce_token_limit, enforce_cost_limit, token_limit, cost_limit_usd, updated_at
- `payment_catalog`: package metadata used by pricing/checkout seeding
- `payment_transactions`: required Stripe transaction tracking collection (session_id, amount, package/category, user_id/email, status/payment_status, metadata, fulfillment state)
- `founder_registry`: founder purchaser listing records

## Pending Tasks

### P1
- Broader regression pass across exports/session/multi-turn retention on production-like data volume
- Improve attachment rendering/preview in conversation history (currently focused on prompt dispatch)
- Continue ChatPage modularization to reduce file size and keep component depth shallow
- Add Stripe customer portal flow (self-serve subscription management/cancel) and richer webhook event mapping
- Add conversation picker/search for switching among older threads beyond latest/current

### P2
- Validate Grok live inference path with user-provided key in Settings (implementation exists; live key verification pending)
- Integrate DeepSeek/Perplexity APIs (still key-blocked in current environment)
- Google Cloud A0 deployment (currently stub)
- Audio output improvements
- Thumbs feedback refinements (downgraded priority by user)
- Upgrade Stripe catalog from DB-seeded package map to dashboard-managed product/price IDs if production billing ops require strict Stripe object governance

## MOCKED
- EDCM metrics are stubs — they receive data from Agent Zero but no real A0 is running on this server
- Google Cloud A0 connection is a stub placeholder
- DeepSeek/Perplexity: API integration remains key-blocked in this environment
