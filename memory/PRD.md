# Multi-Model Hub — Product Requirements Document

## Original Problem Statement
Build a multi-model AI hub that serves as the primary instrument for a0 (Agent Zero) to interact with LLMs, while also being a paid product for human users. The app provides parallel model responses, synthesis capabilities, batch chains, and is aligned with the spec at interdependentway.org.

## Architecture
- **Backend**: Python, FastAPI, MongoDB (motor), emergentintegrations
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Auth**: JWT + Google OAuth + Service Account tokens for a0
- **LLM Integration**: Emergent universal key (OpenAI/Anthropic/Google) + OpenAI-compatible (xAI/DeepSeek/Perplexity)
- **Spec Alignment**: v1.0.2-S9, append-only events, EDCM metrics, PTCA schema

## API Surface (v1)
- `/api/v1/a0/prompt` — Multi-model fan-out
- `/api/v1/a0/prompt/stream` — SSE streaming
- `/api/v1/a0/prompt-single` — Single model
- `/api/v1/a0/synthesize` — Cross-model synthesis
- `/api/v1/a0/batch` — Sequential chains
- `/api/v1/a0/history` — Thread list
- `/api/v1/a0/thread/{id}` — Thread messages
- `/api/v1/a0/export/{id}` — Full export with events
- `/api/v1/a0/feedback` — Thumbs up/down
- `/api/v1/a0/jobs/{id}` — Async job polling
- `/api/v1/edcm/eval` — EDCM evaluation
- `/api/v1/edcm/metrics/{id}` — Metric snapshots
- `/api/v1/edcm/alerts/{id}` — Alerts
- `/api/v1/ptca/schema` — Tensor schema
- `/api/v1/models` — Available models
- `/api/v1/registry` — User model registry CRUD
- `/api/v1/keys` — User API key management

## What's Implemented (as of 2026-03-14)

### P0 — Core (DONE)
- [x] Multi-model fan-out (parallel responses from N models)
- [x] Single model endpoint
- [x] SSE streaming for real-time response display
- [x] Append-only event logging (sacred logs)
- [x] Response persistence (chunk-by-chunk, never lost)
- [x] Thread history with full message replay
- [x] EDCM metrics engine (CM, DA, DRIFT, DVG, INT, TBF)
- [x] Model registry (6 developers, 20+ models, user-extensible)
- [x] API key management (user-addable, never exposed)
- [x] Authentication (JWT + Google OAuth + service accounts)
- [x] Clean dark UI with developer tabs, prompt at top, vertical response stack
- [x] a0 API reference document generated

### P0 — Core (DONE)
- [x] Synthesis endpoint (feed responses into other models)
- [x] Batch/chain endpoint (sequential prompts, configurable rooms)
- [x] Async mode with job polling
- [x] PTCA schema endpoint
- [x] Export endpoint with provenance

## Prioritized Backlog

### P1 — Next Up
- [ ] Resizable response windows + 50/50 split lock
- [ ] Carousel / vertical stack toggle with infinite loop option
- [ ] Stripe integration (pricing page, subscriptions)
- [ ] EDCM dashboard page with metric visualizations
- [ ] File/image upload with model-appropriate dispatch
- [ ] Grok key configuration (user has key, needs to add via Settings)

### P2 — Important
- [ ] Copy, audio, share buttons on response windows
- [ ] Global context box UI
- [ ] Service account management UI
- [ ] DeepSeek/Perplexity key integration
- [ ] Advanced search/filter on thread history
- [ ] "hmmm doctrine" display

### P3 — Future
- [ ] Webhook/callback for async batch completion
- [ ] Cost tracking per model/thread
- [ ] Context window management UI (S5)
- [ ] Deployment documentation for Google Cloud (GKE/Cloud Run)

## Key Files
- Backend: `/app/backend/server.py`, `/app/backend/routes/v1_a0.py`, `/app/backend/services/llm.py`
- Frontend: `/app/frontend/src/pages/ChatPage.js`, `/app/frontend/src/pages/SettingsPage.js`
- a0 Reference: `/app/backend/a0_api_reference.md`
- Spec: interdependentway.org/canon/spec.md
