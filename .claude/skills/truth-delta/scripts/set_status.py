# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Move a plan's truth-delta.md Status one step forward (規劃中 → 實作中 → 已交付), refusing delivery while records are incomplete.

Usage:
    uv run scripts/set_status.py --plan <specs/plans/NNN-name> --status <實作中|已交付>
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


ORDER = ["規劃中", "實作中", "已交付"]
RECONCILE_HEADING = "## 待和解"
STATUS_LINE = re.compile(r"^\*\*Status\*\*: (.+?)[ \t]*$", re.M)


def split_cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def table_rows(text: str) -> list[tuple[str, int, list[str]]]:
    """(section heading, line number, cells) of every data row under a `## ` heading."""
    rows, heading = [], None
    for i, line in enumerate(text.split("\n"), start=1):
        if line.startswith("## "):
            heading = line.strip()
            continue
        if heading and line.startswith("|") and not re.match(r"^\|\s*(-|動作\s*\||#\s*\|)", line):
            rows.append((heading, i, split_cells(line)))
    return rows


def delivery_blockers(text: str) -> list[str]:
    blockers = []
    for heading, line_no, cells in table_rows(text):
        if heading == RECONCILE_HEADING:
            if len(cells) == 6 and cells[4] not in ("已處理", "延後"):
                blockers.append(f"第 {line_no} 行 待和解 #{cells[0]} 狀態為「{cells[4]}」，需標為已處理或延後")
        elif len(cells) == 4:
            for name, value in (("摘要", cells[2]), ("原因", cells[3])):
                if not value or "{{" in value:
                    blockers.append(f"第 {line_no} 行 {heading[3:]} `{cells[1].replace('`', '')}` 的{name}未填")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description="Move a plan's truth-delta.md Status one step forward (規劃中 → 實作中 → 已交付), refusing delivery while records are incomplete.")
    parser.add_argument("--plan", required=True, help="Plan package directory, e.g. specs/plans/003-pvp-spectate")
    parser.add_argument("--status", required=True, choices=ORDER[1:], help="Target Status")
    args = parser.parse_args()

    delta = Path(args.plan) / "truth-delta.md"
    if not delta.is_file():
        sys.stderr.write(f"error: '{delta}' does not exist; create it with the truth-delta skill's 建立 action (scripts/init_delta.py)\n")
        return 2
    text = delta.read_text(encoding="utf-8")
    m = STATUS_LINE.search(text)
    if not m or m.group(1) not in ORDER:
        sys.stderr.write(f"error: {delta} has no valid **Status** line; expected one of {'、'.join(ORDER)}\n")
        return 2
    current = m.group(1)
    if ORDER.index(args.status) != ORDER.index(current) + 1:
        sys.stderr.write(f"error: Status is {current}; it can only move to the next step ({' → '.join(ORDER)}), not to {args.status}\n")
        return 1
    if args.status == "已交付":
        blockers = delivery_blockers(text)
        if blockers:
            for b in blockers:
                sys.stdout.write(b + "\n")
            sys.stderr.write(f"error: {len(blockers)} item(s) block delivery; record them with the truth-delta skill's 記錄 action first\n")
            return 1
    delta.write_text(STATUS_LINE.sub(f"**Status**: {args.status}", text, count=1), encoding="utf-8")
    sys.stdout.write(f"{current} → {args.status}: {delta}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
