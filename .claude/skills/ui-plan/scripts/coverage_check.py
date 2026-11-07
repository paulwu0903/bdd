# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0,<7"]
# ///
"""Check that frontend.md and prototype/ cover every frontend interface in plan.md and only cite existing contracts.

Usage:
    uv run scripts/coverage_check.py --plan <plan.md> --frontend <frontend.md> --prototype <prototype-dir> [--openapi <openapi.yaml>] [--asyncapi <asyncapi.yaml>]
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

FRONTEND = "前端端點"
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace", "query")
# Inventory item in plan.md: "N. `<interface>`" followed by "- 端點類型：`<type>`".
_ITEM = re.compile(r"(?m)^\d+\.\s+`(?P<name>[^`]+)`\s*\n\s+-\s+端點類型：`(?P<type>[^`]+)`")
_PAGE_REF = re.compile(r"`prototype/(?P<file>[^`]+\.html)`")
_CODE = re.compile(r"`([^`]+)`")


def frontend_interfaces(plan: Path) -> list[str]:
    text = plan.read_text(encoding="utf-8")
    return [m.group("name") for m in _ITEM.finditer(text) if m.group("type") == FRONTEND]


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True, type=Path, help="Path to plan.md")
    parser.add_argument("--frontend", required=True, type=Path, help="Path to frontend.md")
    parser.add_argument("--prototype", required=True, type=Path, help="Path to the prototype directory")
    parser.add_argument("--openapi", type=Path, help="Path to upstream openapi.yaml")
    parser.add_argument("--asyncapi", type=Path, help="Path to upstream asyncapi.yaml")
    args = parser.parse_args()

    for path in (args.plan, args.frontend, args.openapi, args.asyncapi):
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

    for name in interfaces:
        if f"## {name}" not in text and f"對應介面：`{name}`" not in text:
            problems.append(f"plan.md `{name}`: frontend.md 沒有「## {name}」段落或「對應介面：`{name}`」")

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

    if problems:
        sys.stdout.write("\n".join(problems) + "\n")
        return 1
    sys.stdout.write(f"ok: {len(interfaces)} 個前端介面皆有段落，雛形檔與引用的契約皆存在\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
