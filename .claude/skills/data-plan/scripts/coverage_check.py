# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6,<7",
# ]
# ///
"""Check that the truth schema.dbml matches the database interfaces of plan.md and stays consistent with the truth contracts after in-place edits.

Usage:
    uv run scripts/coverage_check.py --plan <plan.md> --dbml <schema.dbml> --openapi <openapi.yaml> [--asyncapi <asyncapi.yaml>] [--requirements <requirements.md>]
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
DELETED = "刪除既有"
COMMON_INTERFACE = "資料庫共通介面"
TABLE_SUFFIX = " 資料表介面"
REQUIREMENT_MARK = "**對應需求**"
TRANSACTION_MARK = "**交易**"
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace", "query")

# "1. `products 資料表介面`" in the interface inventory of plan.md, followed by "- key：value" lines.
_ITEM = re.compile(r"^\s*\d+\.\s+`([^`]+)`\s*$")
_FIELD = re.compile(r"^\s+-\s+(端點類型|異動)：\s*`?([^`\n]+?)`?\s*$")
# "Table name {", "Table "name" as alias [settings] {", "TableGroup name {".
_BLOCK = re.compile(r'(?im)^\s*(tablegroup|table)\s+("[^"]+"|[^\s{\[]+)(?:\s+as\s+\S+)?\s*(?:\[[^\]]*\])?\s*\{')
_NOTE = re.compile(r"(?is)^\s*note\s*(?::\s*|\{\s*)('''(.*?)'''|'((?:[^'\\\n]|\\.)*)')", re.M)
_COLUMN = re.compile(r'^\s*("[^"]+"|[A-Za-z_]\w*)\s+\S')
_ERROR_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
_REQ_LINE = re.compile(r"\*\*對應需求\*\*：(?P<ids>[^\n]*)")
_PREFIXED = re.compile(r"^\d{3}/(?:N?FR|SC)-\d{3}[a-z]?$")
_REQ_DEF = re.compile(r"^\s*(?:[-*]\s+\*\*|\|\s*`?)(\d{3}/(?:N?FR|SC)-\d{3}[a-z]?)", re.M)
# A transaction line in the TableGroup Note: "- `opA`、`opB`：steps".
_TX_LINE = re.compile(r"^\s*-\s*((?:`[^`]+`(?:、)?)+)：")
_OPERATION_ID = re.compile(r"^[a-z][A-Za-z0-9]*$")


def db_interfaces(plan: Path) -> dict[str, str]:
    # Interface name -> 異動 (新增 when the field is absent) for every 資料庫端點 interface.
    found: dict[str, dict[str, str]] = {}
    current = None
    for line in plan.read_text(encoding="utf-8").splitlines():
        m = _ITEM.match(line)
        if m:
            current = m.group(1).strip()
            found[current] = {}
            continue
        m = _FIELD.match(line)
        if m and current is not None:
            found[current][m.group(1)] = m.group(2).strip()
    return {n: f.get("異動", "新增") for n, f in found.items() if f.get("端點類型") == DB_ENDPOINT}


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


class Block:
    def __init__(self, kind: str, name: str, body: str):
        self.kind, self.name, self.body = kind, name, body
        note = _NOTE.search(body)
        self.note = None if note is None else (note.group(2) if note.group(2) is not None else note.group(3)).strip()

    def top_lines(self) -> list[str]:
        # Lines at depth 1 of the block, outside ''' strings: column definitions or group members.
        lines, depth, in_triple = [], 0, False
        for line in self.body.splitlines():
            starts_in_triple = in_triple
            if line.count("'''") % 2 == 1:
                in_triple = not in_triple
            if starts_in_triple or "'''" in line:
                continue
            if depth == 0 and line.strip() and not re.match(r"^\s*(Note|note|indexes)\b", line):
                lines.append(line)
            code = re.sub(r"'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"", "", line)
            depth += code.count("{") - code.count("}")
        return lines


def dbml_blocks(dbml: Path) -> tuple[dict[str, Block], dict[str, Block]]:
    text = dbml.read_text(encoding="utf-8")
    tables: dict[str, Block] = {}
    groups: dict[str, Block] = {}
    pos = 0
    while True:
        m = _BLOCK.search(text, pos)
        if not m:
            break
        end = _block_end(text, m.end())
        name = m.group(2).strip('"')
        kind = m.group(1).lower()
        block = Block(kind, name, text[m.end():end - 1])
        (groups if kind == "tablegroup" else tables)[name] = block
        pos = end
    return tables, groups


def openapi_operations(doc: dict) -> dict[str, bool]:
    # operationId -> whether its description carries a **交易** section.
    ops: dict[str, bool] = {}
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        candidates = [(m, item[m]) for m in HTTP_METHODS if isinstance(item.get(m), dict)]
        candidates += [(m, op) for m, op in (item.get("additionalOperations") or {}).items() if isinstance(op, dict)]
        for method, op in candidates:
            ops[op.get("operationId") or f"{method.upper()} {path}"] = TRANSACTION_MARK in str(op.get("description") or "")
    return ops


def error_enum(doc: dict) -> set[str]:
    error = ((doc.get("components") or {}).get("schemas") or {}).get("Error") or {}
    return set(((error.get("properties") or {}).get("code") or {}).get("enum") or [])


def transaction_refs(note: str) -> list[str]:
    # operationIds named at the start of each top-level line in the **交易** section of a TableGroup Note.
    refs, inside, indent = [], False, None
    for line in note.splitlines():
        stripped = line.strip()
        heading = re.match(r"^\*\*([^*]+)\*\*", stripped)
        if heading:
            inside, indent = stripped == TRANSACTION_MARK, None
            continue
        m = _TX_LINE.match(line) if inside else None
        if not m:
            continue
        depth = len(line) - len(line.lstrip())
        indent = depth if indent is None else indent
        if depth == indent:
            refs += [r for r in re.findall(r"`([^`]+)`", m.group(1)) if _OPERATION_ID.match(r)]
    return refs


def check_requirements(label: str, note: str | None, known: set[str] | None) -> list[str]:
    if note is None or REQUIREMENT_MARK not in note:
        return [f"{label} 的 Note 缺少「{REQUIREMENT_MARK}」"]
    problems = []
    for m in _REQ_LINE.finditer(note):
        for ref in (t for t in re.split(r"[、，,；;\s]+", m.group("ids").strip().rstrip("。")) if t):
            if not _PREFIXED.match(ref):
                problems.append(f"{label}: 對應需求 `{ref}` 不是帶 plan 前綴的編號（NNN/FR-nnn）")
            elif known is not None and ref not in known:
                problems.append(f"{label}: 對應需求 `{ref}` 不在 requirements.md 中（已刪除或編號錯誤）")
    return problems


def check(plan: Path, dbml: Path, openapi: dict, asyncapi: dict | None, known: set[str] | None) -> list[str]:
    violations: list[str] = []
    tables, groups = dbml_blocks(dbml)

    for name, change in db_interfaces(plan).items():
        deleted = change == DELETED
        if name == COMMON_INTERFACE:
            if not deleted and name not in groups:
                violations.append(f"plan.md 的 `{name}` 在 schema.dbml 沒有對應的 `TableGroup {name}`")
            continue
        if not name.endswith(TABLE_SUFFIX):
            violations.append(f"plan.md 的 `{name}` 名稱不是 `<table>{TABLE_SUFFIX}` 或 `{COMMON_INTERFACE}`，無法對應到 Table")
            continue
        table = name[: -len(TABLE_SUFFIX)]
        if deleted:
            if table in tables:
                violations.append(f"plan.md 的 `{name}`（{DELETED}）在 schema.dbml 仍有 `Table {table}`")
            continue
        if table not in tables:
            violations.append(f"plan.md 的 `{name}`（{change}）在 schema.dbml 沒有對應的 `Table {table}`")
            continue
        note = tables[table].note
        if note is None or not note.startswith(f"`{name}`"):
            violations.append(f"`Table {table}` 的 Note 沒有以「`{name}`：」開頭")

    for table, block in tables.items():
        violations += check_requirements(f"`Table {table}`", block.note, known)
    for group, block in groups.items():
        violations += check_requirements(f"`TableGroup {group}`", block.note, known)

    # Group members and tables must agree in both directions.
    common = groups.get(COMMON_INTERFACE)
    if common is not None:
        members = {line.strip().strip('"') for line in common.top_lines()}
        for member in sorted(members - set(tables)):
            violations.append(f"`TableGroup {COMMON_INTERFACE}` 的成員 `{member}` 沒有對應的 Table（已刪除的表要一併移出成員）")
        for table in sorted(set(tables) - members):
            violations.append(f"`Table {table}` 不在 `TableGroup {COMMON_INTERFACE}` 的成員中")

    # Transactions: every openapi transaction is written down, every written one still exists.
    ops = openapi_operations(openapi)
    async_ops = set(((asyncapi or {}).get("operations") or {}).keys())
    common_note = (common.note if common is not None else None) or ""
    for op, has_tx in ops.items():
        if has_tx and f"`{op}`" not in common_note:
            violations.append(f"openapi 的 `{op}` 有「{TRANSACTION_MARK}」段，但 `TableGroup {COMMON_INTERFACE}` 的 Note 沒有提到 `{op}`")
    for block in groups.values():
        for ref in transaction_refs(block.note or ""):
            if ref not in ops and ref not in async_ops:
                violations.append(f"`TableGroup {block.name}` 的交易段引用 `{ref}`，但 openapi / asyncapi 已沒有這個 operation")

    # Error codes named on columns must exist in Error.code.
    enum = error_enum(openapi)
    for table, block in tables.items():
        for line in block.top_lines():
            col = _COLUMN.match(line)
            if not col:
                continue
            for code in sorted(set(_ERROR_TOKEN.findall(line)) - enum):
                violations.append(f"`Table {table}.{col.group(1).strip(chr(34))}` 的 note 提到 `{code}`，但 openapi `Error.code` 的 enum 沒有這個錯誤碼")
    return violations


def load_yaml(flag: str, path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"error: {flag} '{path}' is not valid YAML; fix the syntax first ({e})\n")
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that the truth schema.dbml matches plan.md and stays consistent with the truth contracts.")
    parser.add_argument("--plan", required=True, help="Path to plan.md produced by system-analysis")
    parser.add_argument("--dbml", required=True, help="Path to specs/truth/data/schema.dbml")
    parser.add_argument("--openapi", required=True, help="Path to specs/truth/contracts/openapi.yaml")
    parser.add_argument("--asyncapi", help="Path to specs/truth/contracts/asyncapi.yaml, if real-time events exist")
    parser.add_argument("--requirements", help="Path to specs/truth/requirements.md")
    args = parser.parse_args()
    paths = {"--plan": args.plan, "--dbml": args.dbml, "--openapi": args.openapi, "--asyncapi": args.asyncapi}
    for flag, path in paths.items():
        if path is not None and not Path(path).is_file():
            sys.stderr.write(f"error: {flag} '{path}' is not a file; pass the path to an existing file\n")
            return 2
    known = None
    if args.requirements and Path(args.requirements).is_file():
        known = set(_REQ_DEF.findall(Path(args.requirements).read_text(encoding="utf-8")))
    else:
        sys.stderr.write("warning: requirements.md not given or not found; 對應需求 existence is not checked\n")
    openapi = load_yaml("--openapi", Path(args.openapi))
    asyncapi = load_yaml("--asyncapi", Path(args.asyncapi)) if args.asyncapi else None
    violations = check(Path(args.plan), Path(args.dbml), openapi, asyncapi, known)
    if violations:
        for v in violations:
            sys.stdout.write(f"- {v}\n")
        sys.stdout.write(f"{len(violations)} violation(s)\n")
        return 1
    sys.stdout.write("OK: no violations\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
