# AIMMH Engineering Companion (Claude Guide)

This file describes how to reason about and safely extend this repository.

## Product intent

AIMMH is a modular AI orchestration hub where users can:
- instantiate many model personas
- organize them into nested groups
- run staged orchestration pipelines (batch + roleplay)
- compare and synthesize outputs
- inspect architecture and module docs directly inside the app

## Technical stack

- **Frontend**: React, Tailwind, router-based tabbed UX
- **Backend**: FastAPI, Motor/MongoDB, Pydantic models
- **Orchestration core**: local `aimmh_lib`
- **Billing**: Stripe routes under `/api/v2/payments`
- **Dynamic documentation**: backend registry scanner + frontend module map/README assist

## Repository shape

```
/app
├── aimmh_lib/
├── backend/
│   ├── routes/
│   ├── services/
│   ├── models/
│   └── server.py
├── frontend/
│   ├── src/components/hub/
│   ├── src/pages/
│   └── mobile/apk/
├── memory/
└── scripts/
```

## Important operational patterns

1. **Split-file execution wrappers**
   - Some backend modules are wrappers (e.g., `v1_hub.py`, `hub_runner.py`) that execute `.part*.txt` files.
   - Update the `.part*.txt` files for behavior changes.

2. **Mongo serialization safety**
   - Never return raw `_id` or `ObjectId` in API payloads.
   - Use projection `{"_id": 0}` and explicit response models.

3. **Roleplay and context performance**
   - Use `services/hub_cache.py` for per-instantiation context caching.
   - Cache key uses instance config + instance/thread update stamps + verbosity.
   - Invalidation is automatic via key changes and explicit purge on instance mutations.

4. **Frontend testability discipline**
   - Keep `data-testid` on all interactive/critical UI elements.
   - Preserve IDs when refactoring.

5. **Documentation UX and discovery**
   - Dynamic docs are surfaced in:
     - `HelpReadmePanel` (README context + ask flow)
     - `DocsModuleMapPanel` (graphical module map)

## Extending the app safely

### Add a new orchestration pattern
1. Add pattern support in `aimmh_lib`
2. Extend `HubPattern` in `backend/models/hub.py`
3. Wire execution branch in `services/hub_runner.py.part*`
4. Add pattern option in `frontend/src/components/hub/hubConfig.js`
5. Add visual node/steps in `PatternVisualizerPanel.jsx`

### Add a new hub tab
1. Add tab id/label in `AimmhHubPage.jsx`
2. Add tab route case in `AimmhHubTabContent.jsx`
3. Create panel component in `src/components/hub/`
4. Add robust `data-testid` coverage

### Ship Android APK variants
Use `/frontend/mobile/apk` scripts:
- `build-debug-apk.sh webview`
- `build-debug-apk.sh bundled`

## Current high-value next tasks

- saved workflow templates lifecycle (rename/tag/export/import/share)
- drag-and-drop stage reordering
- deeper instance thread drill-down
- WS-Admin cache observability (hit/miss + purge controls)
