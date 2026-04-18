# AIMMH — Assistive Iterational Modular Model Hub

Multi-model orchestration workspace for parallel comparison, roleplay simulation, synthesis, and guided extension.

## What this repository contains

- **Frontend (`/frontend`)**: React + Tailwind mobile-first orchestration UI
- **Backend (`/backend`)**: FastAPI + MongoDB APIs for hub instances, groups, runs, chat, synthesis, billing, and admin
- **Core orchestration library (`/aimmh_lib`)**: fan-out, daisy-chain, room, council, and roleplay execution primitives
- **Project memory (`/memory`)**: living PRD, roadmap context, and credential/testing references

## In-depth architecture snapshot

### 1) Runtime layers
- **UI layer**: tabbed AIMMH workspace (`/chat`) with Help, Module Map, Visualizer, Registry, Runs, Chat, Synthesis
- **Service layer**: routed APIs (`/api/v1/*`, `/api/v2/payments/*`) with tier enforcement and guest usage rules
- **Execution layer**: `aimmh_lib` orchestration patterns executed from `services/hub_runner`
- **Persistence layer**: Mongo collections for users, model registry, instances/groups/runs, prompt histories, synthesis batches, and cache state

### 2) Core orchestration data flow
1. Create instances/groups in hub workspace.
2. Build run stages (batch or roleplay).
3. Execute run via `/api/v1/hub/runs`.
4. Persist stage outputs and per-instance thread history.
5. Review in responses/chat/synthesis views and visualizer.

### 3) Key backend modules
- `backend/routes/v1_hub.py*`: hub CRUD, run execute/list/detail, chat/synthesis endpoints
- `backend/services/hub_runner.py*`: orchestration execution + instance context assembly
- `backend/services/hub_chat.py`: direct same-prompt multi-instance chat
- `backend/services/hub_synthesis.py`: selected-response synthesis fan-out
- `backend/services/hub_cache.py`: per-instantiation context/prompt caching with TTL
- `backend/services/registry.py`: dynamic README registry collector and marker sync

### 4) Key frontend modules
- `src/pages/AimmhHubPage.jsx`: workspace shell + tab state
- `src/components/hub/AimmhHubTabContent.jsx`: tab-to-panel router
- `src/components/hub/PatternVisualizerPanel.jsx`: orchestration pattern animations
- `src/components/hub/DocsModuleMapPanel.jsx`: dynamic document/module graphical map GUI
- `src/components/hub/HelpReadmePanel.jsx`: dynamic README assist panel

## Dynamic Module Map GUI

The workspace now includes a **Module Map** tab that:
- pulls dynamic module registry (`/api/v1/readme/registry`)
- groups files by root folder
- renders a graphical node-style file map with relative code-size bars
- shows module docs + function docs on selection

## APK packaging (both modes)

Implemented in `/frontend/mobile/apk`:

- **Mode A (WebView)**: wraps live AIMMH URL
- **Mode B (Bundled)**: ships local built web assets

Run from `/app/frontend`:

```bash
./mobile/apk/build-debug-apk.sh webview
./mobile/apk/build-debug-apk.sh bundled
```

> Note: this environment does not include Java/Android SDK, so APK binary compile must be finished in Android Studio from `/app/frontend/android`.

## Local development quick start

```bash
# frontend deps
cd frontend && yarn

# backend deps
cd ../backend && pip install -r requirements.txt
```

Services are supervisor-managed in the platform runtime.

## Quality and guardrails

- 400-line code policy enforcement script: `/scripts/check_max_lines.py`
- dynamic marker metadata support via README registry
- curated Universal Key model registry enforced server-side
- cookie-first auth + guest quota fallback support

