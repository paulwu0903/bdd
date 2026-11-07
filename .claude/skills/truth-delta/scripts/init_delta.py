# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Create a plan package's truth-delta.md with its Base commit and the deferred items of the last delivered plan.

Usage:
    uv run scripts/init_delta.py --plan <specs/plans/NNN-name> --branch <branch name>
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


FILE_NAME = "truth-delta.md"
DELTA_SECTIONS = [
    "## /specify — truth/requirements.md",
    "## /technical-research — truth/techstack.md",
    "## /api-plan — truth/contracts/",
    "## /data-plan — truth/data/",
    "## /dsl-refine — truth/features/",
]
DELTA_HEADER = "| 動作 | 部位 | 摘要 | 原因 |\n|---|---|---|---|"
RECONCILE_HEADING = "## 待和解"
RECONCILE_HEADER = "| # | 部位 | 衝突內容 | 建議 owner | 狀態 | 處理紀錄 |\n|---|---|---|---|---|---|"


def git(cwd: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip() if result.returncode == 0 else None


def header_value(text: str, name: str) -> str | None:
    m = re.search(rf"^\*\*{name}\*\*: `?([^`\n]+?)`?[ \t]*$", text, re.M)
    return m.group(1).strip() if m else None


def split_cells(line: str) -> list[str]:
    cells = re.split(r"(?<!\\)\|", line.strip())
    return [c.strip() for c in cells[1:-1]]


def reconcile_rows(text: str) -> list[list[str]]:
    lines = text.split("\n")
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == RECONCILE_HEADING)
    except StopIteration:
        return []
    rows = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if not line.startswith("|") or re.match(r"^\|\s*(#|-)", line):
            continue
        cells = split_cells(line)
        if len(cells) == 6:
            rows.append(cells)
    return rows


def last_delivered(plans_dir: Path, current: Path) -> Path | None:
    candidates = []
    for d in plans_dir.iterdir():
        f = d / FILE_NAME
        m = re.match(r"(\d+)-", d.name)
        if d == current or not m or not f.is_file():
            continue
        if header_value(f.read_text(encoding="utf-8"), "Status") == "已交付":
            candidates.append((int(m.group(1)), d))
    return max(candidates)[1] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a plan package's truth-delta.md with its Base commit and the deferred items of the last delivered plan.")
    parser.add_argument("--plan", required=True, help="Plan package directory, e.g. specs/plans/003-pvp-spectate")
    parser.add_argument("--branch", required=True, help="Git branch of this plan, e.g. 003-pvp-spectate")
    args = parser.parse_args()

    plan = Path(args.plan).resolve()
    if not plan.is_dir():
        sys.stderr.write(f"error: '{args.plan}' is not a directory; create the plan package first (specify skill create_feature.py)\n")
        return 2
    target = plan / FILE_NAME
    if target.is_file():
        text = target.read_text(encoding="utf-8")
        sys.stdout.write(f"exists: {target}\nBase: {header_value(text, 'Base')}\nStatus: {header_value(text, 'Status')}\n")
        return 0
    if git(plan, "rev-parse", "--show-toplevel") is None:
        sys.stderr.write("error: not inside a git repository; run `git init` and make a baseline commit first (specify skill asks the user)\n")
        return 2
    base = git(plan, "rev-parse", "HEAD")
    if base is None:
        sys.stderr.write("error: the repository has no commit yet; make a baseline commit before creating the plan branch\n")
        return 2

    carried = []
    previous = last_delivered(plan.parent, plan)
    if previous is not None:
        for cells in reconcile_rows((previous / FILE_NAME).read_text(encoding="utf-8")):
            if cells[4] == "延後":
                carried.append(cells)

    parts = [
        f"# Truth Delta: {plan.name}",
        "",
        f"**Plan**: `specs/plans/{plan.name}`",
        f"**Branch**: `{args.branch}`",
        f"**Base**: `{base}`",
        "**Status**: 規劃中",
        "",
    ]
    for heading in DELTA_SECTIONS:
        parts += [heading, "", DELTA_HEADER, ""]
    parts += [RECONCILE_HEADING, "", RECONCILE_HEADER]
    for i, cells in enumerate(carried, start=1):
        note = f"接續自 {previous.name} #{cells[0]}：{cells[5]}"
        parts.append(f"| {i} | {cells[1]} | {cells[2]} | {cells[3]} | 待處理 | {note} |")
    target.write_text("\n".join(parts) + "\n", encoding="utf-8")
    sys.stdout.write(f"created: {target}\nBase: {base}\nStatus: 規劃中\ncarried reconcile items: {len(carried)}"
                     + (f" (from {previous.name})" if previous else "") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
