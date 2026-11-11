# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0,<7"]
# ///
"""Check that frontend.md and prototype/ cover every frontend interface in plan.md and every contract change of this plan, citing only existing contracts.

Usage:
    uv run scripts/coverage_check.py --plan <plan.md> --frontend <frontend.md> --prototype <prototype-dir> [--openapi <openapi.yaml>] [--asyncapi <asyncapi.yaml>] [--delta <truth-delta.md>]
"""
import argparse
import re
import sys
import tomllib
from collections import Counter
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

FRONTEND = "前端端點"
EXISTING = ("修改既有", "刪除既有")
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace", "query")
# Inventory item in plan.md: "N. `<interface>`" followed by its "- key：value" lines.
_ITEM = re.compile(r"^\s*\d+\.\s+`(?P<name>[^`]+)`\s*$")
_FIELD = re.compile(r"^\s+-\s+(?P<key>端點類型|異動)：\s*`?(?P<value>[^`\n]+?)`?\s*$")
_PAGE_REF = re.compile(r"`prototype/(?P<file>[^`]+\.html)`")
_CODE = re.compile(r"`([^`]+)`")
CONTRACTS_HEADING = "## /api-plan — truth/contracts/"
NO_SCREEN_IMPACT = "不影響畫面的契約異動："
# Contract parts the screens cite by name: HTTP operationIds and asyncapi message names.
_DELTA_PART = re.compile(r"› (?:operationId (?P<op>\S+)|components\.messages\.(?P<msg>\S+))$")


def frontend_interfaces(plan: Path) -> dict[str, str]:
    # Interface name -> 異動 (新增 when the field is absent) for every 前端端點 interface.
    found: dict[str, dict[str, str]] = {}
    current = None
    for line in plan.read_text(encoding="utf-8").splitlines():
        m = _ITEM.match(line)
        if m:
            current = m.group("name").strip()
            found[current] = {}
            continue
        m = _FIELD.match(line)
        if m and current is not None:
            found[current][m.group("key")] = m.group("value").strip()
    return {n: f.get("異動", "新增") for n, f in found.items() if f.get("端點類型") == FRONTEND}


def table_cells(text: str, header: tuple[str, str], column: int) -> list[str]:
    # Collect one column of every markdown table whose first two header cells match.
    cells, inside = [], False
    for line in text.splitlines():
        row = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else None
        if row is None:
            inside = False
        elif tuple(row[:2]) == header:
            inside = True
        elif inside and not set(line.replace("|", "").strip()) <= set("-: "):
            cells.append(row[column] if column < len(row) else "")
    return cells


def load_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        sys.stderr.write(f"error: '{path}' is not valid YAML ({exc}); fix the syntax and rerun\n")
        sys.exit(2)


def operation_ids(doc: dict) -> set[str]:
    return {
        op["operationId"]
        for item in (doc.get("paths") or {}).values()
        for method in HTTP_METHODS
        if isinstance(op := item.get(method), dict) and "operationId" in op
    }


def message_names(doc: dict) -> set[str]:
    return set(((doc.get("components") or {}).get("messages") or {}).keys())


def contract_changes(delta: Path) -> list[tuple[str, str]]:
    # (action, operationId or message name) for every row of the contracts section of truth-delta.md.
    rows, inside = [], False
    for line in delta.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.strip() == CONTRACTS_HEADING
            continue
        if not inside or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] not in ("ADD", "MODIFY", "DELETE"):
            continue
        m = _DELTA_PART.search(cells[1].strip("`"))
        if m:
            rows.append((cells[0], m.group("op") or m.group("msg")))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True, type=Path, help="Path to plan.md")
    parser.add_argument("--frontend", required=True, type=Path, help="Path to <plan>/ui/frontend.md")
    parser.add_argument("--prototype", required=True, type=Path, help="Path to the <plan>/ui/prototype directory")
    parser.add_argument("--openapi", type=Path, help="Path to specs/truth/contracts/openapi.yaml")
    parser.add_argument("--asyncapi", type=Path, help="Path to specs/truth/contracts/asyncapi.yaml")
    parser.add_argument("--delta", type=Path, help="Path to <plan>/truth-delta.md, to check this plan's contract changes")
    args = parser.parse_args()

    for path in (args.plan, args.frontend, args.openapi, args.asyncapi, args.delta):
        if path is not None and not path.is_file():
            sys.stderr.write(f"error: '{path}' is not a file; check the path passed by the caller\n")
            return 2
    if not args.prototype.is_dir():
        sys.stderr.write(f"error: '{args.prototype}' is not a directory; write the prototype pages first\n")
        return 2

    interfaces = frontend_interfaces(args.plan)
    if not interfaces:
        sys.stderr.write(f"error: no `{FRONTEND}` interface found in '{args.plan}'; check its 系統介面的盤點 section\n")
        return 2
    text = args.frontend.read_text(encoding="utf-8")
    problems = []

    changed = {name for cell in table_cells(text, ("畫面", "對應介面"), 1) for name in _CODE.findall(cell)}
    for name, change in interfaces.items():
        if change != "刪除既有" and f"## {name}" not in text and f"對應介面：`{name}`" not in text:
            problems.append(f"plan.md `{name}`: frontend.md 沒有「## {name}」段落或「對應介面：`{name}`」")
        if change in EXISTING and name not in changed:
            problems.append(f"plan.md `{name}`（{change}）: frontend.md「本次異動的既有畫面」表的對應介面欄沒有列出")

    if not (args.prototype / "index.html").is_file():
        problems.append("prototype: 缺少入口 index.html")
    for page in sorted({m.group("file") for m in _PAGE_REF.finditer(text)}):
        if not (args.prototype / page).is_file():
            problems.append(f"frontend.md `prototype/{page}`: 檔案不存在")

    if args.openapi:
        known = operation_ids(load_yaml(args.openapi))
        # The first code span of a 呼叫 cell is the operationId; later spans are its parameters.
        for cell in table_cells(text, ("操作", "呼叫"), 1):
            for ref in _CODE.findall(cell)[:1]:
                if ref not in known:
                    problems.append(f"frontend.md 呼叫 `{ref}`: openapi.yaml 沒有此 operationId")
    if args.asyncapi:
        known = message_names(load_yaml(args.asyncapi))
        for cell in table_cells(text, ("事件", "畫面反應"), 0):
            for ref in _CODE.findall(cell):
                if ref not in known:
                    problems.append(f"frontend.md 事件 `{ref}`: asyncapi.yaml 沒有此 message")
        # The first code span of a 送出訊息 cell is the message name; later spans are its fields.
        for cell in table_cells(text, ("操作", "送出訊息"), 1):
            for ref in _CODE.findall(cell)[:1]:
                if ref not in known:
                    problems.append(f"frontend.md 送出訊息 `{ref}`: asyncapi.yaml 沒有此 message")

    if args.delta:
        cited = Counter(_CODE.findall(text))
        # The 現況 column of the changed-screen table may still name what this plan deletes.
        before = Counter(ref for cell in table_cells(text, ("畫面", "對應介面"), 3) for ref in _CODE.findall(cell))
        exempt = {
            ref
            for line in text.splitlines()
            if line.strip().startswith(f"- {NO_SCREEN_IMPACT}")
            for ref in _CODE.findall(line)
        }
        for action, ref in contract_changes(args.delta):
            if action == "DELETE" and ref not in exempt and cited[ref] > before[ref]:
                problems.append(f"truth-delta DELETE `{ref}`: 契約已刪除，frontend.md 仍引用")
            elif action != "DELETE" and ref not in cited:
                problems.append(f"truth-delta {action} `{ref}`: frontend.md 沒有引用，也沒有列在「{NO_SCREEN_IMPACT}」")

    if problems:
        sys.stdout.write("\n".join(problems) + "\n")
        return 1
    sys.stdout.write(f"ok: {len(interfaces)} 個前端介面皆有段落，雛形檔、引用的契約與本次契約異動皆已涵蓋\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
