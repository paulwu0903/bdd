# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Compare a plan's truth-delta.md with the semantic-unit changes of specs/truth/ between its Base commit and the working tree.

Usage:
    uv run scripts/check_delta.py --plan <specs/plans/NNN-name> [--section requirements|techstack|contracts|data|features]
"""
import argparse
import difflib
import re
import subprocess
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

# Section key -> (heading of its table in truth-delta.md, truth path relative to the repository root).
SECTIONS = {
    "requirements": ("## /specify — truth/requirements.md", "specs/truth/requirements.md"),
    "techstack": ("## /technical-research — truth/techstack.md", "specs/truth/techstack.md"),
    "contracts": ("## /api-plan — truth/contracts/", "specs/truth/contracts"),
    "data": ("## /data-plan — truth/data/", "specs/truth/data"),
    "features": ("## /dsl-refine — truth/features/", "specs/truth/features"),
}
LOCATION_FORMAT = {
    "requirements": re.compile(r"^\d{3}/(?:N?FR|SC)-\d{3}$"),
    "techstack": re.compile(r"^.+ / .+$"),
    "contracts": re.compile(r"^\S+\.(?:ya?ml|json)(?: › .+)?$"),
    "data": re.compile(r"^\S+\.dbml(?: › .+)?$"),
    "features": re.compile(r"^[^/\s]+/.+\.(?:feature|md)(?: › .+)?$"),
}
ACTIONS = ("ADD", "MODIFY", "DELETE")
EXCERPT_LINES = 15
DIFF_LINES = 30

Units = dict[str, tuple[str, str]]  # identity -> (location shown in truth-delta.md, content)


# ---------------------------------------------------------------------------
# git access

class Repo:
    def __init__(self, root: Path, base: str):
        self.root, self.base = root, base

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, encoding="utf-8")

    def base_files(self, rel: str) -> dict[str, str]:
        # -z: raw paths; otherwise git quotes non-ASCII names (e.g. 聊天訊息/) with octal escapes.
        listed = self._git("ls-tree", "-r", "-z", "--name-only", self.base, "--", rel)
        files = {}
        for name in filter(None, listed.stdout.split("\0")):
            shown = self._git("show", f"{self.base}:{name}")
            if shown.returncode == 0:
                files[name] = shown.stdout
        return files

    def work_files(self, rel: str) -> dict[str, str]:
        path = self.root / rel
        if path.is_file():
            return {rel: path.read_text(encoding="utf-8")}
        if not path.is_dir():
            return {}
        return {
            f.relative_to(self.root).as_posix(): f.read_text(encoding="utf-8")
            for f in sorted(path.rglob("*"))
            if f.is_file() and not f.name.startswith(".")
        }


# ---------------------------------------------------------------------------
# Semantic units per truth type

def requirement_units(files: dict[str, str]) -> Units:
    units: Units = {}
    item = re.compile(r"^\s*(?:[-*]\s+\*\*|\|\s*`?)(\d{3}/(?:N?FR|SC)-\d{3})")
    for text in files.values():
        current = None
        for line in text.split("\n"):
            m = item.match(line)
            if m:
                current = m.group(1)
                units[current] = (current, line.rstrip())
            elif current and (line.startswith("#") or (line.strip().startswith("|") and not line.startswith("  "))):
                current = None
            elif current and line.strip():
                loc, content = units[current]
                units[current] = (loc, content + "\n" + line.rstrip())
    return units


def split_cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def techstack_units(files: dict[str, str]) -> Units:
    units: Units = {}
    for text in files.values():
        section, key_col = "", 0
        for line in text.split("\n"):
            if line.startswith("## "):
                section, key_col = line[3:].strip(), 0
                continue
            if not line.startswith("|") or re.match(r"^\|\s*-", line):
                continue
            cells = split_cells(line)
            if "套件" in cells or "項目" in cells:
                key_col = cells.index("套件") if "套件" in cells else cells.index("項目")
                continue
            if section and len(cells) > key_col:
                loc = f"{section} / {cells[key_col]}"
                units[loc] = (loc, " | ".join(cells))
    return units


def dump(obj) -> str:
    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=True, width=100).rstrip()


def contract_units(files: dict[str, str], root_rel: str) -> Units:
    units: Units = {}
    for name, text in files.items():
        prefix = name[len(root_rel) + 1 :]
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SystemExit(f"error: cannot parse '{name}' as YAML ({exc}); fix the contract file first")
        if not isinstance(doc, dict):
            units[prefix] = (prefix, text.rstrip())
            continue

        def add(unit: str, obj) -> None:
            loc = f"{prefix} › {unit}"
            units[loc] = (loc, dump(obj))

        for key, value in doc.items():
            if key == "paths" and isinstance(value, dict):
                for path, item in value.items():
                    for method, op in (item or {}).items():
                        if isinstance(op, dict) and method.lower() in {"get", "put", "post", "delete", "patch", "head", "options", "trace", "query"}:
                            add(f"operationId {op.get('operationId') or method.upper() + ' ' + path}", op)
                        else:
                            add(f"paths.{path}.{method}", op)
            elif key in {"channels", "operations", "tags"} and isinstance(value, (dict, list)):
                entries = value.items() if isinstance(value, dict) else ((t.get("name"), t) for t in value)
                for entry_name, entry in entries:
                    add(f"{key}.{entry_name}", entry)
            elif key == "components" and isinstance(value, dict):
                for group, entries in value.items():
                    for entry_name, entry in (entries or {}).items():
                        add(f"components.{group}.{entry_name}", entry)
            else:
                add(key, value)
    return units


def _code_of(line: str, in_triple: bool) -> tuple[str, bool]:
    """Text of the line outside ''' strings and quoted literals, and the triple-quote state after it."""
    out, parts = [], line.split("'''")
    for i, part in enumerate(parts):
        inside = in_triple if i == 0 else not inside
        if not inside:
            out.append(re.sub(r"'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"|`[^`]*`", "", part))
    return "".join(out), (in_triple if len(parts) % 2 == 1 else not in_triple)


def dbml_units(files: dict[str, str], root_rel: str) -> Units:
    units: Units = {}
    block_start = re.compile(r'^(Table|TableGroup|Project|Enum)\s+("([^"]+)"|[^\s{\[]+)')
    column = re.compile(r'^("([^"]+)"|[^\s\[{}:]+)\s+\S')
    for name, text in files.items():
        prefix = name[len(root_rel) + 1 :]
        in_triple, depth, current, body = False, 0, None, []
        for line in text.split("\n"):
            starts_in_triple = in_triple
            code, in_triple = _code_of(line, in_triple)
            s = line.strip()
            if current is None:
                m = block_start.match(s) if not starts_in_triple else None
                if m and "{" in code:
                    kind, label = m.group(1), m.group(3) or m.group(2)
                    current = f"{kind} {label}" if kind != "Project" else "Project"
                    body, depth = [line.rstrip()], code.count("{") - code.count("}")
                elif s.startswith("Ref") and not starts_in_triple:
                    loc = f"{prefix} › Ref {' '.join(s.split())}"
                    units[loc] = (loc, s)
                if current is None or depth > 0:
                    continue
            else:
                col = column.match(s) if (current.startswith("Table ") and depth == 1 and not starts_in_triple) else None
                if col and not re.match(r"^(Note|note|indexes)\b", s):
                    loc = f"{prefix} › {current}.{col.group(2) or col.group(1)}"
                    units[loc] = (loc, s)
                else:
                    body.append(line.rstrip())
                depth += code.count("{") - code.count("}")
                if depth > 0:
                    continue
            loc = f"{prefix} › {current}"
            units[loc] = (loc, "\n".join(body))
            current = None
    return units


EXAMPLE_KW = re.compile(r"^\s*(Example|Scenario Outline|Scenario Template|Scenario):\s*(.*)$")
RULE_KW = re.compile(r"^\s*Rule:\s*(.*)$")


def feature_units(rel: str, text: str) -> Units:
    units: dict[str, list[str]] = {}
    order: list[str] = []
    rule, current, pending = None, f"{rel} › Feature", []

    def start(key: str, first: list[str]) -> str:
        n, unique = 2, key
        while unique in units:
            unique, n = f"{key} #{n}", n + 1
        units[unique] = list(first)
        order.append(unique)
        return unique

    current = start(current, [])
    for line in text.split("\n"):
        if line.strip().startswith("@"):
            pending.append(line.rstrip())
            continue
        m_rule, m_ex = RULE_KW.match(line), EXAMPLE_KW.match(line)
        if m_rule:
            rule = m_rule.group(1).strip()
            current = start(f"{rel} › Rule: {rule}", pending + [line.rstrip()])
        elif m_ex:
            label = f"{m_ex.group(1)}: {m_ex.group(2).strip()}"
            key = f"{rel} › Rule: {rule} › {label}" if rule else f"{rel} › {label}"
            current = start(key, pending + [line.rstrip()])
        else:
            units[current].extend(pending + [line.rstrip()])
        pending = []
    return {k: (k, "\n".join(units[k]).strip()) for k in order}


def dsl_units(rel: str, text: str) -> Units:
    units: Units = {}
    endpoint = rel.split("/", 1)[0]
    keyword, intro, appendix = None, [], None
    for line in text.split("\n"):
        heading = re.match(r"^## (Given|When|Then) 句型", line)
        if heading:
            keyword = heading.group(1)
            continue
        if line.startswith("## "):
            keyword = None
            if line.startswith("## 附錄"):
                appendix = [line.rstrip()]
                continue
        if appendix is not None:
            appendix.append(line.rstrip())
            continue
        row = re.match(r"^\| `([^`]+)` \|", line)
        if keyword and row:
            units[f"dsl::{endpoint}::{keyword}::{row.group(1)}"] = (f"{rel} › {keyword} › {row.group(1)}", line.rstrip() + f"\n@ {rel}")
        elif keyword is None and not line.startswith("## ") and appendix is None:
            intro.append(line.rstrip())
    units[f"{rel} › 說明"] = (f"{rel} › 說明", "\n".join(intro).strip())
    if appendix is not None:
        units[f"{rel} › 附錄"] = (f"{rel} › 附錄", "\n".join(appendix).strip())
    return units


# ---------------------------------------------------------------------------
# Actual changes

def compare(before: Units, after: Units) -> list[tuple[str, str, str, str]]:
    changes = []
    for key in sorted(set(before) | set(after)):
        if key not in before:
            changes.append(("ADD", after[key][0], "", after[key][1]))
        elif key not in after:
            changes.append(("DELETE", before[key][0], before[key][1], ""))
        elif before[key][1] != after[key][1]:
            changes.append(("MODIFY", after[key][0], before[key][1], after[key][1]))
    return changes


def feature_changes(before: dict[str, str], after: dict[str, str], root_rel: str) -> list[tuple[str, str, str, str]]:
    def rel(name: str) -> str:
        return name[len(root_rel) + 1 :]

    changes, dsl_before, dsl_after = [], {}, {}
    for name in sorted(set(before) | set(after)):
        r = rel(name)
        if r.endswith("dsl.md"):
            if name in before:
                dsl_before.update(dsl_units(r, before[name]))
            if name in after:
                dsl_after.update(dsl_units(r, after[name]))
        elif r.endswith(".feature"):
            if name not in before:
                changes.append(("ADD", r, "", after[name]))
            elif name not in after:
                changes.append(("DELETE", r, before[name], ""))
            else:
                changes += compare(feature_units(r, before[name]), feature_units(r, after[name]))
    return changes + compare(dsl_before, dsl_after)


def actual_changes(repo: Repo, section: str) -> list[tuple[str, str, str, str]]:
    rel = SECTIONS[section][1]
    before, after = repo.base_files(rel), repo.work_files(rel)
    if section == "requirements":
        return compare(requirement_units(before), requirement_units(after))
    if section == "techstack":
        return compare(techstack_units(before), techstack_units(after))
    if section == "contracts":
        return compare(contract_units(before, rel), contract_units(after, rel))
    if section == "data":
        return compare(dbml_units(before, rel), dbml_units(after, rel))
    return feature_changes(before, after, rel)


# ---------------------------------------------------------------------------
# truth-delta.md rows

def header_value(text: str, name: str) -> str | None:
    m = re.search(rf"^\*\*{name}\*\*: `?([^`\n]+?)`?[ \t]*$", text, re.M)
    return m.group(1).strip() if m else None


def section_rows(text: str, heading: str) -> list[tuple[int, list[str]]] | None:
    lines = text.split("\n")
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return None
    rows = []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.startswith("## "):
            break
        if line.startswith("|") and not re.match(r"^\|\s*(-|動作\s*\|)", line):
            rows.append((i + 1, split_cells(line)))
    return rows


def normalize(location: str) -> str:
    return " ".join(location.replace("`", "").split())


def excerpt(action: str, old: str, new: str) -> list[str]:
    if action == "ADD":
        lines = new.split("\n")
        return ["    改後: " + l for l in lines[:EXCERPT_LINES]] + (["    …"] if len(lines) > EXCERPT_LINES else [])
    if action == "DELETE":
        lines = old.split("\n")
        return ["    改前: " + l for l in lines[:EXCERPT_LINES]] + (["    …"] if len(lines) > EXCERPT_LINES else [])
    diff = [l for l in difflib.unified_diff(old.split("\n"), new.split("\n"), lineterm="", n=0) if not l.startswith(("---", "+++", "@@"))]
    return ["    " + l for l in diff[:DIFF_LINES]] + (["    …"] if len(diff) > DIFF_LINES else [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a plan's truth-delta.md with the semantic-unit changes of specs/truth/ between its Base commit and the working tree.")
    parser.add_argument("--plan", required=True, help="Plan package directory, e.g. specs/plans/003-pvp-spectate")
    parser.add_argument("--section", choices=list(SECTIONS), help="Check only this section (default: all five)")
    args = parser.parse_args()

    plan = Path(args.plan).resolve()
    delta = plan / "truth-delta.md"
    if not delta.is_file():
        sys.stderr.write(f"error: '{delta}' does not exist; create it with the truth-delta skill's 建立 action (scripts/init_delta.py)\n")
        return 2
    text = delta.read_text(encoding="utf-8")
    base = header_value(text, "Base")
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=plan, capture_output=True, text=True, encoding="utf-8")
    if top.returncode != 0:
        sys.stderr.write("error: not inside a git repository; the Base comparison needs git\n")
        return 2
    root = Path(top.stdout.strip())
    if not base or subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=root, capture_output=True).returncode != 0:
        sys.stderr.write(f"error: **Base** '{base}' in {delta} is not a commit of this repository; fix the header to the commit the plan branch started from\n")
        return 2
    repo = Repo(root, base)

    problems: list[str] = []
    counts = {}
    for section in [args.section] if args.section else list(SECTIONS):
        heading = SECTIONS[section][0]
        rows = section_rows(text, heading)
        if rows is None:
            problems.append(f"[段落缺少] {section}: truth-delta.md 沒有標題 `{heading}`")
            continue
        actual = {normalize(loc): (action, old, new) for action, loc, old, new in actual_changes(repo, section)}
        seen: dict[str, int] = {}
        for line_no, cells in rows:
            if len(cells) != 4:
                problems.append(f"[格式錯誤] {section} 第 {line_no} 行：表格應為 4 欄（動作、部位、摘要、原因）")
                continue
            action, location, summary, reason = cells
            loc = normalize(location)
            if action not in ACTIONS:
                problems.append(f"[格式錯誤] {section} 第 {line_no} 行：動作 `{action}` 應為 ADD、MODIFY 或 DELETE")
            if not LOCATION_FORMAT[section].match(loc):
                problems.append(f"[部位格式] {section} 第 {line_no} 行：`{loc}` 不符合本段的部位寫法")
            if loc in seen:
                problems.append(f"[部位重複] {section} 第 {line_no} 行：`{loc}` 已在第 {seen[loc]} 行記錄")
            seen.setdefault(loc, line_no)
            if not summary or "{{" in summary:
                problems.append(f"[留空] {section} 第 {line_no} 行 `{loc}`：摘要未填")
            if not reason or "{{" in reason:
                problems.append(f"[留空] {section} 第 {line_no} 行 `{loc}`：原因未填")
            if loc in actual:
                if action in ACTIONS and actual[loc][0] != action:
                    problems.append(f"[動作不符] {section} 第 {line_no} 行 `{loc}`：記錄為 {action}，實際為 {actual[loc][0]}")
            elif LOCATION_FORMAT[section].match(loc):
                problems.append(f"[沒有異動] {section} 第 {line_no} 行 `{loc}`：Base 到工作目錄之間沒有這項異動，應刪除此列或修正部位")
        for loc, (action, old, new) in actual.items():
            if loc not in seen:
                problems.append(f"[未記錄] {section} {action} `{loc}`")
                problems.extend(excerpt(action, old, new))
        counts[section] = {a: sum(1 for v in actual.values() if v[0] == a) for a in ACTIONS}

    for line in problems:
        sys.stdout.write(line + "\n")
    summary = "；".join(f"{s} 實際 ADD {c['ADD']}／MODIFY {c['MODIFY']}／DELETE {c['DELETE']}" for s, c in counts.items())
    violations = sum(1 for p in problems if p.startswith("["))
    sys.stdout.write(f"Base {base[:12]}；{summary}；違規 {violations} 項\n")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
