# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6,<7",
#   "orjson>=3,<4",
# ]
# ///
"""Convert a YAML file to JSON on stdout.

Usage:
    uv run scripts/yaml_to_json.py <source> [--indent]
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


_require("yaml", "orjson")

import orjson  # noqa: E402
import yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a YAML file to JSON on stdout.")
    parser.add_argument("source", help="Path to the YAML file")
    parser.add_argument("--indent", action="store_true", help="Pretty-print with two-space indent")
    args = parser.parse_args()
    source = Path(args.source)
    if not source.is_file():
        sys.stderr.write(f"error: '{source}' is not a file; pass the path to an existing YAML file\n")
        return 2
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    option = orjson.OPT_INDENT_2 if args.indent else 0
    sys.stdout.write(orjson.dumps(data, option=option).decode() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
