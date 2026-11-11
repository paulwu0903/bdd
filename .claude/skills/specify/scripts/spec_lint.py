# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List structural violations of a spec.md written from the specify skill's spec template.

The optional `## 既有需求異動` table is also checked against the requirements.md of the plan's Base commit
(truth-delta.md `**Base**:`); when that is unavailable, the working-tree specs/truth/requirements.md is used.

Usage:
    uv run scripts/spec_lint.py --spec <specs/plans/NNN-name/spec.md> [--requirements <requirements.md>]
"""
import argparse
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


# Fixed headings of templates/spec.md in order: (pattern, required, repeatable).
HEADINGS = [
    (r"# Feature Specification: .+", True, False),
    (r"## User Scenarios & Requirements", True, False),
    (r"### User Story \d+ - .+ \(Priority: P\d+\)", True, True),
    (r"### Edge Cases", True, False),
    (r"## Global Requirements（全域需求）", False, False),
    (r"### Functional Requirements（全域）", False, False),
    (r"### Non-Functional Requirements（全域）", False, False),
    (r"## System Constraints（系統約束）", False, False),
    (r"## Key Entities", False, False),
    (r"## Success Criteria", True, False),
    (r"### Measurable Outcomes", True, False),
    (r"## 既有需求異動", False, False),
    (r"## Assumptions", True, False),
]
_ID = r"(?:FR|NFR|SC)-\d{3}[a-z]?"
_DEF = re.compile(rf"^- \*\*({_ID})\*\*")
# A reference preceded by '/' belongs to another plan (e.g. `002/FR-002`) and is not checked against this spec.
_REF = re.compile(rf"(?<![\w/-])({_ID})(?![\w])")
_US_HEAD = re.compile(r"^### User Story (\d+) - ")
_AC = re.compile(r"^\d+\. \*\*Given\*\* .+，\*\*When\*\* .+，\*\*Then\*\* .+")
_US_FR = re.compile(r"^- \*\*FR-\d{3}[a-z]?\*\*: \S")
_US_NFR = re.compile(r"^- \*\*NFR-\d{3}[a-z]?\*\*（[^）]+）: \S")
_GLOBAL = re.compile(r"^- \*\*(?:FR|NFR)-\d{3}[a-z]?\*\*（適用：([^）]*)）: \S")
_SYSTEM = re.compile(r"^- \*\*NFR-\d{3}[a-z]?\*\*: \S")


def check_headings(lines: list[str], out: list[str]) -> None:
    # Walk headings against HEADINGS; a required entry may be skipped only after it has matched.
    pos, matched = 0, False
    for n, line in enumerate(lines, 1):
        if not line.startswith("#"):
            continue
        i = pos
        while i < len(HEADINGS):
            pattern, required, _ = HEADINGS[i]
            if re.fullmatch(pattern, line):
                break
            if required and not (i == pos and matched):
                out.append(f"line {n}: heading '{line}' appears before required heading '{pattern}'")
                return
            i += 1
        else:
            out.append(f"line {n}: heading '{line}' is not in the template or is out of order")
            return
        pos, matched = (i, True) if HEADINGS[i][2] else (i + 1, False)
    for i in range(pos, len(HEADINGS)):
        pattern, required, _ = HEADINGS[i]
        if required and not (i == pos and matched):
            out.append(f"end of file: missing required heading '{pattern}'")
            return


def sections(lines: list[str]) -> dict[str, list[tuple[int, str]]]:
    # Group lines by the nearest level-2 heading; user stories are keyed by their own heading.
    groups: dict[str, list[tuple[int, str]]] = {}
    key = ""
    for n, line in enumerate(lines, 1):
        if line.startswith("## ") or _US_HEAD.match(line) or line == "### Edge Cases":
            key = line
        groups.setdefault(key, []).append((n, line))
    return groups


def check_stories(groups: dict[str, list[tuple[int, str]]], out: list[str]) -> set[str]:
    stories: set[str] = set()
    for key, body in groups.items():
        m = _US_HEAD.match(key)
        if not m:
            continue
        us = f"US{m.group(1)}"
        stories.add(us)
        part = ""
        counts = {"ac": 0, "fr": 0, "nfr": 0}
        opened: dict[str, int] = {}
        for n, line in body:
            if line.startswith("**Acceptance Scenarios**"):
                part = "ac"
                opened[part] = n
            elif line.startswith("**Functional Requirements**"):
                part = "fr"
                opened[part] = n
            elif line.startswith("**Non-Functional Requirements**"):
                part = "nfr"
                opened[part] = n
            elif part and (line.startswith("- ") or re.match(r"\d+\. ", line)):
                ok = {"ac": _AC, "fr": _US_FR, "nfr": _US_NFR}[part].match(line)
                if ok:
                    counts[part] += 1
                else:
                    out.append(f"line {n}: {us} {part.upper()} item does not follow the template format")
        if counts["ac"] == 0:
            out.append(f"line {body[0][0]}: {us} has no Acceptance Scenario")
        if counts["fr"] + counts["nfr"] == 0:
            out.append(f"line {body[0][0]}: {us} has no FR or NFR")
        for part, label in (("fr", "Functional"), ("nfr", "Non-Functional")):
            if part in opened and counts[part] == 0:
                out.append(f"line {opened[part]}: {us} {label} Requirements section is empty; omit the whole section")
    return stories


def check_global_and_system(groups: dict[str, list[tuple[int, str]]], stories: set[str], out: list[str]) -> None:
    for n, line in groups.get("## Global Requirements（全域需求）", []):
        if not line.startswith("- **"):
            continue
        m = _GLOBAL.match(line)
        if not m:
            out.append(f"line {n}: Global item must be '- **ID**（適用：USx、USy）: ...'")
            continue
        applies = [s.strip() for s in m.group(1).split("、")]
        if "全部" in m.group(1):
            out.append(f"line {n}: 適用 must list user story numbers, not 全部")
            continue
        if len(set(applies)) < 2:
            out.append(f"line {n}: Global item must apply to at least 2 user stories; move it into its user story")
        for s in applies:
            if s not in stories:
                out.append(f"line {n}: 適用 refers to unknown user story '{s}'")
    for n, line in groups.get("## System Constraints（系統約束）", []):
        if line.startswith("- **") and not _SYSTEM.match(line):
            out.append(f"line {n}: System Constraints item must be '- **NFR-ID**: ...' without 適用")


def check_edge_cases(groups: dict[str, list[tuple[int, str]]], out: list[str]) -> None:
    # An edge case that states a MUST has to point at the FR / NFR carrying it.
    for n, line in groups.get("### Edge Cases", []):
        if line.startswith("- ") and "MUST" in line and not re.search(r"(?<![\w-])N?FR-\d{3}[a-z]?(?![\w])", line):
            out.append(f"line {n}: Edge Case states MUST without referencing the FR / NFR that carries it")


def check_ids(lines: list[str], out: list[str]) -> None:
    defined: dict[str, int] = {}
    for n, line in enumerate(lines, 1):
        m = _DEF.match(line)
        if not m:
            continue
        if m.group(1) in defined:
            out.append(f"line {n}: {m.group(1)} is already defined at line {defined[m.group(1)]}")
        else:
            defined[m.group(1)] = n
    for n, line in enumerate(lines, 1):
        for ref in _REF.findall(line):
            if ref not in defined:
                out.append(f"line {n}: {ref} is referenced but never defined")


CHANGE_HEADING = "## 既有需求異動"
CHANGE_HEADER = ["#", "動作", "既有編號", "新內容", "理由", "確認"]
_CHANGE_ID = re.compile(r"^`(\d{3})/((?:N?FR|SC)-\d{3}[a-z]?)`$")
_CONFIRM = re.compile(r"^(?:使用者於 \d{4}-\d{2}-\d{2} 確認|低風險)$")
_SEPARATOR = re.compile(r"^:?-+:?$")
# Same entry shape as truth-delta check_delta.py requirement_units.
_REQ_ITEM = re.compile(r"^\s*(?:[-*]\s+\*\*|\|\s*`?)(\d{3}/(?:N?FR|SC)-\d{3}[a-z]?)")
EMPTY = {"", "—"}


def split_cells(line: str) -> list[str]:
    # Cells of a markdown table row; '\|' is an escaped pipe inside a cell.
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def _git(cwd: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        return None
    return r.stdout if r.returncode == 0 else None


def base_requirements(spec: Path) -> tuple[str | None, str]:
    """Text of requirements.md at the plan's Base commit, falling back to the working tree; plus where it came from."""
    plan = spec.resolve().parent
    top = _git(plan, "rev-parse", "--show-toplevel")
    root = Path(top.strip()) if top else Path.cwd()
    delta = plan / "truth-delta.md"
    if top and delta.is_file():
        m = re.search(r"^\*\*Base\*\*: `?([0-9a-fA-F]{4,40})`?[ \t]*$", delta.read_text(encoding="utf-8"), re.M)
        if m:
            shown = _git(root, "show", f"{m.group(1)}:specs/truth/requirements.md")
            if shown is not None:
                return shown, f"Base {m.group(1)[:12]}"
    work = root / "specs" / "truth" / "requirements.md"
    if work.is_file():
        return work.read_text(encoding="utf-8"), work.as_posix()
    return None, work.as_posix()


def check_changes(groups: dict[str, list[tuple[int, str]]], spec: Path, override: Path | None, out: list[str]) -> None:
    body = groups.get(CHANGE_HEADING)
    if body is None:
        return
    own = m.group(1) if (m := re.match(r"^(\d{3})-", spec.resolve().parent.name)) else None
    table = [(n, line) for n, line in body[1:] if line.strip()]
    for n, line in table:
        if not line.lstrip().startswith("|"):
            out.append(f"line {n}: {CHANGE_HEADING} must contain only its table; move this text elsewhere")
    rows = [(n, split_cells(line)) for n, line in table if line.lstrip().startswith("|")]
    if len(rows) < 2 or rows[0][1] != CHANGE_HEADER or not all(_SEPARATOR.match(c) for c in rows[1][1]) or len(rows[1][1]) != 6:
        at = rows[0][0] if rows else body[0][0]
        out.append(f"line {at}: {CHANGE_HEADING} table header must be '| " + " | ".join(CHANGE_HEADER) + " |' followed by '|---|---|---|---|---|---|'")
        return
    rows = rows[2:]
    if not rows:
        out.append(f"line {body[0][0]}: {CHANGE_HEADING} has no rows; omit the whole section")
        return
    if override is not None:
        req_text = override.read_text(encoding="utf-8") if override.is_file() else None
        source = override.as_posix()
    else:
        req_text, source = base_requirements(spec)
    known = None if req_text is None else {m.group(1) for line in req_text.split("\n") if (m := _REQ_ITEM.match(line))}
    seen: dict[str, int] = {}
    for i, (n, cells) in enumerate(rows, 1):
        if len(cells) != 6:
            out.append(f"line {n}: {CHANGE_HEADING} row must have 6 cells ({len(cells)} found); escape '|' inside a cell as '\\|'")
            continue
        num, action, ref, text, reason, confirm = cells
        if num != str(i):
            out.append(f"line {n}: # must be {i} (rows are numbered 1, 2, 3, ... in order), found '{num}'")
        if action not in ("MODIFY", "DELETE"):
            out.append(f"line {n}: 動作 must be MODIFY or DELETE, found '{action}'")
        rm = _CHANGE_ID.match(ref)
        if not rm:
            out.append(f"line {n}: 既有編號 must be a backticked plan-qualified ID like `002/FR-002`, found '{ref}'")
        else:
            key = f"{rm.group(1)}/{rm.group(2)}"
            if own is not None and rm.group(1) == own:
                out.append(f"line {n}: {key} belongs to this plan; edit the requirement in this spec instead of listing it here")
            if key in seen:
                out.append(f"line {n}: {key} is already listed in row at line {seen[key]}")
            else:
                seen[key] = n
            if known is None:
                out.append(f"line {n}: {key} cannot be verified: requirements.md was not found ({source}); sync requirements before referencing them")
            elif key not in known:
                out.append(f"line {n}: {key} does not exist in requirements.md ({source}); reference a requirement that exists at the plan's Base")
        if action == "MODIFY" and text in EMPTY:
            out.append(f"line {n}: MODIFY row must give the complete new requirement text in 新內容")
        if action == "DELETE" and text != "—":
            out.append(f"line {n}: DELETE row must have '—' as 新內容")
        if not reason:
            out.append(f"line {n}: 理由 must not be empty")
        if not _CONFIRM.match(confirm):
            out.append(f"line {n}: 確認 must be '使用者於 YYYY-MM-DD 確認' or '低風險', found '{confirm}'")
        elif action == "DELETE" and confirm == "低風險":
            out.append(f"line {n}: DELETE is always high impact; 確認 must be '使用者於 YYYY-MM-DD 確認'")


def main() -> int:
    parser = argparse.ArgumentParser(description="List structural violations of a spec.md written from the specify skill's spec template.")
    parser.add_argument("--spec", required=True, help="Path to the spec.md to check")
    parser.add_argument("--requirements", help="requirements.md to check 既有需求異動 against instead of the plan's Base version (for testing)")
    args = parser.parse_args()
    spec = Path(args.spec)
    if not spec.is_file():
        sys.stderr.write(f"error: '{spec}' is not a file; pass --spec <feature dir>/spec.md\n")
        return 2
    lines = spec.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for n, line in enumerate(lines, 1):
        if "{{" in line or "}}" in line:
            out.append(f"line {n}: unfilled placeholder remains")
    check_headings(lines, out)
    groups = sections(lines)
    stories = check_stories(groups, out)
    check_global_and_system(groups, stories, out)
    check_edge_cases(groups, out)
    check_ids(lines, out)
    check_changes(groups, spec, Path(args.requirements) if args.requirements else None, out)
    if out:
        sys.stdout.write("\n".join(out) + "\n")
        return 1
    sys.stdout.write("OK: no violations\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
