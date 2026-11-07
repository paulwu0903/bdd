# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Create the next numbered feature directory under specs/ and print its path.

Usage:
    uv run scripts/create_feature.py --short-name <kebab-case-name>
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


SPECS_ROOT = Path("specs")
_SHORT_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FEATURE_DIR = re.compile(r"^(\d{3})-")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the next numbered feature directory under specs/ and print its path.")
    parser.add_argument("--short-name", required=True, help="Project name in lowercase kebab-case, e.g. photo-album-organizer")
    args = parser.parse_args()
    if not _SHORT_NAME.match(args.short_name):
        sys.stderr.write(
            f"error: '{args.short_name}' is not lowercase kebab-case; pass e.g. --short-name photo-album-organizer\n"
        )
        return 2
    # Next number is the highest existing NNN prefix plus one; start at 001.
    numbers = [
        int(m.group(1))
        for d in (SPECS_ROOT.iterdir() if SPECS_ROOT.is_dir() else [])
        if d.is_dir() and (m := _FEATURE_DIR.match(d.name))
    ]
    feature_dir = SPECS_ROOT / f"{max(numbers, default=0) + 1:03d}-{args.short_name}"
    feature_dir.mkdir(parents=True)
    sys.stdout.write(f"{feature_dir.as_posix()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
