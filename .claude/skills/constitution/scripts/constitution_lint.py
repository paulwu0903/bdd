# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Lint the constitution files: Applies To header, 引用 / 驗證 paths and RuleFile structure.

Usage:
    uv run scripts/constitution_lint.py --root .claude/constitution
"""
import argparse
import re
import sys
from pathlib import Path

RULE_H1 = re.compile(r"^# Rule (\d+) - .+ \[(MUST|SHOULD|MAY)\]$")
BACKTICK = re.compile(r"`([^`]+)`")


def lint_file(path: Path, root: Path) -> list[str]:
    # Return violations of one constitution file as "<file>: <message>" lines.
    rel = path.relative_to(root).as_posix()
    lines = path.read_text(encoding="utf-8").splitlines()
    errors: list[str] = []
    if not lines or not lines[0].startswith("- Applies To："):
        errors.append(f"{rel}: first line must start with '- Applies To：'")

    for line in lines:
        if line.startswith("- 引用："):
            for ref in BACKTICK.findall(line):
                if not (root / ref).is_file():
                    errors.append(f"{rel}: 引用 target not found: {ref}")
        elif line.startswith("- 驗證："):
            value = line[len("- 驗證："):].strip()
            if value == "lint":
                continue
            if not value.startswith("script "):
                errors.append(f"{rel}: 驗證 must be 'script checks/<名稱>.py' or 'lint': {value}")
            elif not (root / value[len("script "):].strip()).is_file():
                errors.append(f"{rel}: 驗證 script not found: {value[len('script '):].strip()}")

    blocks: list[str] = []
    rule_count, in_code = 0, False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("# "):
            match = RULE_H1.match(line)
            if not match:
                errors.append(f"{rel}: H1 is not '# Rule N - 名稱 [MUST|SHOULD|MAY]': {line}")
            else:
                rule_count += 1
                if int(match.group(1)) != rule_count:
                    errors.append(f"{rel}: Rule numbering out of order: {line}")
            blocks.append("R")
        elif line.startswith("## "):
            title = line[3:].strip()
            blocks.append({"Good Example": "G", "Bad Example": "B"}.get(title, "?"))
            following = next((x for x in lines[i + 1:] if x.strip()), "")
            if not following.startswith("- "):
                errors.append(f"{rel}: first line under '{line}' must be a bullet")
    if "".join(blocks) != "RGB" * rule_count:
        errors.append(f"{rel}: each Rule must be followed by '## Good Example' then '## Bad Example'")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint the constitution files.")
    parser.add_argument("--root", required=True, type=Path, help="constitution root, e.g. .claude/constitution")
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        sys.stderr.write(f"constitution root not found: {root}\n")
        return 2
    errors: list[str] = []
    if not (root / "CONSTITUTION.md").is_file():
        errors.append("CONSTITUTION.md: missing")
    files = sorted((root / "shared").glob("*.md")) + sorted((root / "skills").glob("*/*.md"))
    for path in files:
        errors.extend(lint_file(path, root))

    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"OK: {len(files)} constitution files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
