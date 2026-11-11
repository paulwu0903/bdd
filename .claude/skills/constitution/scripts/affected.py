# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report which constitution rules apply to artifacts and which artifacts fail the script-verified ones.

For every skills/<skill>/<產出物>.md, collect its rules and those of its 引用 shared files, and match
its Applies To glob against the artifacts. Both modes use one glob semantics: `*` and `?` never
cross `/`, and a whole `**` segment matches zero or more directories.
- Without --file: check every existing artifact under the repository root and list failures grouped
  by owner skill (exit 0). Plans under specs/plans/<plan>/ are skipped when their truth-delta.md
  Status is 已交付, or when they have no truth-delta.md (legacy plans from before the truth split);
  the last lines name the skipped plans.
- With --file: list the constitution files that apply to each given path; the file need not exist yet.
- With --file and --check: run the script-verified rules on each given file, list failures and the
  rules left for self-check (rules verified by lint are left to the workspace lint); exit 1 on failure.

Usage:
    uv run scripts/affected.py --root .claude/constitution --repo <repository root>
    uv run scripts/affected.py --root .claude/constitution --repo <repository root> --file <產出物路徑> [--file ...] [--check]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

RULE_H1 = re.compile(r"^# (Rule \d+) - (.+)$")
BACKTICK = re.compile(r"`([^`]+)`")
STATUS_LINE = re.compile(r"^\*\*Status\*\*: (.+?)[ \t]*$", re.M)
PLAN_PATH = re.compile(r"^specs/plans/([^/]+)/")
DELIVERED = "已交付"
SKIP_DIRS = {".git", "node_modules"}


@lru_cache(maxsize=None)
def glob_regex(pattern: str) -> re.Pattern[str]:
    # Translate an Applies To glob into a regex over repo-relative POSIX paths.
    # `*` and `?` stay inside one path segment; a whole `**` segment spans zero or more directories.
    parts = pattern.split("/")
    out = []
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if part == "**":
            out.append(".*" if last else "(?:[^/]+/)*")
            continue
        seg = ""
        for ch in part:
            seg += "[^/]*" if ch == "*" else "[^/]" if ch == "?" else re.escape(ch)
        out.append(seg if last else seg + "/")
    return re.compile("".join(out) + r"\Z")


def matches(path: str, pattern: str) -> bool:
    return glob_regex(pattern).match(path) is not None


def rules(path: Path) -> list[tuple[str, str, str | None]]:
    # Return (rule label, rule title, verification) for every Rule in one file.
    # verification is the check path for `- 驗證：script`, "lint" for `- 驗證：lint`, otherwise None.
    found, in_code = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = RULE_H1.match(line)
        if match:
            found.append([match.group(1), match.group(2), None])
        elif found and found[-1][2] is None and line.startswith("- 驗證："):
            value = line[len("- 驗證："):].strip()
            found[-1][2] = value[len("script "):].strip() if value.startswith("script ") else value
    return [tuple(r) for r in found]


def header(path: Path) -> tuple[str | None, list[str]]:
    # Return the Applies To glob and the 引用 paths of a constitution file.
    applies, refs = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Applies To："):
            found = BACKTICK.findall(line)
            applies = found[0] if found else None
        elif line.startswith("- 引用："):
            refs.extend(BACKTICK.findall(line))
        elif line.startswith("# "):
            break
    return applies, refs


def modules(root: Path) -> list[tuple[str, str, list[str]]]:
    # Return (owner skill, Applies To glob, constitution files incl. 引用) for every artifact module.
    found = []
    for module in sorted((root / "skills").glob("*/*.md")):
        applies, refs = header(module)
        if applies is None:
            sys.stderr.write(f"skip {module.relative_to(root).as_posix()}: no Applies To glob\n")
            continue
        found.append((module.parent.name, applies, [module.relative_to(root).as_posix(), *refs]))
    return found


def repo_files(repo: Path) -> list[str]:
    # Return repo-relative POSIX paths of every file; honour .gitignore when the repo is a git work tree.
    git = shutil.which("git")
    if git and (repo / ".git").exists():
        result = subprocess.run(
            [git, "-C", str(repo), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0:
            return sorted({p for p in result.stdout.split("\0") if p and (repo / p).is_file()})
    found = []
    for current, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        base = Path(current).relative_to(repo)
        found += [(base / name).as_posix() for name in names]
    return sorted(found)


def frozen_reason(repo: Path, plan: str) -> str | None:
    # Return why a plan is frozen (delivered or legacy), or None when it is still open.
    delta = repo / "specs" / "plans" / plan / "truth-delta.md"
    if not delta.is_file():
        return "沒有 truth-delta.md（舊制 plan）"
    match = STATUS_LINE.search(delta.read_text(encoding="utf-8"))
    if match and match.group(1) == DELIVERED:
        return f"Status 為{DELIVERED}"
    return None


def run_check(uv: str, root: Path, check: str, artifact: Path) -> tuple[int, list[str]]:
    result = subprocess.run(
        [uv, "run", "-q", str(root / check), "--file", str(artifact)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode not in (0, 1, 2):
        sys.stderr.write(f"{check} failed on {artifact}: {result.stderr.strip()}\n")
    return result.returncode, result.stdout.splitlines()


def check_artifact(uv: str, root: Path, files: list[str], artifact: Path, label: str) -> tuple[list[str], list[str]]:
    # Return (failures, self-check rules) of one artifact against the given constitution files.
    failures, self_check = [], []
    for rule_file in files:
        for rule, title, verify in rules(root / rule_file):
            if verify is None:
                self_check.append(f"self-check | {label} | {rule_file} {rule} - {title}")
            elif verify != "lint":
                code, lines = run_check(uv, root, verify, artifact)
                if code == 1:
                    failures += [f"{label} | {rule_file} {rule} | {line}" for line in lines]
                elif code == 2:
                    self_check.append(f"self-check | {label} | {rule_file} {rule} - {title}（script 不支援此格式）")
    return failures, self_check


def check_all(uv: str, root: Path, repo: Path, mods: list[tuple[str, str, list[str]]]) -> int:
    # Check every existing artifact outside frozen plans and print failures grouped by owner skill.
    frozen: dict[str, str | None] = {}
    by_owner: dict[str, list[str]] = {}
    for path in repo_files(repo):
        plan = PLAN_PATH.match(path)
        if plan:
            name = plan.group(1)
            if name not in frozen:
                frozen[name] = frozen_reason(repo, name)
            if frozen[name]:
                continue
        for owner, applies, files in mods:
            if matches(path, applies):
                failures, _ = check_artifact(uv, root, files, repo / path, path)
                by_owner.setdefault(owner, []).extend(f"{owner} | {line}" for line in failures)
    findings = [line for owner in sorted(by_owner) for line in by_owner[owner]]
    for line in findings:
        print(line)
    if not findings:
        print("No existing artifact fails the script-verified rules.")
    skipped = sorted((name, reason) for name, reason in frozen.items() if reason)
    print(f"skipped frozen plans: {len(skipped)}")
    for name, reason in skipped:
        print(f"skipped | specs/plans/{name}/ | {reason}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Report constitution rules that apply to artifacts and their script verdicts.")
    parser.add_argument("--root", required=True, type=Path, help="constitution root, e.g. .claude/constitution")
    parser.add_argument("--repo", required=True, type=Path, help="repository root that the Applies To globs are relative to")
    parser.add_argument("--file", action="append", type=Path, default=[], help="artifact path; repeatable")
    parser.add_argument("--check", action="store_true", help="with --file: run the checks instead of only listing files")
    args = parser.parse_args()

    root, repo = args.root.resolve(), args.repo.resolve()
    if not (root / "skills").is_dir():
        if args.file and not args.check:
            for path in args.file:
                print(f"{path.as_posix()}: no constitution applies")
            return 0
        print("No constitution found; nothing to check.")
        return 0
    if args.check and not args.file:
        sys.stderr.write("--check needs at least one --file; omit both to check every existing artifact.\n")
        return 2
    uv = shutil.which("uv")
    if uv is None and (args.check or not args.file):
        sys.stderr.write("uv not found on PATH; install it from https://docs.astral.sh/uv/ and rerun.\n")
        return 2

    mods = modules(root)
    if not args.file:
        return check_all(uv, root, repo, mods)

    any_failure = False
    for path in args.file:
        absolute = path if path.is_absolute() else Path.cwd() / path
        try:
            label = absolute.resolve().relative_to(repo).as_posix()
        except ValueError:
            sys.stderr.write(f"{path} is outside --repo {repo}; pass a path inside the repository.\n")
            return 2
        files = list(dict.fromkeys(f for _, applies, fs in mods if matches(label, applies) for f in fs))
        if not args.check:
            print(f"{label}: " + (", ".join(files) if files else "no constitution applies"))
            continue
        if not files:
            print(f"{label}: no constitution applies")
            continue
        if not absolute.is_file():
            sys.stderr.write(f"{label} does not exist; write the artifact before running --check.\n")
            return 2
        failures, self_check = check_artifact(uv, root, files, absolute, label)
        any_failure |= bool(failures)
        for line in failures + self_check:
            print(line)
        if not failures:
            print(f"{label}: passes the script-verified rules")
    return 1 if any_failure else 0


if __name__ == "__main__":
    sys.exit(main())
