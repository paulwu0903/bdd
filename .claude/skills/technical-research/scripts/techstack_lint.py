# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List structural violations of the truth techstack.md and inconsistencies between its rows changed by one plan and that plan's research.md.

Structure: the `# Tech Stack:` title, the fixed Truth note, the `**Source**:` line listing one
`[NNN research.md](../plans/NNN-name/research.md)` link per plan (ascending, existing files, this plan
included), and the three fixed sections with their table headers.

Consistency is judged only on rows this plan changed: the techstack.md of the plan's Base commit
(truth-delta.md `**Base**:`; falling back to HEAD, then to an empty file) is diffed with the given file.
  - ADD / MODIFY rows: the package (or environment item) name and the version appear in a Decision of
    this plan's research.md.
  - DELETE rows: the name appears somewhere in this plan's research.md.
  - Runtime rows that are added, moved from Dev, or changed in version are listed in research.md 依賴授權,
    and every package in 依賴授權 is a Runtime row.
Unchanged rows are not checked against research.md.

Usage:
    uv run scripts/techstack_lint.py --techstack specs/truth/techstack.md --plan specs/plans/NNN-name \
        [--base-techstack <file>]
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


_TITLE = re.compile(r"# Tech Stack: \S.*")
_TRUTH_NOTE_START = "本檔屬於 Truth："
_SOURCE_PREFIX = "**Source**: "
_SOURCE_LINK = re.compile(r"\[(\d{3}) research\.md\]\(\.\./plans/(\d{3})-[a-z0-9][a-z0-9-]*/research\.md\)")
_PLAN_DIR = re.compile(r"^(\d{3})-[a-z0-9][a-z0-9-]*$")
# Fixed sections of templates/techstack.md in order, with their table headers.
SECTIONS = [
    ("## 執行環境", ["項目", "版本 / 範圍"]),
    ("## Runtime Dependencies", ["類別", "套件", "版本", "用途"]),
    ("## Dev Dependencies", ["類別", "套件", "版本", "用途"]),
]
_ENV, _RUNTIME, _DEV = (h for h, _ in SECTIONS)
_ENTRY = re.compile(r"^(?P<name>[^（(]+?)\s*[（(](?P<entry>[^）)]+)[）)]$")
_FIELD = re.compile(r"^- \*\*([^*]+)\*\*[:：]")
_BASE = re.compile(r"^\*\*Base\*\*: `?([0-9a-fA-F]{4,40})`?[ \t]*$", re.M)


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_rows(lines: list[str], out: list[str] | None) -> dict[str, list[tuple[int, list[str]]]]:
    # Data rows per fixed section; structural problems go to out when it is given.
    heads = [(n, line) for n, line in enumerate(lines, 1) if line.startswith("## ")]
    rows: dict[str, list[tuple[int, list[str]]]] = {}
    for i, (n, head) in enumerate(heads):
        if head not in dict(SECTIONS):
            continue
        end = heads[i + 1][0] - 1 if i + 1 < len(heads) else len(lines)
        table = [(k, lines[k - 1]) for k in range(n + 1, end + 1) if lines[k - 1].startswith("|")]
        header = dict(SECTIONS)[head]
        if not table or cells(table[0][1]) != header:
            if out is not None:
                out.append(f"line {n}: {head} table header must be '| {' | '.join(header)} |'")
            continue
        data = [(k, cells(line)) for k, line in table[2:]]
        if out is not None:
            if not data:
                out.append(f"line {table[0][0]}: {head} table has no row")
            for k, row in data:
                if len(row) != len(header) or any(not c for c in row):
                    out.append(f"line {k}: {head} row must have {len(header)} non-empty cells")
        rows[head] = [(k, row) for k, row in data if len(row) == len(header)]
    return rows


def check_structure(lines: list[str], techstack: Path, plan_no: str, out: list[str]) -> None:
    # Title, Truth note, Source links and the ordered fixed headings.
    if not lines or not _TITLE.fullmatch(lines[0]):
        out.append("line 1: first line must be '# Tech Stack: <product name>'")
    notes = [(n, line) for n, line in enumerate(lines, 1) if line.startswith(_TRUTH_NOTE_START)]
    if not notes:
        out.append(f"missing Truth note paragraph starting with '{_TRUTH_NOTE_START}' (copy it from templates/techstack.md)")
    for n, line in notes:
        if "truth-delta.md" not in line or "changes.md" in line:
            out.append(f"line {n}: Truth note must say changes are recorded in the plan's `truth-delta.md` "
                       "(not `changes.md`); copy it from templates/techstack.md")
    sources = [(n, line) for n, line in enumerate(lines, 1) if line.startswith(_SOURCE_PREFIX)]
    if len(sources) != 1:
        out.append(f"expected exactly one '{_SOURCE_PREFIX}' line, found {len(sources)}")
    else:
        n, line = sources[0]
        rest = line[len(_SOURCE_PREFIX):]
        links = list(_SOURCE_LINK.finditer(rest))
        leftover = _SOURCE_LINK.sub("", rest).replace("、", "").strip()
        if not links or leftover:
            out.append(f"line {n}: Source must be '[NNN research.md](../plans/NNN-<name>/research.md)' links joined by 、")
        numbers = []
        for m in links:
            if m.group(1) != m.group(2):
                out.append(f"line {n}: link text {m.group(1)} does not match its target plan {m.group(2)}")
            target = (techstack.parent / m.group(0).split("](", 1)[1][:-1]).resolve()
            if not target.is_file():
                out.append(f"line {n}: Source link target '{m.group(0)}' does not exist")
            numbers.append(m.group(2))
        if numbers != sorted(set(numbers)):
            out.append(f"line {n}: Source links must be unique and in ascending plan order")
        if plan_no not in numbers:
            out.append(f"line {n}: Source must include this plan's research link ({plan_no} research.md)")
    heads = [(n, line) for n, line in enumerate(lines, 1) if line.startswith("#")][1:]
    expected = [h for h, _ in SECTIONS]
    if [h for _, h in heads] != expected:
        found = ", ".join(f"'{h}' (line {n})" for n, h in heads) or "none"
        out.append(f"headings must be exactly {expected} in order; found {found}")


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


def keyed(rows: dict[str, list[tuple[int, list[str]]]]) -> dict[str, tuple[str, int, list[str]]]:
    # name -> (section, line, row); environment items and packages share one namespace by section prefix.
    result: dict[str, tuple[str, int, list[str]]] = {}
    for head, data in rows.items():
        for k, row in data:
            name = row[0] if head == _ENV else row[1]
            m = _ENTRY.match(name) if head != _ENV else None
            key = (m.group("name") if m else name) if head != _ENV else f"env:{name}"
            result.setdefault(key, (head, k, row))
    return result


def check_duplicates(rows: dict[str, list[tuple[int, list[str]]]], out: list[str]) -> None:
    seen: dict[str, int] = {}
    for head in (_RUNTIME, _DEV):
        for k, row in rows.get(head, []):
            m = _ENTRY.match(row[1])
            name = m.group("name") if m else row[1]
            if name in seen:
                out.append(f"line {k}: {name} is already listed at line {seen[name]}; list each package once")
            seen.setdefault(name, k)


def check_changes(current: dict, base: dict, research: str, out: list[str]) -> tuple[int, int, int]:
    # Judge only the rows that differ from Base against this plan's research.md.
    decisions, licensed = research_parts(research)
    lower_decisions, lower_research = decisions.lower(), research.lower()
    added = modified = 0
    for key, (head, k, row) in current.items():
        old = base.get(key)
        if old is not None and old[0] == head and old[2] == row:
            continue
        if old is None:
            added += 1
        else:
            modified += 1
        version = row[1] if head == _ENV else row[2]
        label = row[0] if head == _ENV else row[1]
        m = _ENTRY.match(label) if head != _ENV else None
        names = [m.group("name"), m.group("entry").strip("`")] if m else [label]
        for n in names:
            if n.lower() not in lower_research:
                out.append(f"line {k}: changed row '{n}' does not appear in this plan's research.md")
        if version not in decisions:
            out.append(f"line {k}: changed row version '{version}' of {names[0]} does not appear in any Decision of this plan's research.md")
        elif names[0].lower() not in lower_decisions and names[0] not in licensed:
            out.append(f"line {k}: changed row {names[0]} is not chosen in any Decision of this plan's research.md")
        if head == _RUNTIME:
            old_version = old[2][2] if old is not None and old[0] == _RUNTIME else None
            if old_version != row[2] and names[0] not in licensed:
                out.append(f"line {k}: Runtime row {names[0]} is added or changes version but is not listed in this plan's research.md 依賴授權")
    deleted = 0
    for key, (head, k, row) in base.items():
        if key in current:
            continue
        deleted += 1
        name = key[4:] if key.startswith("env:") else key
        if name.lower() not in lower_research:
            out.append(f"Base line {k}: {head} row '{name}' was deleted but this plan's research.md does not mention it")
    runtime_now = {key for key, (head, _, _) in current.items() if head == _RUNTIME}
    for name in sorted(licensed - runtime_now):
        out.append(f"research.md 依賴授權 lists '{name}' that is not a Runtime Dependencies row")
    return added, modified, deleted


def _git(cwd: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        return None
    return r.stdout if r.returncode == 0 else None


def base_techstack(techstack: Path, plan: Path) -> tuple[str, str]:
    """Text of techstack.md at the plan's Base commit, else at HEAD, else empty; plus where it came from."""
    top = _git(techstack.resolve().parent, "rev-parse", "--show-toplevel")
    if not top:
        return "", "empty (not a git repository)"
    root = Path(top.strip())
    rel = techstack.resolve().relative_to(root).as_posix()
    delta = plan / "truth-delta.md"
    if delta.is_file():
        m = _BASE.search(delta.read_text(encoding="utf-8"))
        if m:
            shown = _git(root, "show", f"{m.group(1)}:{rel}")
            if shown is not None:
                return shown, f"Base {m.group(1)[:12]}"
    shown = _git(root, "show", f"HEAD:{rel}")
    if shown is not None:
        return shown, "HEAD (no usable Base in truth-delta.md)"
    return "", "empty (techstack.md not in Base or HEAD)"


def main() -> int:
    parser = argparse.ArgumentParser(description="List structural violations of the truth techstack.md and inconsistencies between the rows one plan changed and that plan's research.md.")
    parser.add_argument("--techstack", required=True, help="Path to specs/truth/techstack.md")
    parser.add_argument("--plan", required=True, help="Path to the plan directory specs/plans/NNN-name holding research.md")
    parser.add_argument("--base-techstack", help="techstack.md to diff against instead of the plan's Base version (for testing)")
    args = parser.parse_args()
    techstack, plan = Path(args.techstack), Path(args.plan)
    research = plan / "research.md"
    if not techstack.is_file():
        sys.stderr.write(f"error: '{techstack}' is not a file; pass --techstack specs/truth/techstack.md\n")
        return 2
    m = _PLAN_DIR.match(plan.resolve().name)
    if not plan.is_dir() or not m:
        sys.stderr.write(f"error: '{plan}' is not a plan directory; pass --plan specs/plans/NNN-<name>\n")
        return 2
    if not research.is_file():
        sys.stderr.write(f"error: '{research}' does not exist; write the plan's research.md first\n")
        return 2
    lines = techstack.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for n, line in enumerate(lines, 1):
        if "{{" in line or "}}" in line:
            out.append(f"line {n}: unfilled placeholder remains")
    check_structure(lines, techstack, m.group(1), out)
    rows = table_rows(lines, out)
    check_duplicates(rows, out)
    if args.base_techstack:
        base_text, source = Path(args.base_techstack).read_text(encoding="utf-8"), args.base_techstack
    else:
        base_text, source = base_techstack(techstack, plan)
    base = keyed(table_rows(base_text.splitlines(), None))
    counts = check_changes(keyed(rows), base, research.read_text(encoding="utf-8"), out)
    summary = f"compared with {source}: {counts[0]} added, {counts[1]} modified, {counts[2]} deleted row(s)"
    if out:
        sys.stdout.write("\n".join(out) + "\n")
        sys.stderr.write(summary + "\n")
        return 1
    sys.stdout.write(f"OK: no violations ({summary})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
