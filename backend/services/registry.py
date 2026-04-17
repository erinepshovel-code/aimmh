# "lines of code":"174","lines of commented":"11"
"""Dynamic README registry collector.

What this module does:
- Scans backend/frontend source modules.
- Computes code vs commented line counts.
- Extracts module/function docstrings/comments.
- Optionally syncs begin/end metric markers per module.

How it works:
- Uses extension-aware line classification.
- Uses Python AST for Python docstrings.
- Uses simple JSDoc-style regex extraction for JS/TS files.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = [ROOT / "backend", ROOT / "frontend" / "src", ROOT / "frontend" / "plugins", ROOT / "aimmh_lib"]
SOURCE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx"}
SKIP_DIR_NAMES = {"node_modules", ".git", ".emergent", "__pycache__", "test_reports", "tests"}
METRIC_RE = re.compile(r"lines of code\"\s*:\s*\"(?P<code>\d+)\"\s*,\s*\"lines of commented\"\s*:\s*\"(?P<commented>\d+)\"")


def _comment_prefix(path: Path) -> str:
    return "#" if path.suffix == ".py" else "//"


def _is_source(path: Path) -> bool:
    if path.suffix not in SOURCE_EXTS:
        return False
    return not any(part in SKIP_DIR_NAMES for part in path.parts)


def _read_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def _count_py(lines: List[str]) -> Tuple[int, int]:
    code, commented = 0, 0
    in_block = False
    block_delim = ""
    for idx, raw in enumerate(lines):
        if idx == 0 or idx == len(lines) - 1:
            continue
        s = raw.strip()
        if not s:
            continue
        if in_block:
            commented += 1
            if block_delim in s and s.count(block_delim) % 2 == 1:
                in_block = False
            continue
        if s.startswith("#"):
            commented += 1
            continue
        if s.startswith("\"\"\"") or s.startswith("'''"):
            delim = s[:3]
            if s.count(delim) >= 2 and len(s) > 6:
                commented += 1
                continue
            in_block = True
            block_delim = delim
            commented += 1
            continue
        code += 1
    return code, commented


def _count_js(lines: List[str]) -> Tuple[int, int]:
    code, commented = 0, 0
    in_block = False
    for idx, raw in enumerate(lines):
        if idx == 0 or idx == len(lines) - 1:
            continue
        s = raw.strip()
        if not s:
            continue
        if in_block:
            commented += 1
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("//"):
            commented += 1
            continue
        if s.startswith("/*"):
            commented += 1
            if "*/" not in s:
                in_block = True
            continue
        code += 1
    return code, commented


def _extract_python_docs(text: str) -> Tuple[str, List[Dict[str, str]]]:
    module_doc = ""
    functions: List[Dict[str, str]] = []
    try:
        tree = ast.parse(text)
        module_doc = ast.get_docstring(tree) or ""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name": node.name,
                    "doc": ast.get_docstring(node) or "",
                })
    except Exception:
        pass
    return module_doc, functions


def _extract_js_docs(text: str) -> Tuple[str, List[Dict[str, str]]]:
    module_doc = ""
    functions: List[Dict[str, str]] = []
    module_match = re.search(r"/\*\*([\s\S]*?)\*/", text)
    if module_match:
        module_doc = re.sub(r"^\s*\* ?", "", module_match.group(1), flags=re.MULTILINE).strip()
    fn_matches = re.finditer(
        r"/\*\*([\s\S]*?)\*/\s*(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=|class\s+(\w+))",
        text,
    )
    for match in fn_matches:
        doc = re.sub(r"^\s*\* ?", "", match.group(1), flags=re.MULTILINE).strip()
        name = match.group(2) or match.group(3) or match.group(4) or "anonymous"
        functions.append({"name": name, "doc": doc})
    return module_doc, functions


def _metric_marker(path: Path, code: int, commented: int) -> str:
    return f'{_comment_prefix(path)} "lines of code":"{code}","lines of commented":"{commented}"'


def _sync_markers(path: Path, lines: List[str], code: int, commented: int) -> bool:
    marker = _metric_marker(path, code, commented)
    changed = False
    if not lines:
        lines = [marker, marker]
        changed = True
    if not lines or METRIC_RE.search(lines[0] or "") is None:
        lines = [marker] + lines
        changed = True
    else:
        if lines[0] != marker:
            lines[0] = marker
            changed = True
    if len(lines) < 2 or METRIC_RE.search(lines[-1] or "") is None:
        lines = lines + [marker]
        changed = True
    else:
        if lines[-1] != marker:
            lines[-1] = marker
            changed = True
    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def _collect_file(path: Path, sync_markers: bool) -> Dict[str, Any]:
    lines = _read_lines(path)
    code, commented = _count_py(lines) if path.suffix == ".py" else _count_js(lines)
    if sync_markers:
        _sync_markers(path, lines, code, commented)
        lines = _read_lines(path)
        code, commented = _count_py(lines) if path.suffix == ".py" else _count_js(lines)
    text = "\n".join(lines)
    module_doc, functions = _extract_python_docs(text) if path.suffix == ".py" else _extract_js_docs(text)
    top_ok = bool(lines and METRIC_RE.search(lines[0] or ""))
    bottom_ok = bool(lines and METRIC_RE.search(lines[-1] or ""))
    return {
        "path": str(path.relative_to(ROOT)),
        "ext": path.suffix,
        "lines_of_code": code,
        "lines_of_commented": commented,
        "max_code_rule_ok": code <= 400,
        "marker_top_ok": top_ok,
        "marker_bottom_ok": bottom_ok,
        "module_doc": module_doc,
        "functions": functions,
    }


def collect_dynamic_registry(sync_markers: bool = False) -> Dict[str, Any]:
    modules: List[Dict[str, Any]] = []
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for path in scan_dir.rglob("*"):
            if not path.is_file() or not _is_source(path):
                continue
            modules.append(_collect_file(path, sync_markers))

    modules.sort(key=lambda item: item["path"])
    violations = [
        {
            "path": m["path"],
            "max_code_rule_ok": m["max_code_rule_ok"],
            "marker_top_ok": m["marker_top_ok"],
            "marker_bottom_ok": m["marker_bottom_ok"],
            "lines_of_code": m["lines_of_code"],
        }
        for m in modules
        if (not m["max_code_rule_ok"]) or (not m["marker_top_ok"]) or (not m["marker_bottom_ok"])
    ]

    return {
        "module_count": len(modules),
        "violations": violations,
        "modules": modules,
    }

# "lines of code":"174","lines of commented":"11"
