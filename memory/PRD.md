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
    agent_zero.py    # A0 models
  routes/
    auth.py          # Register, login, Google OAuth, logout, /me
    keys.py          # API key CRUD
    chat.py          # Chat streaming, feedback, conversations, catchup
    export.py        # JSON/TXT/PDF export
    agent_zero.py    # A0 ingest, route, health
  services/
    auth.py          # Password hashing, JWT, get_current_user
    llm.py           # LLM streaming (Emergent + OpenAI-compatible)
  tests/
    test_api_endpoints.py  # Regression tests
```

### Frontend (React + Tailwind + Shadcn)
```
/app/frontend/src/
  App.js, App.css, index.js, index.css
  contexts/AuthContext.js
  pages/AuthPage.js, ChatPage.js, SettingsPage.js, AuthCallback.js
  components/ModelSelector.js, A0Settings.js, ui/
```

## What's Been Implemented
- Multi-model AI chat (GPT, Claude, Gemini via Emergent; Grok/DeepSeek/Perplexity via OpenAI-compatible)
- Dual auth (JWT + Google OAuth via Emergent)
- API key management with universal key toggle
- Mobile-optimized dark theme UI with carousel view
- Synthesis, batch prompting, global context, role assignment
- Auto-export toggle
- Export to JSON/TXT/PDF
- Agent Zero backend endpoints (ingest, route, health)
- A0Settings frontend component (not yet integrated into main flow)
- Auto-Cascade frontend skeleton (needs completion)
- **Backend refactoring** from monolithic server.py to modular routes/services/models (Feb 2026)

## Pending Tasks (Prioritized)

### P0
- Complete Agent Zero frontend integration (connect A0Settings into SettingsPage, wire up routing toggle in ChatPage)

### P1
- Fix thumbs up/down feedback (reported broken — endpoint works, likely frontend integration issue with specific user sessions)
- Complete Auto-Cascade feature (logic partially in ChatPage, needs testing with real models)
- Verify Enter key = newline, Ctrl+Enter = send
- Verify session persistence across reloads
- Verify export functionality
- Verify multi-turn context retention

### P2
- Integrate Grok/DeepSeek/Perplexity APIs (currently placeholders)
- Audio output improvements (currently uses browser TTS)

## Key DB Collections
- `users`: id/user_id, username/email, password, api_keys
- `messages`: id, conversation_id, user_id, role, content, model, timestamp, feedback
- `conversations`: id, user_id, title, created_at, updated_at
- `user_sessions`: user_id, session_token, expires_at (Google OAuth)
