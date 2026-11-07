# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List structural and research-consistency violations of a techstack.md written from the technical-research skill's techstack template.

Usage:
    uv run scripts/techstack_lint.py --techstack <techstack.md> --research <research.md>
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


_TITLE = re.compile(r"# Tech Stack: \S.*")
_SOURCE = "**Source**: [research.md](./research.md)"
# Fixed sections of templates/techstack.md in order, with their table headers.
SECTIONS = [
    ("## 執行環境", ["項目", "版本 / 範圍"]),
    ("## Runtime Dependencies", ["類別", "套件", "版本", "用途"]),
    ("## Dev Dependencies", ["類別", "套件", "版本", "用途"]),
]
_ENTRY = re.compile(r"^(?P<name>[^（(]+?)\s*[（(](?P<entry>[^）)]+)[）)]$")
_FIELD = re.compile(r"^- \*\*([^*]+)\*\*[:：]")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def check_structure(lines: list[str], out: list[str]) -> dict[str, list[tuple[int, list[str]]]]:
    # Validate headings, Source line and table headers; return data rows per section.
    if not lines or not _TITLE.fullmatch(lines[0]):
        out.append("line 1: first line must be '# Tech Stack: <feature name>'")
    if _SOURCE not in lines:
        out.append(f"missing source line '{_SOURCE}'")
    heads = [(n, line) for n, line in enumerate(lines, 1) if line.startswith("#")][1:]
    expected = [h for h, _ in SECTIONS]
    if [h for _, h in heads] != expected:
        found = ", ".join(f"'{h}' (line {n})" for n, h in heads) or "none"
        out.append(f"headings must be exactly {expected} in order; found {found}")
    rows: dict[str, list[tuple[int, list[str]]]] = {}
    for i, (n, head) in enumerate(heads):
        if head not in dict(SECTIONS):
            continue
        end = heads[i + 1][0] - 1 if i + 1 < len(heads) else len(lines)
        table = [(k, lines[k - 1]) for k in range(n + 1, end + 1) if lines[k - 1].startswith("|")]
        header = dict(SECTIONS)[head]
        if not table or cells(table[0][1]) != header:
            out.append(f"line {n}: {head} table header must be '| {' | '.join(header)} |'")
            continue
        data = [(k, cells(line)) for k, line in table[2:]]
        if not data:
            out.append(f"line {table[0][0]}: {head} table has no row")
        for k, row in data:
            if len(row) != len(header) or any(not c for c in row):
                out.append(f"line {k}: {head} row must have {len(header)} non-empty cells")
        rows[head] = [(k, row) for k, row in data if len(row) == len(header)]
    return rows


def research_parts(text: str) -> tuple[str, set[str]]:
    # Return all Decision field text and the package names in the 依賴授權 table.
    decisions, in_decision, in_license, licensed = [], False, False, set()
    for line in text.splitlines():
        if line.startswith("## "):
            in_decision, in_license = False, line == "## 依賴授權"
            continue
        m = _FIELD.match(line)
        if m:
            in_decision = m.group(1) == "Decision"
        if in_decision:
            decisions.append(line)
        if in_license and line.startswith("|"):
            first = cells(line)[0]
            if first and first != "套件" and not set(first) <= set("-: "):
                licensed.update(p.strip() for p in re.split(r"\s+/\s+|、", first) if p.strip())
    return "\n".join(decisions), licensed


def check_consistency(rows: dict[str, list[tuple[int, list[str]]]], research: str, out: list[str]) -> None:
    decisions, licensed = research_parts(research)
    lower_decisions, lower_research = decisions.lower(), research.lower()
    seen: dict[str, int] = {}
    runtime: set[str] = set()
    for head in ("## Runtime Dependencies", "## Dev Dependencies"):
        for k, (_, package, version, _) in rows.get(head, []):
            m = _ENTRY.match(package)
            name = m.group("name") if m else package
            names = [name] + ([m.group("entry").strip("`")] if m else [])
            if name in seen:
                out.append(f"line {k}: {name} is already listed at line {seen[name]}; list each package once")
            seen[name] = k
            if head == "## Runtime Dependencies":
                runtime.add(name)
            for n in names:
                if n.lower() not in lower_research:
                    out.append(f"line {k}: '{n}' does not appear in research.md")
            if version not in decisions:
                out.append(f"line {k}: version '{version}' of {name} does not appear in any research.md Decision")
            elif name.lower() not in lower_decisions and name not in licensed:
                out.append(f"line {k}: {name} is not chosen in any research.md Decision")
    if licensed and runtime != licensed:
        for name in sorted(licensed - runtime):
            out.append(f"Runtime Dependencies is missing '{name}' listed in research.md 依賴授權")
        for name in sorted(runtime - licensed):
            out.append(f"Runtime Dependencies has '{name}' that research.md 依賴授權 does not list")


def main() -> int:
    parser = argparse.ArgumentParser(description="List structural and research-consistency violations of a techstack.md written from the technical-research skill's techstack template.")
    parser.add_argument("--techstack", required=True, help="Path to the techstack.md to check")
    parser.add_argument("--research", required=True, help="Path to the research.md it summarizes")
    args = parser.parse_args()
    techstack, research = Path(args.techstack), Path(args.research)
    for path, flag in ((techstack, "--techstack"), (research, "--research")):
        if not path.is_file():
            sys.stderr.write(f"error: '{path}' is not a file; pass {flag} <feature dir>/{path.name}\n")
            return 2
    lines = techstack.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for n, line in enumerate(lines, 1):
        if "{{" in line or "}}" in line:
            out.append(f"line {n}: unfilled placeholder remains")
    rows = check_structure(lines, out)
    check_consistency(rows, research.read_text(encoding="utf-8"), out)
    if out:
        sys.stdout.write("\n".join(out) + "\n")
        return 1
    sys.stdout.write("OK: no violations\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
