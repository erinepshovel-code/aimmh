from __future__ import annotations

from pathlib import Path

MAX_LINES = 400
ROOT = Path(__file__).resolve().parents[1]

SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".json", ".css", ".html"}
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
    return True


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for _ in handle)


def main() -> int:
    violations: list[tuple[int, Path]] = []

    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_check(path):
            continue
        count = line_count(path)
        if count > MAX_LINES:
            violations.append((count, path.relative_to(ROOT)))

    if not violations:
        print(f"PASS: All checked source files are <= {MAX_LINES} lines.")
        return 0

    print(f"FAIL: {len(violations)} file(s) exceed {MAX_LINES} lines:")
    for count, rel_path in sorted(violations, reverse=True):
        print(f" - {rel_path} ({count} lines)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
