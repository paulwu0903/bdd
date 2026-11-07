# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6,<7",
# ]
# ///
"""Detect a project's cucumber-js setup and print the commands the BDD loop needs as JSON.

Usage:
    uv run scripts/detect_bdd_stack.py --project <project-root>
"""
import argparse
import json
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


_require("yaml")

import yaml  # noqa: E402

# Lookup order documented by cucumber-js (docs/configuration.md): first file found wins.
CONFIG_FILES = ("cucumber.json", "cucumber.yaml", "cucumber.yml", "cucumber.js", "cucumber.cjs", "cucumber.mjs")
CLI = "npx cucumber-js"
DEFAULT_FEATURE_DIR = "features"
_GLOB_CHARS = re.compile(r"[*?\[{]")


def _dependencies(package: dict) -> dict:
    deps: dict = {}
    for key in ("dependencies", "devDependencies"):
        deps.update(package.get(key) or {})
    return deps


def _default_profile(data: object) -> dict:
    # JSON/YAML configs hold profiles; "default" is the one used without --profile.
    if isinstance(data, dict):
        profile = data.get("default", data)
        if isinstance(profile, dict):
            return profile
    return {}


def _js_array(text: str, key: str) -> list[str]:
    # Static, best-effort read of `key: ['a', "b"]` or `key: 'a'` from a JS config; JS is not executed.
    m = re.search(rf"\b{key}\s*:\s*\[(.*?)\]", text, re.S)
    if m:
        return re.findall(r"""['"`]([^'"`]+)['"`]""", m.group(1))
    m = re.search(rf"""\b{key}\s*:\s*['"`]([^'"`]+)['"`]""", text)
    return [m.group(1)] if m else []


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def _read_config(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return _default_profile(json.loads(text)), "parsed"
    if path.suffix in (".yaml", ".yml"):
        return _default_profile(yaml.safe_load(text)), "parsed"
    profile = {key: _js_array(text, key) for key in ("paths", "import", "require")}
    tags = re.search(r"""\btags\s*:\s*['"`]([^'"`]+)['"`]""", text)
    profile["tags"] = tags.group(1) if tags else None
    return profile, "heuristic"


def _base_dir(pattern: str) -> str:
    # Directory part of a glob before the first wildcard, e.g. features/steps/**/*.ts -> features/steps.
    head = _GLOB_CHARS.split(pattern, maxsplit=1)[0]
    if head.endswith("/"):
        base = head.rstrip("/")
    elif head == pattern and not Path(pattern).suffix:
        base = pattern
    else:
        base = str(Path(head).parent)
    return base.removeprefix("./") or "."


def _is_single_file(pattern: str) -> bool:
    # Entries such as ./tsx-register.js are loaders, not step directories.
    return not _GLOB_CHARS.search(pattern) and bool(Path(pattern).suffix)


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def detect(project: Path) -> dict:
    package_file = project / "package.json"
    if not package_file.is_file():
        return {"detected": False, "reason": "package.json not found; this is not a Node.js project"}
    try:
        package = json.loads(package_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"detected": False, "reason": f"package.json is not valid JSON ({exc}); fix it and rerun"}
    deps = _dependencies(package)
    if "@cucumber/cucumber" not in deps:
        return {"detected": False, "reason": "@cucumber/cucumber is not in dependencies or devDependencies"}

    config_file = next((project / name for name in CONFIG_FILES if (project / name).is_file()), None)
    profile: dict = {}
    config_mode = None
    if config_file is not None:
        profile, config_mode = _read_config(config_file)

    feature_globs = _as_list(profile.get("paths"))
    support_globs = _as_list(profile.get("import")) + _as_list(profile.get("require"))
    feature_dirs = _unique([_base_dir(g) for g in feature_globs]) or [DEFAULT_FEATURE_DIR]
    step_dirs = _unique([_base_dir(g) for g in support_globs if not _is_single_file(g)])
    tags = profile.get("tags")
    if isinstance(tags, list):
        tags = " and ".join(f"({t})" for t in tags)

    return {
        "detected": True,
        "installed": (project / "node_modules" / "@cucumber" / "cucumber").is_dir(),
        "cucumber_version": deps["@cucumber/cucumber"],
        "config_file": config_file.name if config_file else None,
        "config_parse": config_mode,
        "feature_dirs": feature_dirs,
        "step_dirs": step_dirs or None,
        "config_tags": tags or None,
        "commands": {
            "lint": f"npx gherkin-lint {' '.join(feature_dirs)}" if "gherkin-lint" in deps else None,
            "snippets": f"{CLI} --dry-run --format snippets",
            "run_scenario": f"{CLI} <feature-file>:<line>",
            "run_all_random": f"{CLI} --order random",
            "usage": f"{CLI} --dry-run --format usage",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect a project's cucumber-js setup and print the commands the BDD loop needs as JSON."
    )
    parser.add_argument("--project", required=True, help="Project root directory that contains package.json")
    args = parser.parse_args()
    project = Path(args.project)
    if not project.is_dir():
        sys.stderr.write(f"error: '{project}' is not a directory; pass the project root with --project <dir>\n")
        return 2
    try:
        result = detect(project.resolve())
    except (OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: could not read the cucumber config ({exc}); fix the file and rerun\n")
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
