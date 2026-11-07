# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List structural violations of a spec.md written from the specify skill's spec template.

Usage:
    uv run scripts/spec_lint.py --spec <spec.md>
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
    (r"## Assumptions", True, False),
]
_ID = r"(?:FR|NFR|SC)-\d{3}[a-z]?"
_DEF = re.compile(rf"^- \*\*({_ID})\*\*")
_REF = re.compile(rf"(?<![\w-])({_ID})(?![\w])")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="List structural violations of a spec.md written from the specify skill's spec template.")
    parser.add_argument("--spec", required=True, help="Path to the spec.md to check")
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
    if out:
        sys.stdout.write("\n".join(out) + "\n")
        return 1
    sys.stdout.write("OK: no violations\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
