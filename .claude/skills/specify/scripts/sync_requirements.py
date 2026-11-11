# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Sync a plan's FR / NFR / SC and its 既有需求異動 rows from spec.md into specs/truth/requirements.md.

The plan's own section (## NNN-name) is regenerated from the spec; MODIFY rows of `## 既有需求異動`
rewrite an older plan's entry in place and mark it （最後異動：NNN 既有需求異動 #n）, DELETE rows remove it.
Plans must be synced in ascending order: syncing is refused when requirements.md has a newer plan section or
a newer plan directory's spec.md has a 既有需求異動 table. Rerunning gives byte-identical output.

Usage:
    uv run scripts/sync_requirements.py --spec specs/plans/NNN-name/spec.md [--requirements specs/truth/requirements.md]
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


# Embedded format of specs/truth/requirements.md.
TITLE = "# Requirements"
INTRO = "> 現行有效的 FR、NFR、SC，依 plan 與 spec 區塊排列；由 /specify 的 sync_requirements.py 維護，請勿手動編輯。"
SUB_GLOBAL = "### 全域需求"
SUB_SYSTEM = "### 系統約束"
SUB_SC = "### Success Criteria"

_ID = r"(?:N?FR|SC)-\d{3}[a-z]?"
_SPEC_ITEM = re.compile(rf"^- \*\*({_ID})\*\*(?:（([^）]*)）)?: (.*)$")
_STORY = re.compile(r"^### User Story (\d+) - (.+?)\s*\(Priority: P\d+\)\s*$")
_CATEGORY = re.compile(r"^\*\*(.+)\*\*\s*$")
_BARE_REF = re.compile(rf"(?<![/A-Za-z0-9])({_ID})(?![A-Za-z0-9])")
_PLAN_HEAD = re.compile(r"^## (\d{3})-\S+$")
_ENTRY = re.compile(rf"^- \*\*(\d{{3}}/{_ID})\*\*((?:（[^）]*）)?: )(.*)$")
_MARK = re.compile(r"（最後異動：(\d{3}) 既有需求異動 #\d+）$")
_CHANGE_ID = re.compile(rf"^`(\d{{3}}/{_ID})`$")
CHANGE_HEADING = "## 既有需求異動"
CHANGE_HEADER = ["#", "動作", "既有編號", "新內容", "理由", "確認"]


class SyncError(Exception):
    pass


def qualify(text: str, nnn: str) -> str:
    # Bare IDs are this plan's own; already-qualified ones (002/FR-001) are left alone.
    return _BARE_REF.sub(lambda m: f"{nnn}/{m.group(1)}", text)


def spec_items(lines: list[str], nnn: str) -> list[tuple[str, list[str]]]:
    """Ordered (subsection heading, entry lines) built from the spec's requirement items."""
    subs: dict[str, list[str]] = {}
    sub, category = None, None
    for line in lines:
        if line.startswith("#"):
            category = None
            story = _STORY.match(line)
            if story:
                sub = f"### 使用者故事 {story.group(1)} - {story.group(2)}"
            elif line.startswith("### Edge Cases") or line.startswith("## Key Entities") or line.startswith("## Assumptions"):
                sub = None
            elif line.startswith("## Global Requirements"):
                sub = SUB_GLOBAL
            elif line.startswith("## System Constraints"):
                sub = SUB_SYSTEM
            elif line == "### Measurable Outcomes":
                sub = SUB_SC
            elif line.startswith("## ") and not line.startswith("## User Scenarios"):
                sub = None
            continue
        if sub is None:
            continue
        cat = _CATEGORY.match(line)
        if cat and sub in (SUB_GLOBAL, SUB_SYSTEM):
            category = cat.group(1).strip()
            continue
        m = _SPEC_ITEM.match(line)
        if not m:
            continue
        rid, paren, text = m.groups()
        if sub in (SUB_GLOBAL, SUB_SYSTEM) and category:
            paren = f"{category}；{paren}" if paren else category
        label = f"（{paren}）" if paren else ""
        subs.setdefault(sub, []).append(f"- **{nnn}/{rid}**{label}: {qualify(text, nnn)}")
    return list(subs.items())


def change_rows(lines: list[str]) -> list[tuple[int, str, str, str]]:
    """(row #, action, plan-qualified ID, new text) from the spec's 既有需求異動 table."""
    try:
        start = lines.index(CHANGE_HEADING)
    except ValueError:
        return []
    rows = []
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if cells == CHANGE_HEADER or all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        if len(cells) != 6 or not cells[0].isdigit() or cells[1] not in ("MODIFY", "DELETE") or not _CHANGE_ID.match(cells[2]):
            raise SyncError(f"malformed {CHANGE_HEADING} row '{line.strip()}'; run spec_lint.py and fix the spec first")
        rows.append((int(cells[0]), cells[1], _CHANGE_ID.match(cells[2]).group(1), cells[3]))
    return rows


Plan = list[tuple[str, list[str]]]  # ordered (subsection heading, entry lines)


def parse_requirements(text: str) -> dict[str, tuple[str, Plan]]:
    """NNN -> (plan section heading, subsections) from an existing requirements.md."""
    plans: dict[str, tuple[str, Plan]] = {}
    current: Plan | None = None
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip() or line in (TITLE, INTRO):
            continue
        m = _PLAN_HEAD.match(line)
        if m:
            if m.group(1) in plans:
                raise SyncError(f"line {n}: plan {m.group(1)} appears twice; restore requirements.md from git and resync")
            current = []
            plans[m.group(1)] = (line, current)
        elif current is not None and line.startswith("### "):
            current.append((line, []))
        elif current and _ENTRY.match(line):
            current[-1][1].append(line)
        else:
            raise SyncError(f"line {n}: unrecognised line '{line}'; requirements.md must not be edited by hand, restore it from git and resync")
    return plans


def render(plans: dict[str, tuple[str, Plan]]) -> str:
    blocks = [TITLE, INTRO]
    for nnn in sorted(plans):
        heading, subs = plans[nnn]
        subs = [(h, entries) for h, entries in subs if entries]
        if not subs:
            continue
        blocks.append(heading)
        for h, entries in subs:
            blocks += [h, "\n".join(entries)]
    return "\n\n".join(blocks) + "\n"


def entry_map(plans: dict[str, tuple[str, Plan]]) -> dict[str, str]:
    return {_ENTRY.match(e).group(1): e for _, subs in plans.values() for _, entries in subs for e in entries}


def newer_change_plans(plans_dir: Path, nnn: str) -> list[str]:
    """Higher-numbered plan dirs whose spec.md carries a 既有需求異動 table (they may MODIFY / DELETE older entries)."""
    found = []
    for d in sorted(plans_dir.iterdir()) if plans_dir.is_dir() else []:
        spec = d / "spec.md"
        m = re.match(r"^(\d{3})-", d.name)
        if m and m.group(1) > nnn and spec.is_file():
            if CHANGE_HEADING in spec.read_text(encoding="utf-8").splitlines():
                found.append(d.name)
    return found


def sync(spec_text: str, plan_name: str, old_text: str | None, plans_dir: Path) -> tuple[str, dict[str, str], dict[str, str]]:
    nnn = plan_name[:3]
    lines = spec_text.splitlines()
    plans = parse_requirements(old_text) if old_text is not None else {}
    later = newer_change_plans(plans_dir, nnn)
    if later:
        raise SyncError(
            f"newer plan(s) {', '.join(later)} under {plans_dir.as_posix()} carry a {CHANGE_HEADING} table; "
            f"resyncing {nnn} would undo their MODIFY / DELETE rows, so older plans cannot be synced after them"
        )
    newer = sorted(p for p in plans if p > nnn)
    if newer:
        raise SyncError(
            f"requirements.md already has plan section(s) {', '.join(newer)} newer than {nnn}; "
            "older plans must be synced before newer ones (restore requirements.md from git or sync the plans in order)"
        )
    before = entry_map(plans)

    # Regenerate this plan's section; keep entries another plan has modified (they carry its 最後異動 mark).
    fresh = spec_items(lines, nnn)
    foreign: dict[str, tuple[str, str]] = {}
    for h, entries in plans.get(nnn, ("", []))[1]:
        for e in entries:
            mark = _MARK.search(e)
            if mark and mark.group(1) != nnn:
                foreign[_ENTRY.match(e).group(1)] = (h, e)
    placed = set()
    section: Plan = []
    for h, entries in fresh:
        kept = []
        for e in entries:
            rid = _ENTRY.match(e).group(1)
            if rid in foreign:
                e = foreign[rid][1]
                placed.add(rid)
            kept.append(e)
        section.append((h, kept))
    for rid, (h, e) in foreign.items():
        if rid not in placed:
            target = next((entries for sh, entries in section if sh == h), None)
            if target is None:
                section.append((h, [e]))
            else:
                target.append(e)
    plans[nnn] = (f"## {plan_name}", section)

    # Apply 既有需求異動 to older plans' entries.
    for row, action, rid, new_text in change_rows(lines):
        owner = rid[:3]
        if owner == nnn:
            raise SyncError(f"{CHANGE_HEADING} #{row} refers to this plan's own {rid}; edit it in the spec body instead")
        subs = plans.get(owner, ("", []))[1]
        hit = next(((entries, i) for _, entries in subs for i, e in enumerate(entries) if _ENTRY.match(e).group(1) == rid), None)
        if action == "MODIFY":
            if hit is None:
                raise SyncError(f"{CHANGE_HEADING} #{row} MODIFY {rid}: no such entry in requirements.md; sync plan {owner} first or fix the ID")
            entries, i = hit
            prefix = _ENTRY.match(entries[i]).group(2)
            entries[i] = f"- **{rid}**{prefix}{qualify(new_text, nnn)}（最後異動：{nnn} {CHANGE_HEADING[3:]} #{row}）"
        elif hit is not None:
            entries, i = hit
            del entries[i]

    rendered = render(plans)
    return rendered, before, entry_map(parse_requirements(rendered))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync a plan's FR / NFR / SC and its 既有需求異動 rows from spec.md into specs/truth/requirements.md.")
    parser.add_argument("--spec", required=True, help="Plan spec, e.g. specs/plans/003-pvp-spectate/spec.md")
    parser.add_argument("--requirements", default="specs/truth/requirements.md", help="Target requirements.md (default: specs/truth/requirements.md)")
    args = parser.parse_args()
    spec = Path(args.spec)
    if not spec.is_file():
        sys.stderr.write(f"error: '{spec}' is not a file; pass --spec specs/plans/NNN-name/spec.md\n")
        return 2
    plan_name = spec.resolve().parent.name
    if not re.match(r"^\d{3}-\S+$", plan_name):
        sys.stderr.write(f"error: spec's directory '{plan_name}' is not named NNN-name; pass a spec inside specs/plans/NNN-name/\n")
        return 2
    target = Path(args.requirements)
    old = target.read_text(encoding="utf-8") if target.is_file() else None
    try:
        rendered, before, after = sync(spec.read_text(encoding="utf-8"), plan_name, old, spec.resolve().parent.parent)
    except SyncError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    added = len(after.keys() - before.keys())
    removed = len(before.keys() - after.keys())
    updated = sum(1 for k in after.keys() & before.keys() if after[k] != before[k])
    if rendered != old:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8", newline="\n")
    sys.stdout.write(
        f"{'created' if old is None else 'synced'}: {target.as_posix()} (plan {plan_name})\n"
        f"added: {added}\nupdated: {updated}\nremoved: {removed}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
