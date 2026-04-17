from __future__ import annotations

import re
from pathlib import Path

MAX_LINES = 400
ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [
    ROOT / "backend",
    ROOT / "frontend" / "src",
    ROOT / "frontend" / "plugins",
    ROOT / "aimmh_lib",
]

SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
EXCLUDED_DIR_NAMES = {
    ".git",
    ".emergent",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test_reports",
}
EXCLUDED_FILE_NAMES = {
    "yarn.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
}
MARKER_RE = re.compile(r'"lines of code"\s*:\s*"\d+"\s*,\s*"lines of commented"\s*:\s*"\d+"')


def should_check(path: Path) -> bool:
    if path.name in EXCLUDED_FILE_NAMES:
        return False
    if path.suffix not in SOURCE_EXTENSIONS:
        return False
    parts = set(path.parts)
    if parts & EXCLUDED_DIR_NAMES:
        return False
    if ".part" in path.name and path.suffix == ".txt":
        return False
    if "tests" in path.parts:
        return False
    return True


def read_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return handle.read().splitlines()


def count_code_and_commented(path: Path, lines: list[str]) -> tuple[int, int]:
    code = 0
    commented = 0
    if len(lines) <= 2:
        return 0, 0

    in_block = False
    py_block_delim = ""
    for idx, raw in enumerate(lines):
        if idx == 0 or idx == len(lines) - 1:
            continue
        stripped = raw.strip()
        if not stripped:
            continue

        if path.suffix == ".py":
            if in_block:
                commented += 1
                if py_block_delim in stripped and stripped.count(py_block_delim) % 2 == 1:
                    in_block = False
                continue
            if stripped.startswith("#"):
                commented += 1
                continue
            if stripped.startswith("\"\"\"") or stripped.startswith("'''"):
                delim = stripped[:3]
                commented += 1
                if not (stripped.count(delim) >= 2 and len(stripped) > 6):
                    in_block = True
                    py_block_delim = delim
                continue
            code += 1
        else:
            if in_block:
                commented += 1
                if "*/" in stripped:
                    in_block = False
                continue
            if stripped.startswith("//"):
                commented += 1
                continue
            if stripped.startswith("/*"):
                commented += 1
                if "*/" not in stripped:
                    in_block = True
                continue
            code += 1
    return code, commented


def main() -> int:
    violations: list[str] = []

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for path in scan_dir.rglob("*"):
            if not path.is_file() or not should_check(path):
                continue
            lines = read_lines(path)
            top_ok = bool(lines and MARKER_RE.search(lines[0] or ""))
            bottom_ok = bool(lines and MARKER_RE.search(lines[-1] or ""))
            code_count, _commented_count = count_code_and_commented(path, lines)
            if code_count > MAX_LINES or not top_ok or not bottom_ok:
                rel = path.relative_to(ROOT)
                violations.append(f" - {rel} (code={code_count}, top_marker={top_ok}, bottom_marker={bottom_ok})")

    if not violations:
        print(f"PASS: All checked modules satisfy marker + <= {MAX_LINES} code-line rules.")
        return 0

    print(f"FAIL: {len(violations)} module(s) violate rules:")
    for row in violations:
        print(row)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
