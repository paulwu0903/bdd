# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0,<7"]
# ///
"""Check that the truth contracts match the backend interfaces of plan.md, cite existing prefixed requirements, keep no orphan components and keep Error codes in sync.

Usage:
    uv run scripts/coverage_check.py --plan <plan.md> --openapi <openapi.yaml> [--asyncapi <asyncapi.yaml>] [--requirements <requirements.md>]
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
DELETED = "刪除既有"
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace", "query")
# Inventory item in plan.md: "N. `<interface>`" followed by its "- key：value" lines.
_ITEM = re.compile(r"^\s*\d+\.\s+`(?P<name>[^`]+)`\s*$")
_FIELD = re.compile(r"^\s+-\s+(?P<key>端點類型|異動)：\s*`?(?P<value>[^`\n]+?)`?\s*$")
# An error line in a response description: "- `ERROR_CODE`：<condition>".
_ERROR_LINE = re.compile(r"`([A-Z][A-Z0-9_]*)`：\S")
_REQ_LINE = re.compile(r"\*\*對應需求\*\*：(?P<ids>[^\n]*)")
_PREFIXED = re.compile(r"^\d{3}/(?:N?FR|SC)-\d{3}[a-z]?$")
_REQ_DEF = re.compile(r"^\s*(?:[-*]\s+\*\*|\|\s*`?)(\d{3}/(?:N?FR|SC)-\d{3}[a-z]?)", re.M)
_REF = re.compile(r"#/components/(?P<group>[A-Za-z]+)/(?P<name>[^'\"\s/]+)")
REQ_MARK = "**對應需求**"
CHECKED_GROUPS = ("schemas", "parameters", "responses")


def backend_interfaces(plan: Path) -> dict[str, str]:
    # Interface name -> 異動 (新增 when the field is absent, as in plans written before the field existed).
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
    return {n: f.get("異動", "新增") for n, f in found.items() if f.get("端點類型") == BACKEND}


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.stderr.write(f"error: '{path}' is not valid YAML ({exc}); fix the syntax and rerun\n")
        sys.exit(2)
    return data or {}


def operations(doc: dict) -> list[tuple[str, dict]]:
    ops = []
    for path, item in (doc.get("paths") or {}).items():
        for method in HTTP_METHODS:
            op = (item or {}).get(method)
            if isinstance(op, dict):
                ops.append((op.get("operationId") or f"{method.upper()} {path}", op))
    return ops


def requirement_ids(description: str) -> list[str]:
    m = _REQ_LINE.search(description or "")
    if not m:
        return []
    return [t for t in re.split(r"[、，,；;\s]+", m.group("ids").strip().rstrip("。")) if t]


def check_requirements(label: str, description: str, known: set[str] | None) -> list[str]:
    problems = []
    if REQ_MARK not in (description or ""):
        return [f"{label}: description 缺少「{REQ_MARK}」"]
    for ref in requirement_ids(description):
        if not _PREFIXED.match(ref):
            problems.append(f"{label}: 對應需求 `{ref}` 不是帶 plan 前綴的編號（NNN/FR-nnn）")
        elif known is not None and ref not in known:
            problems.append(f"{label}: 對應需求 `{ref}` 不在 requirements.md 中（已刪除或編號錯誤）")
    return problems


def response_codes(description: str) -> set[str]:
    codes = set()
    for line in (description or "").splitlines():
        m = re.match(r"^\s*-\s*((?:`[A-Z][A-Z0-9_]*`(?:、)?)+)：", line)
        if m:
            codes.update(re.findall(r"`([A-Z][A-Z0-9_]*)`", m.group(1)))
    return codes


def check_openapi(doc: dict, known: set[str] | None) -> tuple[dict[str, set[str]], list[str]]:
    # Return tag -> operationIds tagged with it (declared tags map to an empty set), and problems.
    tags: dict[str, set[str]] = {t.get("name"): set() for t in doc.get("tags", []) if isinstance(t, dict)}
    problems: list[str] = []
    listed_codes: set[str] = set()
    for label, op in operations(doc):
        for tag in op.get("tags", []):
            tags.setdefault(tag, set()).add(label)
        problems += check_requirements(f"openapi {label}", op.get("description") or "", known)
        for status, resp in (op.get("responses") or {}).items():
            if str(status).startswith("2") or not isinstance(resp, dict) or "$ref" in resp:
                continue
            if not _ERROR_LINE.search(resp.get("description") or ""):
                problems.append(f"openapi {label} {status}: 錯誤回應缺少「- `錯誤碼`：發生情況」")
            listed_codes |= response_codes(resp.get("description") or "")
    components = doc.get("components") or {}
    for name, resp in (components.get("responses") or {}).items():
        if not _ERROR_LINE.search((resp or {}).get("description") or ""):
            problems.append(f"openapi components.responses.{name}: 缺少「- `錯誤碼`：發生情況」")
        listed_codes |= response_codes((resp or {}).get("description") or "")

    # Orphan components: an entry no $ref anywhere else in the document points to.
    text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=10_000)
    refs = {(m.group("group"), m.group("name")) for m in _REF.finditer(text)}
    for group in CHECKED_GROUPS:
        for name in (components.get(group) or {}):
            if (group, name) not in refs:
                problems.append(f"openapi components.{group}.{name}: 沒有任何 $ref 引用（孤兒，刪除或補上引用）")

    error = (components.get("schemas") or {}).get("Error")
    enum = set((((error or {}).get("properties") or {}).get("code") or {}).get("enum") or [])
    if listed_codes and not enum:
        problems.append("openapi components.schemas.Error: 缺少 `code` 的 enum，無法收錄各回應列出的錯誤碼")
    else:
        for code in sorted(listed_codes - enum):
            problems.append(f"openapi `{code}`: 回應有列出，但 `Error.code` 的 enum 沒有收錄")
        for code in sorted(enum - listed_codes):
            problems.append(f"openapi `{code}`: `Error.code` 的 enum 有收錄，但沒有任何回應列出發生情況")
    return tags, problems


def check_asyncapi(doc: dict, known: set[str] | None) -> tuple[dict[str, set[str]], list[str]]:
    tags: dict[str, set[str]] = {t.get("name"): set() for t in (doc.get("info") or {}).get("tags", []) if isinstance(t, dict)}
    problems: list[str] = []
    for op_id, op in (doc.get("operations") or {}).items():
        for tag in (op or {}).get("tags", []):
            tags.setdefault(tag.get("name") if isinstance(tag, dict) else tag, set()).add(op_id)
        problems += check_requirements(f"asyncapi {op_id}", (op or {}).get("description") or "", known)
    return tags, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True, type=Path, help="Path to plan.md")
    parser.add_argument("--openapi", required=True, type=Path, help="Path to specs/truth/contracts/openapi.yaml")
    parser.add_argument("--asyncapi", type=Path, help="Path to specs/truth/contracts/asyncapi.yaml, if real-time events exist")
    parser.add_argument("--requirements", type=Path, help="Path to specs/truth/requirements.md")
    args = parser.parse_args()

    for path in (args.plan, args.openapi, args.asyncapi):
        if path is not None and not path.is_file():
            sys.stderr.write(f"error: '{path}' is not a file; check the path passed by the caller\n")
            return 2

    interfaces = backend_interfaces(args.plan)
    if not interfaces:
        sys.stderr.write(f"error: no `{BACKEND}` interface found in '{args.plan}'; check its 系統介面的盤點 section\n")
        return 2

    known = None
    if args.requirements is not None and args.requirements.is_file():
        known = set(_REQ_DEF.findall(args.requirements.read_text(encoding="utf-8")))
    else:
        sys.stderr.write("warning: requirements.md not given or not found; 對應需求 existence is not checked\n")

    tags, problems = check_openapi(load_yaml(args.openapi), known)
    if args.asyncapi:
        async_tags, async_problems = check_asyncapi(load_yaml(args.asyncapi), known)
        for name, ops in async_tags.items():
            tags.setdefault(name, set()).update(ops)
        problems += async_problems

    head = []
    for name, change in interfaces.items():
        if change == DELETED:
            if name in tags:
                left = "、".join(sorted(tags[name])) or "tag 宣告"
                head.append(f"plan.md `{name}`（{DELETED}）: openapi / asyncapi 仍有同名 tag 或 operation：{left}")
        elif name not in tags:
            head.append(f"plan.md `{name}`（{change}）: openapi / asyncapi 沒有同名 tag")
    problems = head + problems

    if problems:
        sys.stdout.write("\n".join(problems) + "\n")
        return 1
    sys.stdout.write(f"ok: {len(interfaces)} 個後端介面與 tag 一致，對應需求、錯誤碼與 components 引用皆完整\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
