# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List structural violations of a research.md written from the technical-research skill's research template.

Usage:
    uv run scripts/research_lint.py --research <research.md>
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


_TITLE = re.compile(r"# Research: \S.*")
_R_HEAD = re.compile(r"## R(\d+)\. \S.*")
_LICENSE_HEAD = "## 依賴授權"
_SOURCES_HEAD = "## Sources"
_FIELD = re.compile(r"^- \*\*([^*]+)\*\*[:：]")
_LICENSE_TABLE_HEAD = re.compile(r"^\|\s*套件\s*\|\s*授權\s*\|\s*備註\s*\|$")
# Field order inside an R section: Decision, Rationale, supplementary labels, Alternatives considered.
_RANK = {"Decision": 0, "Rationale": 1, "Alternatives considered": 3}
_SUPPLEMENTARY = 2


def headings(lines: list[str]) -> list[tuple[int, str]]:
    # Collect headings outside fenced code blocks.
    found, fenced = [], False
    for n, line in enumerate(lines, 1):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            found.append((n, line))
    return found


def check_headings(heads: list[tuple[int, str]], out: list[str]) -> None:
    # Expected order: title, R1..Rn (n >= 1, consecutive), 依賴授權, Sources.
    if not heads or heads[0][0] != 1 or not _TITLE.fullmatch(heads[0][1]):
        out.append("line 1: first line must be '# Research: <feature name>'")
    stage, expected_r = "title", 1
    for n, line in heads[1:] if heads and _TITLE.fullmatch(heads[0][1]) else heads:
        m = _R_HEAD.fullmatch(line)
        if m and stage in ("title", "r"):
            if int(m.group(1)) != expected_r:
                out.append(f"line {n}: expected R{expected_r}, found R{m.group(1)}; R numbers must start at 1 and be consecutive")
            expected_r = int(m.group(1)) + 1
            stage = "r"
        elif line == _LICENSE_HEAD and stage == "r":
            stage = "license"
        elif line == _SOURCES_HEAD and stage == "license":
            stage = "sources"
        else:
            out.append(f"line {n}: heading '{line}' is not in the template or is out of order")
    if stage == "title":
        out.append("end of file: missing '## R1. <topic>' section")
    if stage in ("title", "r"):
        out.append(f"end of file: missing required heading '{_LICENSE_HEAD}'")
    if stage != "sources":
        out.append(f"end of file: missing required heading '{_SOURCES_HEAD}'")


def sections(lines: list[str], heads: list[tuple[int, str]]) -> list[tuple[int, str, list[tuple[int, str]]]]:
    # Split the body into (heading line, heading, lines) per level-2 heading.
    result = []
    for i, (n, head) in enumerate(heads):
        if not head.startswith("## "):
            continue
        end = heads[i + 1][0] - 1 if i + 1 < len(heads) else len(lines)
        result.append((n, head, [(k, lines[k - 1]) for k in range(n + 1, end + 1)]))
    return result


def check_r_section(n: int, head: str, body: list[tuple[int, str]], out: list[str]) -> None:
    r = head.split(".", 1)[0][3:]
    labels = []
    last_rank = -1
    for k, line in body:
        m = _FIELD.match(line)
        if not m:
            continue
        label = m.group(1)
        rank = _RANK.get(label, _SUPPLEMENTARY)
        if rank < last_rank or (rank == last_rank and rank != _SUPPLEMENTARY):
            out.append(f"line {k}: {r} field '{label}' is out of order; use Decision → Rationale → supplementary → Alternatives considered, each once")
        last_rank = max(last_rank, rank)
        labels.append(label)
    for required in ("Decision", "Rationale"):
        if required not in labels:
            out.append(f"line {n}: {r} is missing '- **{required}**:'")


def check_license(n: int, body: list[tuple[int, str]], out: list[str]) -> None:
    rows = [(k, line) for k, line in body if line.startswith("|")]
    if not rows or not _LICENSE_TABLE_HEAD.match(rows[0][1]):
        out.append(f"line {n}: {_LICENSE_HEAD} must start with the table header '| 套件 | 授權 | 備註 |'")
        return
    if len(rows) < 3:
        out.append(f"line {rows[0][0]}: {_LICENSE_HEAD} table has no dependency row")


def check_sources(n: int, body: list[tuple[int, str]], out: list[str]) -> None:
    if not any(line.startswith("- ") for _, line in body):
        out.append(f"line {n}: {_SOURCES_HEAD} has no source item")


def main() -> int:
    parser = argparse.ArgumentParser(description="List structural violations of a research.md written from the technical-research skill's research template.")
    parser.add_argument("--research", required=True, help="Path to the research.md to check")
    args = parser.parse_args()
    research = Path(args.research)
    if not research.is_file():
        sys.stderr.write(f"error: '{research}' is not a file; pass --research <feature dir>/research.md\n")
        return 2
    lines = research.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for n, line in enumerate(lines, 1):
        if "{{" in line or "}}" in line:
            out.append(f"line {n}: unfilled placeholder remains")
    heads = headings(lines)
    check_headings(heads, out)
    for n, head, body in sections(lines, heads):
        if _R_HEAD.fullmatch(head):
            check_r_section(n, head, body, out)
        elif head == _LICENSE_HEAD:
            check_license(n, body, out)
        elif head == _SOURCES_HEAD:
            check_sources(n, body, out)
    if out:
        sys.stdout.write("\n".join(out) + "\n")
        return 1
    sys.stdout.write("OK: no violations\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
