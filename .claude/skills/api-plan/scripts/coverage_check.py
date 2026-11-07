# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0,<7"]
# ///
"""Check that openapi.yaml / asyncapi.yaml cover every backend interface in plan.md and document each error.

Usage:
    uv run scripts/coverage_check.py --plan <plan.md> --openapi <openapi.yaml> [--asyncapi <asyncapi.yaml>]
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

BACKEND = "後端端點"
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace", "query")
# Inventory item in plan.md: "N. `<interface>`" followed by "- 端點類型：`<type>`".
_ITEM = re.compile(r"(?m)^\d+\.\s+`(?P<name>[^`]+)`\s*\n\s+-\s+端點類型：`(?P<type>[^`]+)`")
# An error line in a response description: "- `ERROR_CODE`：<condition>".
_ERROR_LINE = re.compile(r"`[A-Z][A-Z0-9_]*`：\S")
REQ_MARK = "**對應需求**"


def backend_interfaces(plan: Path) -> list[str]:
    text = plan.read_text(encoding="utf-8")
    return [m.group("name") for m in _ITEM.finditer(text) if m.group("type") == BACKEND]


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.stderr.write(f"error: '{path}' is not valid YAML ({exc}); fix the syntax and rerun\n")
        sys.exit(2)
    return data or {}


def check_openapi(doc: dict) -> tuple[set[str], list[str]]:
    tags = {t.get("name") for t in doc.get("tags", [])}
    problems = []
    for path, item in (doc.get("paths") or {}).items():
        for method in HTTP_METHODS:
            op = item.get(method)
            if not op:
                continue
            label = op.get("operationId") or f"{method.upper()} {path}"
            tags.update(op.get("tags", []))
            if REQ_MARK not in (op.get("description") or ""):
                problems.append(f"openapi {label}: description 缺少「{REQ_MARK}」")
            for status, resp in (op.get("responses") or {}).items():
                if str(status).startswith("2") or "$ref" in resp:
                    continue
                if not _ERROR_LINE.search(resp.get("description") or ""):
                    problems.append(f"openapi {label} {status}: 錯誤回應缺少「- `錯誤碼`：發生情況」")
    for name, resp in ((doc.get("components") or {}).get("responses") or {}).items():
        if not _ERROR_LINE.search(resp.get("description") or ""):
            problems.append(f"openapi components.responses.{name}: 缺少「- `錯誤碼`：發生情況」")
    return tags, problems


def check_asyncapi(doc: dict) -> tuple[set[str], list[str]]:
    tags = {t.get("name") for t in (doc.get("info") or {}).get("tags", [])}
    problems = []
    for op_id, op in (doc.get("operations") or {}).items():
        tags.update(t.get("name") for t in op.get("tags", []))
        if REQ_MARK not in (op.get("description") or ""):
            problems.append(f"asyncapi {op_id}: description 缺少「{REQ_MARK}」")
    return tags, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True, type=Path, help="Path to plan.md")
    parser.add_argument("--openapi", required=True, type=Path, help="Path to openapi.yaml")
    parser.add_argument("--asyncapi", type=Path, help="Path to asyncapi.yaml, if real-time events exist")
    args = parser.parse_args()

    for path in (args.plan, args.openapi, args.asyncapi):
        if path is not None and not path.is_file():
            sys.stderr.write(f"error: '{path}' is not a file; check the path passed by the caller\n")
            return 2

    interfaces = backend_interfaces(args.plan)
    if not interfaces:
        sys.stderr.write(f"error: no `{BACKEND}` interface found in '{args.plan}'; check its 系統介面的盤點 section\n")
        return 2

    tags, problems = check_openapi(load_yaml(args.openapi))
    if args.asyncapi:
        async_tags, async_problems = check_asyncapi(load_yaml(args.asyncapi))
        tags |= async_tags
        problems += async_problems
    problems = [f"plan.md `{name}`: openapi / asyncapi 沒有同名 tag" for name in interfaces if name not in tags] + problems

    if problems:
        sys.stdout.write("\n".join(problems) + "\n")
        return 1
    sys.stdout.write(f"ok: {len(interfaces)} 個後端介面皆有對應 tag，API 與錯誤回應說明完整\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
