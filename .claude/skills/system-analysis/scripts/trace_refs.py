# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""List every truth part (requirement, operation, table, feature Example) that cites the given requirement or research IDs.

Usage:
    uv run scripts/trace_refs.py --truth specs/truth --id 002/FR-002 [--id "research 002/R7" ...]
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

REQUIREMENT_ID = re.compile(r"^\d{3}/(?:N?FR|SC)-\d{3}[a-z]?$")
RESEARCH_ID = re.compile(r"^\d{3}/R\d+$")
HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace", "query"}
EXAMPLE_KW = re.compile(r"^\s*(Example|Scenario Outline|Scenario Template|Scenario):\s*(.*)$")
RULE_KW = re.compile(r"^\s*Rule:\s*(.*)$")

# A hit: (part location in truth-delta notation, interface or module it belongs to, or "").
Hit = tuple[str, str]
# A unit: location -> (owning interface or module, text searched for IDs).
Units = dict[str, tuple[str, str]]


def normalize_id(raw: str) -> str:
    value = raw.strip()
    if value.lower().startswith("research "):
        value = value.split(None, 1)[1].strip()
    if REQUIREMENT_ID.match(value) or RESEARCH_ID.match(value):
        return value
    raise ValueError(raw)


def id_pattern(ref: str) -> re.Pattern[str]:
    # ASCII-only boundaries: CJK text may sit right next to an ID ("依002/FR-002"),
    # while 002/FR-002a and 002/R17 must not match 002/FR-002 and 002/R1.
    return re.compile(rf"(?<![0-9A-Za-z/]){re.escape(ref)}(?![0-9A-Za-z])")


# ---------------------------------------------------------------------------
# Semantic units, in the same part notation that truth-delta.md uses.

def requirement_units(text: str) -> Units:
    item = re.compile(r"^\s*(?:[-*]\s+\*\*|\|\s*`?)(\d{3}/(?:N?FR|SC)-\d{3}[a-z]?)")
    units: Units = {}
    current = None
    for line in text.split("\n"):
        m = item.match(line)
        if m:
            current = m.group(1)
            units[current] = ("", line)
        elif current and (line.startswith("#") or line.strip().startswith("|")):
            current = None
        elif current and line.strip():
            owner, body = units[current]
            units[current] = (owner, body + "\n" + line)
    return units


def techstack_units(text: str) -> Units:
    units: Units = {}
    section = ""
    for line in text.split("\n"):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or re.match(r"^\|\s*-", line):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if section and cells and cells[0] not in {"套件", "項目"}:
            units[f"{section} / {cells[0]}"] = ("", line)
    return units


def _tag_names(tags) -> str:
    names = [t.get("name") if isinstance(t, dict) else t for t in (tags or [])]
    return "、".join(str(n) for n in names if n)


def contract_units(name: str, text: str) -> Units:
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        return {name: ("", text)}
    dump = lambda obj: yaml.safe_dump(obj, allow_unicode=True, sort_keys=True, width=1000)  # noqa: E731
    units: Units = {}
    for key, value in doc.items():
        if key == "paths" and isinstance(value, dict):
            for path, item in value.items():
                for method, op in (item or {}).items():
                    if isinstance(op, dict) and method.lower() in HTTP_METHODS:
                        loc = f"operationId {op.get('operationId') or method.upper() + ' ' + path}"
                        units[f"{name} › {loc}"] = (_tag_names(op.get("tags")), dump(op))
                    else:
                        units[f"{name} › paths.{path}.{method}"] = ("", dump(op))
        elif key == "operations" and isinstance(value, dict):
            for op_id, op in value.items():
                units[f"{name} › operations.{op_id}"] = (_tag_names((op or {}).get("tags")), dump(op))
        elif key in {"channels", "tags"} and isinstance(value, (dict, list)):
            entries = value.items() if isinstance(value, dict) else ((t.get("name"), t) for t in value)
            for entry_name, entry in entries:
                owner = str(entry_name) if key == "tags" else ""
                units[f"{name} › {key}.{entry_name}"] = (owner, dump(entry))
        elif key == "components" and isinstance(value, dict):
            for group, entries in value.items():
                for entry_name, entry in (entries or {}).items():
                    units[f"{name} › components.{group}.{entry_name}"] = ("", dump(entry))
        else:
            units[f"{name} › {key}"] = ("", dump(value))
    return units


def _code_of(line: str, in_triple: bool) -> tuple[str, bool]:
    # Text of the line outside ''' strings and quoted literals, and the triple-quote state after it.
    out, parts = [], line.split("'''")
    inside = in_triple
    for i, part in enumerate(parts):
        inside = in_triple if i == 0 else not inside
        if not inside:
            out.append(re.sub(r"'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"|`[^`]*`", "", part))
    return "".join(out), (in_triple if len(parts) % 2 == 1 else not in_triple)


def dbml_units(name: str, text: str) -> Units:
    block_start = re.compile(r'^(Table|TableGroup|Project|Enum)\s+("([^"]+)"|[^\s{\[]+)')
    column = re.compile(r'^("([^"]+)"|[^\s\[{}:]+)\s+\S')
    units: Units = {}
    in_triple, depth, current, body = False, 0, None, []

    def owner_of(block: str) -> str:
        if block.startswith("Table "):
            return f"{block[6:]} 資料表介面"
        if block.startswith("TableGroup "):
            return block[11:]
        return ""

    for line in text.split("\n"):
        starts_in_triple = in_triple
        code, in_triple = _code_of(line, in_triple)
        s = line.strip()
        if current is None:
            m = block_start.match(s) if not starts_in_triple else None
            if m and "{" in code:
                kind, label = m.group(1), m.group(3) or m.group(2)
                current = f"{kind} {label}" if kind != "Project" else "Project"
                body, depth = [line], code.count("{") - code.count("}")
            elif s.startswith("Ref") and not starts_in_triple:
                units[f"{name} › Ref {' '.join(s.split())}"] = ("", s)
            if current is None or depth > 0:
                continue
        else:
            col = column.match(s) if (current.startswith("Table ") and depth == 1 and not starts_in_triple) else None
            if col and not re.match(r"^(Note|note|indexes)\b", s):
                units[f"{name} › {current}.{col.group(2) or col.group(1)}"] = (owner_of(current), s)
            else:
                body.append(line)
            depth += code.count("{") - code.count("}")
            if depth > 0:
                continue
        units[f"{name} › {current}"] = (owner_of(current), "\n".join(body))
        current = None
    return units


def feature_units(rel: str, text: str) -> Units:
    module = rel.rsplit("/", 1)[0]
    units: dict[str, list[str]] = {f"{rel} › Feature": []}
    rule, current, pending = None, f"{rel} › Feature", []
    for line in text.split("\n"):
        if line.strip().startswith("@"):
            pending.append(line)
            continue
        m_rule, m_ex = RULE_KW.match(line), EXAMPLE_KW.match(line)
        if m_rule:
            rule = m_rule.group(1).strip()
            current = f"{rel} › Rule: {rule}"
            units.setdefault(current, []).extend(pending + [line])
        elif m_ex:
            label = f"{m_ex.group(1)}: {m_ex.group(2).strip()}"
            current = f"{rel} › Rule: {rule} › {label}" if rule else f"{rel} › {label}"
            units.setdefault(current, []).extend(pending + [line])
        else:
            units[current].extend(pending + [line])
        pending = []
    return {k: (module, "\n".join(v)) for k, v in units.items()}


def dsl_units(rel: str, text: str) -> Units:
    module = rel.rsplit("/", 1)[0]
    units: Units = {}
    keyword = None
    for line in text.split("\n"):
        heading = re.match(r"^## (Given|When|Then) 句型", line)
        if heading:
            keyword = heading.group(1)
            continue
        if line.startswith("## "):
            keyword = None
        row = re.match(r"^\| `([^`]+)` \|", line)
        loc = f"{rel} › {keyword} › {row.group(1)}" if keyword and row else f"{rel} › 說明"
        owner, body = units.get(loc, (module, ""))
        units[loc] = (owner, body + "\n" + line)
    return units


# ---------------------------------------------------------------------------

def collect(truth: Path) -> dict[str, Units]:
    # Area heading -> semantic units of every truth file in that area.
    areas: dict[str, Units] = {"requirements.md": {}, "techstack.md": {}, "contracts/": {}, "data/": {}, "features/": {}}
    req = truth / "requirements.md"
    if req.is_file():
        areas["requirements.md"] = requirement_units(req.read_text(encoding="utf-8"))
    tech = truth / "techstack.md"
    if tech.is_file():
        areas["techstack.md"] = techstack_units(tech.read_text(encoding="utf-8"))
    for area, suffixes, parse in (
        ("contracts/", (".yaml", ".yml"), contract_units),
        ("data/", (".dbml",), dbml_units),
    ):
        root = truth / area
        for f in sorted(root.rglob("*")) if root.is_dir() else []:
            if f.is_file() and f.suffix in suffixes:
                rel = f.relative_to(root).as_posix()
                try:
                    areas[area].update(parse(rel, f.read_text(encoding="utf-8")))
                except yaml.YAMLError as exc:
                    raise SystemExit(f"error: cannot parse '{f}' as YAML ({exc}); fix the contract file first")
    root = truth / "features"
    for f in sorted(root.rglob("*")) if root.is_dir() else []:
        if not f.is_file():
            continue
        rel = f.relative_to(root).as_posix()
        if f.suffix == ".feature":
            areas["features/"].update(feature_units(rel, f.read_text(encoding="utf-8")))
        elif f.name == "dsl.md":
            areas["features/"].update(dsl_units(rel, f.read_text(encoding="utf-8")))
    return areas


def trace(areas: dict[str, Units], ref: str) -> dict[str, list[Hit]]:
    pattern = id_pattern(ref)
    hits: dict[str, list[Hit]] = {}
    for area, units in areas.items():
        for loc, (owner, body) in units.items():
            if area == "requirements.md" and loc == ref:
                continue  # the requirement's own definition is not a reference
            if pattern.search(body):
                hits.setdefault(area, []).append((loc, owner))
    return hits


def render(ref: str, hits: dict[str, list[Hit]], defined: bool | None) -> list[str]:
    owner_label = {"contracts/": "介面", "data/": "介面", "features/": "模組"}
    lines = [f"## {ref}"]
    if defined is False:
        lines.append("- 注意：specs/truth/requirements.md 沒有這個編號")
    if not hits:
        lines.append("- （truth 中沒有引用）")
    for area, items in hits.items():
        lines.append(f"### {area}")
        for loc, owner in items:
            suffix = f"（{owner_label[area]}：{owner}）" if owner and area in owner_label else ""
            lines.append(f"- `{loc}`{suffix}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--truth", required=True, type=Path, help="Path to specs/truth")
    parser.add_argument("--id", dest="ids", action="append", required=True,
                        help="Prefixed requirement ID (002/FR-002) or research ID (research 002/R7); repeatable")
    args = parser.parse_args()

    if not args.truth.is_dir():
        sys.stderr.write(f"error: '{args.truth}' is not a directory; pass the repository's specs/truth\n")
        return 2
    refs = []
    for raw in args.ids:
        try:
            refs.append(normalize_id(raw))
        except ValueError:
            sys.stderr.write(f"error: '{raw}' is not a prefixed ID; use NNN/FR-nnn, NNN/NFR-nnn, NNN/SC-nnn or research NNN/Rn\n")
            return 2

    areas = collect(args.truth)
    has_requirements = (args.truth / "requirements.md").is_file()
    if not has_requirements:
        sys.stderr.write(f"warning: '{args.truth / 'requirements.md'}' not found; requirement existence is not checked\n")
    out: list[str] = []
    for ref in dict.fromkeys(refs):
        defined = None
        if has_requirements and REQUIREMENT_ID.match(ref):
            defined = ref in areas["requirements.md"]
        out += render(ref, trace(areas, ref), defined) + [""]
    sys.stdout.write("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
