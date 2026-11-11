# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check a features/acceptance directory of acceptance Gherkin files against the spec-by-example standard.

Usage:
    uv run scripts/check_acceptance.py --dir <specs/plans/<NNN>-<name>/features/acceptance> \
        [--min-files 1] [--max-files 8]

Checks (one line per violation on stdout, exit 1 when any, exit 2 on bad arguments):
  A1 the directory path ends with features/acceptance
  A2 the directory holds no dsl.md and no frontend / backend subdirectories
  A3 the number of .feature files is within --min-files .. --max-files (default 1-8; 5-8 recommended only for a first plan of a new product)
  A4 each file: `Feature: <name>` followed by a description line, at most one Background (optional;
     extracted only for steps shared by journeys, so a Background needs at least 2 Examples) before
     the first Rule, at least one Rule, 1-3 Examples, no bare Scenario, every Example under a Rule
  A5 quoting: step lines have balanced double quotes and no 「」; Data Table cells do not start or
     end with a quote mark (quoted digit strings such as codes and IDs are allowed in steps)
  A6 clarification tags: every open tag is `# [NEEDS CLARIFICATION: <問題>？暫以「<暫定答案>」撰寫]`
     and every resolved tag is `# [CLARIFIED: <問題>？→「<定案答案>」]` (kept after /clarify as the
     decision record; both kinds count toward the 0-10 total and follow the same placement rule)
     (本範例暫以 accepted), sits directly above a Background step, an Example line, or a Given /
     When / Then step inside an Example (And / But resolve to the previous keyword), and the whole set has at most 10 tags
  A7 within an Example, every step containing 系統拒絕 is followed, before the next When or the
     end of the Example, by at least one Then / And step containing 仍
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


STEP = re.compile(r"^(Given|When|Then|And|But)\s")
TAG_MARK = "NEEDS CLARIFICATION"
TAG = re.compile(r"^# \[NEEDS CLARIFICATION: .+？(本範例)?暫以「.+」撰寫\]$")
DONE_MARK = "CLARIFIED"
DONE = re.compile(r"^# \[CLARIFIED: .+？→「.+」\]$")
REJECT_MARK = "系統拒絕"
UNCHANGED_MARK = "仍"
SIDE_DIRS = {"frontend", "backend", "前端", "後端"}
MIN_TAGS, MAX_TAGS = 0, 10
MAX_EXAMPLES = 3


def check_file(path: Path, rel: str, errors: list[str]) -> tuple[int, int]:
    # Check one feature file; return (open, resolved) counts of well-formed clarification tags in it.
    lines = path.read_text(encoding="utf-8").splitlines()
    err = lambda n, code, msg: errors.append(f"{rel}:{n}: [{code}] {msg}")
    section = None  # None | "background" | "rule" | "example"
    seen_feature = False
    need_description = False
    backgrounds = rules = examples = tags = done = 0
    last_keyword = None
    pending_tag = None  # line number of a tag waiting for its target line
    open_reject = None  # line number of a rejection step still waiting for an unchanged (仍) checkpoint

    def close_reject() -> None:
        # A rejection left open when its checkpoint window ends is an A7 violation.
        nonlocal open_reject
        if open_reject is not None:
            err(open_reject, "A7", f"after a {REJECT_MARK}… step, add a Then / And step with {UNCHANGED_MARK} "
                "stating what the rejected action did not change (before the next When or Example end)")
            open_reject = None

    for n, raw in enumerate(lines, start=1):
        s = raw.strip()
        if pending_tag is not None and s:
            # The line right below a tag decides whether the tag is placed on a valid target.
            ok = False
            m = STEP.match(s)
            if section == "background" and m:
                ok = True
            elif s.startswith("Example:"):
                ok = True
            elif section == "example" and m:
                kw = m.group(1) if m.group(1) not in ("And", "But") else last_keyword
                ok = kw in ("Given", "When", "Then")
            if not ok:
                err(pending_tag, "A6", "clarification tag must sit directly above a Background step, "
                    "an Example line, or a Given / When / Then step inside an Example; move it onto the "
                    "line its answer changes")
            pending_tag = None
        if not s:
            continue
        if s.startswith("#"):
            if TAG_MARK in s or s.startswith("# [" + DONE_MARK):
                if TAG.match(s):
                    tags += 1
                elif DONE.match(s):
                    done += 1
                elif TAG_MARK in s:
                    err(n, "A6", "clarification tag must read "
                        "`# [NEEDS CLARIFICATION: <問題>？暫以「<暫定答案>」撰寫]`")
                else:
                    err(n, "A6", "resolved clarification tag must read `# [CLARIFIED: <問題>？→「<定案答案>」]`")
                nxt = lines[n] if n < len(lines) else ""
                if not nxt.strip():
                    err(n, "A6", "clarification tag must be directly above its target line, not above a blank line")
                else:
                    pending_tag = n
            continue
        if need_description:
            need_description = False
            if s.startswith(("Background:", "Rule:", "Example:", "Scenario", "@")) or STEP.match(s):
                err(n - 1, "A4", "Feature must be followed by a one-sentence business description line")
        if s.startswith("Feature:"):
            if seen_feature:
                err(n, "A4", "only one Feature per file")
            if not s[len("Feature:"):].strip():
                err(n, "A4", "Feature needs a name")
            seen_feature = True
            need_description = True
            continue
        if s.startswith("Background:"):
            close_reject()
            backgrounds += 1
            if rules:
                err(n, "A4", "Background must come before the first Rule")
            section = "background"
            continue
        if s.startswith("Rule:"):
            close_reject()
            rules += 1
            section = "rule"
            continue
        if s.startswith("Scenario:") or s.startswith("Scenario Outline:"):
            err(n, "A4", "write journeys as `Example:` under a Rule, not `Scenario:`")
            continue
        if s.startswith("Example:"):
            close_reject()
            examples += 1
            if not rules:
                err(n, "A4", "Example must sit under a Rule")
            if not s[len("Example:"):].strip():
                err(n, "A4", "Example needs a scenario title")
            section = "example"
            last_keyword = None
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            for c in cells:
                if c[:1] in ('"', "「") or c[-1:] in ('"', "」"):
                    err(n, "A5", f"Data Table cell `{c}` must not be quoted; write the bare value")
            continue
        m = STEP.match(s)
        if m:
            if m.group(1) not in ("And", "But"):
                last_keyword = m.group(1)
            if section == "example":
                if last_keyword == "When":
                    close_reject()
                elif open_reject is not None and last_keyword == "Then" and UNCHANGED_MARK in s:
                    open_reject = None
                if REJECT_MARK in s:
                    open_reject = n
            if s.count('"') % 2:
                err(n, "A5", "unbalanced double quotes in step; wrap each string parameter in a pair of \"\"")
            if "「" in s or "」" in s:
                err(n, "A5", "string parameters in steps use double quotes, not 「」")
    close_reject()
    if pending_tag is not None:
        err(pending_tag, "A6", "clarification tag at end of file has no target line")

    if not seen_feature:
        err(1, "A4", "file has no `Feature:` line")
    if backgrounds > 1:
        err(1, "A4", f"expected at most one Background, found {backgrounds}")
    if backgrounds == 1 and examples < 2:
        # A Background exists only to extract steps shared by journeys; one journey has nothing to share.
        err(1, "A4", "Background is only for steps shared by 2+ Examples; with a single Example, "
            "move its steps into that Example's Given and delete the Background")
    if rules < 1:
        err(1, "A4", "expected at least one Rule")
    if not 1 <= examples <= MAX_EXAMPLES:
        err(1, "A4", f"expected 1-{MAX_EXAMPLES} Examples (journeys), found {examples}")
    return tags, done


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a features/acceptance directory of acceptance Gherkin files.")
    parser.add_argument("--dir", required=True, help="Path to specs/plans/<NNN>-<name>/features/acceptance")
    parser.add_argument("--min-files", type=int, default=1, help="Minimum number of .feature files (default 1; 5-8 recommended only for a first plan of a new product)")
    parser.add_argument("--max-files", type=int, default=8, help="Maximum number of .feature files (default 8)")
    args = parser.parse_args()
    root = Path(args.dir)
    if not root.is_dir():
        sys.stderr.write(f"error: '{root}' is not a directory; pass --dir <specs/plans/<NNN>-<name>/features/acceptance>\n")
        return 2
    if args.min_files < 1 or args.min_files > args.max_files:
        sys.stderr.write("error: --min-files must be >= 1 and <= --max-files\n")
        return 2

    errors: list[str] = []
    resolved = root.resolve()
    if resolved.parts[-2:] != ("features", "acceptance"):
        errors.append(f"{root}: [A1] directory must be specs/plans/<NNN>-<name>/features/acceptance")
    for p in sorted(resolved.rglob("*")):
        if p.is_file() and p.name.lower() == "dsl.md":
            errors.append(f"{p.relative_to(resolved)}: [A2] acceptance step produces no dsl.md; remove it")
        if p.is_dir() and p.name.lower() in SIDE_DIRS:
            errors.append(f"{p.relative_to(resolved)}: [A2] acceptance features are not split into frontend / backend")

    files = sorted(resolved.glob("*.feature"))
    if not args.min_files <= len(files) <= args.max_files:
        errors.append(f"{root}: [A3] expected {args.min_files}-{args.max_files} feature files, found {len(files)}")

    counts = [check_file(f, f.name, errors) for f in files]
    open_tags = sum(c[0] for c in counts)
    done_tags = sum(c[1] for c in counts)
    tags = open_tags + done_tags
    if not MIN_TAGS <= tags <= MAX_TAGS:
        errors.append(f"{root}: [A6] expected {MIN_TAGS}-{MAX_TAGS} clarification tags (open + clarified) "
                      f"across the set, found {tags}")

    for e in errors:
        sys.stdout.write(e + "\n")
    if errors:
        sys.stderr.write(f"{len(errors)} violation(s)\n")
        return 1
    sys.stdout.write(f"OK: {len(files)} feature files, {tags} clarification tags "
                     f"({open_tags} open, {done_tags} clarified)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
