# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6,<7",
# ]
# ///
"""Check that schema.dbml covers every database interface in plan.md and every openapi transaction.

Usage:
    uv run scripts/coverage_check.py --plan <plan.md> --dbml <schema.dbml> --openapi <openapi.yaml>
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

_PEP723 = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"


def _declared_dependencies() -> list[str]:
    # Read this file's own inline script metadata with the PEP 723 reference regex.
    src = Path(__file__).read_text(encoding="utf-8")
    block = next((m for m in re.finditer(_PEP723, src) if m.group("type") == "script"), None)
    if block is None:
        return []
    content = "".join(
        line[2:] if line.startswith("# ") else line[1:]
        for line in block.group("content").splitlines(keepends=True)
    )
    return tomllib.loads(content).get("dependencies", [])


def _require(*modules: str) -> None:
    # Fail fast with the exact remediation when a declared dependency is missing.
    missing = []
    for module in modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if not missing:
        return
    me = Path(__file__).resolve()
    deps = " ".join(f'"{d}"' for d in _declared_dependencies())
    sys.stderr.write(
        f"[{me.name}] missing module(s): {', '.join(missing)}\n"
        "Dependencies are declared in this file's '# /// script' block.\n"
        f"Preferred (uv manages the environment):  uv run {me}\n"
        "  install uv on macOS/Linux:  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
        "  install uv on Windows:      powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
        f"Fallback (current interpreter):          {sys.executable} -m pip install {deps}\n"
    )
    sys.exit(1)


_require("yaml")

import yaml  # noqa: E402

DB_ENDPOINT = "資料庫端點"
COMMON_INTERFACE = "資料庫共通介面"
TABLE_SUFFIX = " 資料表介面"
REQUIREMENT_MARK = "**對應需求**"
TRANSACTION_MARK = "**交易**"
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace", "query")

# "1. `products 資料表介面`" in the interface inventory of plan.md.
_ITEM = re.compile(r"^\s*\d+\.\s+`([^`]+)`\s*$")
_ENDPOINT = re.compile(r"^\s*-\s*端點類型：\s*`([^`]+)`")
# "Table name {", "Table "name" as alias [settings] {", "TableGroup name {".
_BLOCK = re.compile(r'(?im)^\s*(tablegroup|table)\s+("[^"]+"|[^\s{\[]+)(?:\s+as\s+\S+)?\s*(?:\[[^\]]*\])?\s*\{')
_NOTE = re.compile(r"(?is)^\s*note\s*(?::\s*|\{\s*)('''(.*?)'''|'((?:[^'\\\n]|\\.)*)')", re.M)


def db_interfaces(plan: Path) -> list[str]:
    # Collect interface names whose 端點類型 is 資料庫端點.
    names: list[str] = []
    current = None
    for line in plan.read_text(encoding="utf-8").splitlines():
        m = _ITEM.match(line)
        if m:
            current = m.group(1).strip()
            continue
        m = _ENDPOINT.match(line)
        if m and current is not None:
            if m.group(1).strip() == DB_ENDPOINT:
                names.append(current)
            current = None
    return names


def _block_end(text: str, start: int) -> int:
    # Return the index just after the brace that closes the block opened at text[start - 1].
    depth, i = 1, start
    while i < len(text):
        if text.startswith("'''", i):
            close = text.find("'''", i + 3)
            i = len(text) if close < 0 else close + 3
            continue
        ch = text[i]
        if ch in "'\"`":
            close = text.find(ch, i + 1)
            while close > 0 and text[close - 1] == "\\":
                close = text.find(ch, close + 1)
            i = len(text) if close < 0 else close + 1
            continue
        if ch == "/" and text.startswith("//", i):
            nl = text.find("\n", i)
            i = len(text) if nl < 0 else nl
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def dbml_blocks(dbml: Path) -> tuple[dict[str, str | None], dict[str, str | None]]:
    # Map table and table-group names to their Note text (None when the block has no Note).
    text = dbml.read_text(encoding="utf-8")
    tables: dict[str, str | None] = {}
    groups: dict[str, str | None] = {}
    pos = 0
    while True:
        m = _BLOCK.search(text, pos)
        if not m:
            break
        end = _block_end(text, m.end())
        body = text[m.end():end - 1]
        note = _NOTE.search(body)
        note_text = None if note is None else (note.group(2) if note.group(2) is not None else note.group(3))
        name = m.group(2).strip('"')
        target = groups if m.group(1).lower() == "tablegroup" else tables
        target[name] = None if note_text is None else note_text.strip()
        pos = end
    return tables, groups


def transaction_operations(openapi: Path) -> list[str]:
    # List operationIds whose description carries a **交易** section.
    doc = yaml.safe_load(openapi.read_text(encoding="utf-8")) or {}
    ops: list[str] = []
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        candidates = [(m, item[m]) for m in HTTP_METHODS if isinstance(item.get(m), dict)]
        candidates += [(m, op) for m, op in (item.get("additionalOperations") or {}).items() if isinstance(op, dict)]
        for method, op in candidates:
            if TRANSACTION_MARK in str(op.get("description") or ""):
                ops.append(op.get("operationId") or f"{method.upper()} {path}")
    return ops


def check(plan: Path, dbml: Path, openapi: Path) -> list[str]:
    violations: list[str] = []
    tables, groups = dbml_blocks(dbml)

    for name in db_interfaces(plan):
        if name == COMMON_INTERFACE:
            if name not in groups:
                violations.append(f"plan.md 的 `{name}` 在 schema.dbml 沒有對應的 `TableGroup {name}`")
            continue
        if not name.endswith(TABLE_SUFFIX):
            violations.append(f"plan.md 的 `{name}` 名稱不是 `<table>{TABLE_SUFFIX}` 或 `{COMMON_INTERFACE}`，無法對應到 Table")
            continue
        table = name[: -len(TABLE_SUFFIX)]
        if table not in tables:
            violations.append(f"plan.md 的 `{name}` 在 schema.dbml 沒有對應的 `Table {table}`")
            continue
        note = tables[table]
        if note is None or not note.startswith(f"`{name}`"):
            violations.append(f"`Table {table}` 的 Note 沒有以「`{name}`：」開頭")

    for table, note in tables.items():
        if note is None or REQUIREMENT_MARK not in note:
            violations.append(f"`Table {table}` 的 Note 缺少「{REQUIREMENT_MARK}」")
    for group, note in groups.items():
        if note is None or REQUIREMENT_MARK not in note:
            violations.append(f"`TableGroup {group}` 的 Note 缺少「{REQUIREMENT_MARK}」")

    common_note = groups.get(COMMON_INTERFACE) or ""
    for op in transaction_operations(openapi):
        if f"`{op}`" not in common_note:
            violations.append(f"openapi 的 `{op}` 有「{TRANSACTION_MARK}」段，但 `TableGroup {COMMON_INTERFACE}` 的 Note 沒有提到 `{op}`")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that schema.dbml covers every database interface in plan.md and every openapi transaction.")
    parser.add_argument("--plan", required=True, help="Path to plan.md produced by system-analysis")
    parser.add_argument("--dbml", required=True, help="Path to schema.dbml to check")
    parser.add_argument("--openapi", required=True, help="Path to the upstream openapi.yaml")
    args = parser.parse_args()
    paths = {"--plan": Path(args.plan), "--dbml": Path(args.dbml), "--openapi": Path(args.openapi)}
    for flag, path in paths.items():
        if not path.is_file():
            sys.stderr.write(f"error: {flag} '{path}' is not a file; pass the path to an existing file\n")
            return 2
    try:
        violations = check(paths["--plan"], paths["--dbml"], paths["--openapi"])
    except yaml.YAMLError as e:
        sys.stderr.write(f"error: '{paths['--openapi']}' is not valid YAML; fix the syntax first ({e})\n")
        return 2
    if violations:
        for v in violations:
            sys.stdout.write(f"- {v}\n")
        sys.stdout.write(f"{len(violations)} violation(s)\n")
        return 1
    sys.stdout.write("OK: no violations\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
