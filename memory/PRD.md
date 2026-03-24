# AIMMH Hub — Product Requirements Document

## Original Problem Statement
Build a multi-model AI hub using `aimmh_lib`, with isolated model instances, nested orchestration patterns, FastAPI endpoints, and a mobile-first tabbed UI covering registry, model/group instantiation, runs, responses, and chat/synthesis workflows.

## Current Product Shape
The application is now a full-stack AIMMH workspace with:
- persistent isolated model instances
- nested groups and staged orchestration runs
- direct same-prompt multi-instance chat
- selected-response synthesis
- registry + provider verification tools
- Stripe-backed pricing tiers and Hall of Makers flows
- a mobile-first tabbed orchestration UI

## Architecture
- **Frontend:** React, React Router, Tailwind CSS, Shadcn UI, Sonner
- **Backend:** FastAPI, Pydantic, MongoDB via motor
- **Core orchestration library:** local `/app/aimmh_lib`
- **Payments:** Stripe via `/api/v2/payments`
- **Auth:** JWT-based application auth

## Primary Routes
- `/auth` — login and registration
- `/chat` — AIMMH hub workspace
- `/settings` — registry and key management
- `/pricing` — pricing tiers and checkout entry
- `/makers` — public Hall of Makers page

## Implemented Backend Features
- [x] `/api/v1/hub/instances` create/list/update/archive/unarchive/history
- [x] `/api/v1/hub/groups` nested group management
- [x] `/api/v1/hub/runs` orchestration runs across `fan_out`, `daisy_chain`, `room_all`, `room_synthesized`, `council`, and `roleplay`
- [x] `/api/v1/hub/chat/prompts` direct multi-instance chat
- [x] `/api/v1/hub/chat/synthesize` selected-response synthesis batches
- [x] `/api/v1/registry` developer/model registry with website metadata and verification endpoints
- [x] `/api/v2/payments` pricing catalog, checkout, summary, and Hall of Makers support

## Implemented Frontend Features
- [x] README-style AIMMH splash screen
- [x] Mobile-first tabbed workspace: Registry, Instantiation, Runs, Responses, Chat & Synthesis
- [x] Instance creation/edit/archive flows
- [x] Group creation/edit/archive flows
- [x] Run builder and response workspace
- [x] Prompt-indexed chat responses
- [x] Shared synthesis basket across chat and responses
- [x] Response actions: thumbs up/down, copy, share
- [x] Response formatting preserved via markdown rendering
- [x] Response pane controls/gestures for pane switching and font zoom
- [x] Pricing and Hall of Makers pages

## Latest Verified Fixes — 2026-03-24
- [x] Resolved the blocking Chat & Synthesis usability issue: instances now reliably appear after tab switching because the tab interaction itself is reliable
- [x] Reworked hub tab navigation into a responsive grid so long tab labels no longer clip or behave inconsistently
- [x] Added auto-scroll on tab change in `AimmhHubPage.jsx` so switching from a scrolled tab lands users at the correct content anchor
- [x] Added stronger `data-testid` coverage for hub tabs, instance creation, prompt batches, synthesis selection, and synthesis outputs
- [x] Exposed `hub_prompt_id` and `hub_synthesis_batch_id` through instance history responses in `backend/models/hub.py`

## Verified Testing Status
- [x] Frontend end-to-end synthesis workflow passed in preview
- [x] Tab switching reliability passed from a scrolled instantiation state into Chat & Synthesis
- [x] Backend metadata exposure passed for both direct chat and synthesis history messages

## Important File References
- `/app/frontend/src/pages/AimmhHubPage.jsx`
- `/app/frontend/src/hooks/useHubWorkspace.js`
- `/app/frontend/src/components/hub/HubTabsNav.jsx`
- `/app/frontend/src/components/hub/HubMultiChatPanel.jsx`
- `/app/frontend/src/components/hub/HubInstancesPanel.jsx`
- `/app/backend/models/hub.py`
- `/app/backend/routes/v1_hub.py`
- `/app/backend/services/hub_chat.py`
- `/app/backend/services/hub_synthesis.py`

## Prioritized Backlog

### P0 — Resolved
- [x] Chat & Synthesis tab rendering / usability blocker
- [x] Instance history metadata exposure for chat and synthesis

### P1 — Next
- [ ] Deployment/release pass when requested
- [ ] Broader `data-testid` coverage across remaining untouched controls for stronger regression automation
- [ ] Optional modularization pass for `AimmhHubPage.jsx` and `useHubWorkspace.js`

### P2 — Important Enhancements
- [ ] Save and reuse orchestration workflows
- [ ] Drag-and-drop stage reordering in the runs builder
- [ ] Richer per-instance thread drill-down/history inspection

### P3 — Future Ideas
- [ ] More explicit loading/progress states for long-running syntheses
- [ ] Sharable run/synthesis exports
- [ ] Analytics for prompt, instance, and synthesis usage

## Notes for Next Agent
- Use `frontend/.env` `REACT_APP_BACKEND_URL` as the preview source of truth
- The current synthesis workflow is working in preview after the tab-navigation fix
- If a future report says instances are missing from Chat & Synthesis, first verify the tab actually changed and the page scrolled to the tab anchor
