# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Create the next numbered plan package directory under specs/plans/ and switch to a new git branch of the same name.

The number NNN is one more than the highest NNN among directories in specs/plans/, local branches and
remote-tracking branches (as last fetched; no fetch is done) named NNN-*, so a number is never reused. Run from the repository root.

Prints:
    plan: specs/plans/NNN-<short-name>
    branch: NNN-<short-name>

Usage:
    uv run scripts/create_feature.py --short-name <kebab-case-name>
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
_SHORT_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_NUMBERED = re.compile(r"^(\d{3})-")


def git(*args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return subprocess.CompletedProcess(["git", *args], 127, "", "git is not installed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the next numbered plan package directory under specs/plans/ and switch to a new git branch of the same name.")
    parser.add_argument("--short-name", required=True, help="Plan name in lowercase kebab-case, e.g. photo-album-organizer")
    args = parser.parse_args()
    if not _SHORT_NAME.match(args.short_name):
        sys.stderr.write(
            f"error: '{args.short_name}' is not lowercase kebab-case; pass e.g. --short-name photo-album-organizer\n"
        )
        return 2

    inside = git("rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        sys.stderr.write("error: not inside a git work tree; run `git init` and make a baseline commit first, then rerun\n")
        return 2
    top = Path(git("rev-parse", "--show-toplevel").stdout.strip())
    if top.resolve() != Path.cwd().resolve():
        sys.stderr.write(f"error: run this script from the repository root '{top}', not '{Path.cwd()}'\n")
        return 2

    # Next number is the highest NNN over plan directories and local branches, plus one; start at 001.
    refs = git("for-each-ref", "--format=%(refname:short)", "refs/heads/")
    branches = refs.stdout.splitlines() if refs.returncode == 0 else []
    # Remote-tracking branches as last fetched (no fetch here); strip the "<remote>/" prefix.
    remote_refs = git("for-each-ref", "--format=%(refname:lstrip=3)", "refs/remotes/")
    remote = [r for r in (remote_refs.stdout.splitlines() if remote_refs.returncode == 0 else []) if r != "HEAD"]
    dirs = [d.name for d in PLANS_ROOT.iterdir() if d.is_dir()] if PLANS_ROOT.is_dir() else []
    numbers = [int(m.group(1)) for name in dirs + branches + remote if (m := _NUMBERED.match(name))]
    name = f"{max(numbers, default=0) + 1:03d}-{args.short_name}"
    plan_dir = PLANS_ROOT / name

    if plan_dir.exists():
        sys.stderr.write(f"error: '{plan_dir.as_posix()}' already exists; plan numbers are never reused, inspect it and remove it if it is stray\n")
        return 1
    if git("show-ref", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0:
        sys.stderr.write(f"error: branch '{name}' already exists; plan numbers are never reused, delete or rename that branch first\n")
        return 1
    if name in remote:
        sys.stderr.write(f"error: a remote branch named '{name}' already exists; plan numbers are never reused, pick another short name or clean up the remote branch\n")
        return 1

    created = [d for d in (PLANS_ROOT.parent, PLANS_ROOT, plan_dir) if not d.exists()]
    plan_dir.mkdir(parents=True)
    switched = git("switch", "-c", name)
    if switched.returncode != 0:
        # Undo the directories this run created so a failed run leaves no trace.
        for d in reversed(created):
            d.rmdir()
        detail = (switched.stderr or switched.stdout).strip()
        sys.stderr.write(f"error: `git switch -c {name}` failed ({detail}); resolve it (e.g. commit or stash conflicting changes) and rerun\n")
        return 1
    sys.stdout.write(f"plan: {plan_dir.as_posix()}\nbranch: {name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
