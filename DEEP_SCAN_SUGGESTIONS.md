# Deep Scan Suggestions (2026-04-17) — Nonstandard Build Aware

## What was scanned (deeper pass)

This pass explicitly scanned for **nonstandard repository mechanics**, not just conventional Python/JS layout.

Commands run:

- `python scripts/check_max_lines.py`
- `pytest -q`
- `python -m compileall -q aimmh_lib backend`
- `python - <<'PY' ...` (wrapper/part-file integrity scan)
- `python - <<'PY' ...` (repo-wide Python syntax compile scan)
- `python - <<'PY' ...` (`import aimmh_lib.conversations` smoke check)
- `rg -n "_PART_FILES|PART_FILES|DO NOT EDIT OR REMOVE THIS SECTION|lines of code" -S .`

---

## Core architecture finding: this repo uses split-source loader stubs by design

A major nonstandard pattern is present and intentional:

- Python wrappers define `_PART_FILES`, concatenate `*.partNN.txt`, then `exec(compile(...))`.
- Node wrappers do equivalent `PART_FILES` + `readFileSync` + `Module._compile(...)`.
- Many files include top/bottom marker comments (`"lines of code"`, `"lines of commented"`) to satisfy policy checks.

This means many `*.part*.txt` files are likely **build/runtime inputs**, not disposable artifacts.

**Correction vs prior shallow assessment:** blanket removal of `*.part*.txt` would be unsafe.

---

## Validated integrity checks (nonstandard-aware)

### A) Wrapper-part linkage integrity (good)

Custom scan results:

- Python wrapper modules found: **17**
- JS wrapper modules found: **2**
- Missing part files referenced by wrappers: **0**
- Python syntax errors in concatenated part payloads: **0**

So the wrapper linkage itself is largely consistent.

### B) Structural contamination in wrapper files (high risk)

Detected wrappers where code exists **after** the stub loader line (unexpected for clean wrapper files):

- 10 Python wrappers
- 2 JS wrappers

Example affected files include:

- `aimmh_lib/conversations.py`
- `backend/routes/chat.py`
- `backend/routes/auth.py`
- `backend/routes/v1_hub.py`
- `backend/services/hub_runner.py`
- `frontend/plugins/visual-edits/babel-metadata-plugin.js`

This indicates some wrappers contain both stub logic **and** trailing merged content, which undermines predictability and parser behavior.

### C) Concrete breakage caused by contamination (confirmed)

`aimmh_lib/conversations.py` currently throws syntax errors when parsed/imported directly:

- `python -m compileall -q aimmh_lib backend` fails
- `import aimmh_lib.conversations` fails with:
  - `SyntaxError: from __future__ imports must occur at the beginning of the file`

Repo-wide syntax compile scan found exactly this one Python syntax error, concentrated in `aimmh_lib/conversations.py`.

---

## Test-system finding: protocol-driven, split test-state workflow

`test_result.md` is intentionally an index file pointing to split parts (`test_result_part1.md` etc.) and contains a strict “DO NOT EDIT OR REMOVE” protocol block.
It also gives an explicit reason for that split: **“This file was split to keep each file <= 400 lines.”**

Implication:

- Conventional assumptions (“single test result file”, “delete split files”) are wrong here.
- Any agent automation must preserve this split-protocol workflow.

Clarification:

- The repository provides a clearly stated split reason for `test_result*.md` (line-count cap).
- For many code `*.partNN.txt` splits, a reason is inferred from architecture and marker policy, but not always stated in one canonical sentence.

---

## Updated prioritized suggestions

1. **Fix import/parsing breakage first (P0)**
   - Repair `aimmh_lib/conversations.py` so it is either:
     - pure wrapper-only stub, or
     - pure full module (without wrapper indirection),
     but not a hybrid.

2. **Enforce wrapper purity invariant (P0/P1)**
   - Add a CI check: if a file contains loader-stub signature, it must not contain executable payload after the stub terminator.
   - This prevents future hybrid corruption.

3. **Document split-source contract (P1)**
   - Add/expand docs describing:
     - which directories intentionally use `*.partNN.txt`,
     - generation/update workflow,
     - rules for safe editing.

4. **Improve test bootstrap clarity (P1)**
   - Root-level test invocation still fails without missing deps (`requests`, `selenium`, `aiohttp`).
   - Add a root reproducible test setup command/file so `pytest -q` expectations are explicit.

5. **Keep line-marker policy, but clarify scope (P2)**
   - `scripts/check_max_lines.py` enforces marker + effective LOC policy.
   - Document that split wrappers are part of this policy so contributors don’t “clean up” required structure.

---

## Boundary object (unresolved constraints)

To preserve honest incompletion and mark the handoff between delivered findings and continuing work:

- I did **not** rewrite wrapper files in this pass.
- I did **not** refactor split-source architecture.
- I did **not** install missing test dependencies in this environment.
- I did **not** add CI guard scripts yet.

These unresolved constraints define the next implementation boundary.

---

## Reviewer Q&A addendum (2026-05-01)

### Q1) “This is one of the rare incidents…?”

From the current scan, wrapper contamination (content trailing after stub terminator) is **not rare** in this repository snapshot:

- Contaminated wrappers: **12**
- Total wrappers: **19**
- Ratio: **12 / 19** (~63%)

Interpretation: this appears as a recurring repository state/pattern rather than a one-off anomaly.

### Q2) “Total lines if refactored and consolidated?”

Measured from current wrapper + part files:

- Physical lines in wrapper files: **940**
- Physical lines in referenced part payloads: **12,260**

If refactored into consolidated single-source files (i.e., payload lives directly in canonical files), effective code-bearing line total would be approximately **12,260** lines (wrapper scaffolding removed, payload retained).

### Q3) “Is first line / last line followed?”

For line-marker convention (`"lines of code"` / `"lines of commented"` at first and last line) across wrapper files:

- Wrappers with marker on both first and last line: **11**
- Total wrappers: **19**

So first/last marker convention is followed for many wrappers, but **not all** wrappers in this snapshot.
