# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report the git state of the repository in the current directory and the plan packages that are not yet delivered.

Prints, in this order:
    git repo: yes|no
    branch: <current branch, or (none) when not a repo, detached or unborn without a name>
    uncommitted: <N>            (porcelain entries, untracked included; listing capped at 50 lines)
    undelivered plans: <M>      (specs/plans/*/truth-delta.md whose Status is not 已交付)

Run from the repository root. Always exits 0 unless the arguments are invalid; it is a report, not a gate.

Usage:
    uv run scripts/git_state.py
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


PLANS_ROOT = Path("specs/plans")
DELTA_FILE = "truth-delta.md"
DELIVERED = "已交付"
LIST_CAP = 50


def git(*args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        # git itself is not installed: treat as "not a repository".
        return None


def header_value(text: str, name: str) -> str | None:
    # Same header syntax as truth-delta's init_delta.py: **Name**: `value` (backticks optional).
    m = re.search(rf"^\*\*{name}\*\*: `?([^`\n]+?)`?[ \t]*$", text, re.M)
    return m.group(1).strip() if m else None


def porcelain_lines(raw: str) -> list[str]:
    # -z output: "XY path\0", renames/copies add the original path as the next NUL-separated field.
    fields = raw.split("\0")
    lines, i = [], 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        if status[0] in "RC" and i < len(fields):
            path = f"{fields[i]} -> {path}"
            i += 1
        lines.append(f"{status} {path}")
    return lines


def undelivered_plans() -> list[str]:
    if not PLANS_ROOT.is_dir():
        return []
    out = []
    for delta in sorted(PLANS_ROOT.glob(f"*/{DELTA_FILE}")):
        text = delta.read_text(encoding="utf-8")
        status = header_value(text, "Status") or "(unknown)"
        if status == DELIVERED:
            continue
        branch = header_value(text, "Branch") or "(unknown)"
        out.append(f"{delta.parent.as_posix()} (Status: {status}, Branch: {branch})")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Report the git state of the repository in the current directory and the plan packages that are not yet delivered.")
    parser.parse_args()

    inside = git("rev-parse", "--is-inside-work-tree")
    is_repo = inside is not None and inside.returncode == 0 and inside.stdout.strip() == "true"
    branch, changes = "(none)", []
    if is_repo:
        ref = git("symbolic-ref", "--short", "-q", "HEAD")
        if ref is not None and ref.returncode == 0 and ref.stdout.strip():
            branch = ref.stdout.strip()
        status = git("status", "--porcelain=v1", "-z")
        if status is not None and status.returncode == 0:
            changes = porcelain_lines(status.stdout)
        else:
            sys.stderr.write("warning: `git status` failed; uncommitted count may be wrong\n")

    out = [f"git repo: {'yes' if is_repo else 'no'}", f"branch: {branch}", f"uncommitted: {len(changes)}"]
    out += [f"  {line}" for line in changes[:LIST_CAP]]
    if len(changes) > LIST_CAP:
        out.append(f"  … and {len(changes) - LIST_CAP} more")
    plans = undelivered_plans()
    out.append(f"undelivered plans: {len(plans)}")
    out += [f"  {p}" for p in plans]
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
