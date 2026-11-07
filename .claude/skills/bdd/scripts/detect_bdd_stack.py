# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6,<7",
# ]
# ///
"""Detect an endpoint project's BDD framework (cucumber-js or playwright-bdd) and print the /bdd commands as JSON.

Also reports whether the framework config's feature paths cover every feature file of the endpoint
feature directory given with --features. Command templates use these placeholders:
  <title-regex>  regular expression of one or more slice titles, e.g. ^(標題一|標題二)$
JS configs are read statically (best effort, not executed); config_parse says which way was used.

Usage:
    uv run scripts/detect_bdd_stack.py --project <endpoint code root> --features specs/truth/features/<endpoint> [--framework cucumber-js|playwright-bdd]
"""
import argparse
import glob
import json
import os
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
CUCUMBER_CONFIGS = ("cucumber.json", "cucumber.yaml", "cucumber.yml", "cucumber.js", "cucumber.cjs", "cucumber.mjs")
CUCUMBER_DEFAULT_PATHS = ["features/**/*.{feature,feature.md}"]
PLAYWRIGHT_CONFIGS = ("playwright.config.ts", "playwright.config.js", "playwright.config.mjs", "playwright.config.cjs")
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


def _js_values(text: str, key: str) -> list[str]:
    # Static, best-effort read of `key: ['a', "b"]` or `key: 'a'` from a JS/TS config; JS is not executed.
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


def _base_dir(pattern: str) -> str:
    # Directory part of a glob before the first wildcard, e.g. tests/bdd/**/*.ts -> tests/bdd.
    head = _GLOB_CHARS.split(pattern, maxsplit=1)[0]
    if head.endswith("/"):
        base = head.rstrip("/")
    elif head == pattern and not Path(pattern).suffix:
        base = pattern
    else:
        base = str(Path(head).parent)
    return base.removeprefix("./") or "."


def _is_single_file(pattern: str) -> bool:
    return not _GLOB_CHARS.search(pattern) and bool(Path(pattern).suffix)


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _expand_braces(pattern: str) -> list[str]:
    # glob does not support {a,b}; expand one level at a time.
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    out = []
    for alt in m.group(1).split(","):
        out += _expand_braces(pattern[: m.start()] + alt + pattern[m.end():])
    return out


def _matched_files(project: Path, patterns: list[str]) -> set[Path]:
    # Resolve config feature globs relative to the project root; a directory entry means every feature under it.
    found: set[Path] = set()
    for pattern in patterns:
        for p in _expand_braces(pattern.split(":")[0] if re.search(r"\.feature:\d+$", pattern) else pattern):
            full = os.path.join(str(project), p)
            if os.path.isdir(full):
                full = os.path.join(full, "**", "*.feature")
            found.update(Path(f).resolve() for f in glob.glob(full, recursive=True))
    return found


def _coverage(project: Path, patterns: list[str], features: Path) -> dict:
    wanted = sorted(f.resolve() for f in features.rglob("*.feature"))
    matched = _matched_files(project, patterns)
    missing = [os.path.relpath(f, project) for f in wanted if f not in matched]
    return {
        "endpoint_feature_files": len(wanted),
        "covers_features": not missing,
        "uncovered_feature_files": missing,
        "feature_path_to_add": os.path.relpath(features.resolve(), project).replace(os.sep, "/") + "/**/*.feature",
    }


def _cucumber(project: Path, deps: dict, features: Path) -> dict:
    config_file = next((project / n for n in CUCUMBER_CONFIGS if (project / n).is_file()), None)
    profile: dict = {}
    mode = None
    if config_file is not None:
        text = config_file.read_text(encoding="utf-8")
        if config_file.suffix == ".json":
            profile, mode = _default_profile(json.loads(text)), "parsed"
        elif config_file.suffix in (".yaml", ".yml"):
            profile, mode = _default_profile(yaml.safe_load(text)), "parsed"
        else:
            profile = {k: _js_values(text, k) for k in ("paths", "import", "require")}
            tags = re.search(r"""\btags\s*:\s*['"`]([^'"`]+)['"`]""", text)
            profile["tags"] = tags.group(1) if tags else None
            mode = "heuristic"
    feature_globs = _as_list(profile.get("paths")) or CUCUMBER_DEFAULT_PATHS
    support = _as_list(profile.get("import")) + _as_list(profile.get("require"))
    tags = profile.get("tags")
    if isinstance(tags, list):
        tags = " and ".join(f"({t})" for t in tags)
    cli = "npx cucumber-js"
    return {
        "framework": "cucumber-js",
        "version": deps["@cucumber/cucumber"],
        "installed": _installed(project, "@cucumber", "cucumber"),
        "config_file": config_file.name if config_file else None,
        "config_parse": mode,
        "config_feature_key": "paths",
        "feature_globs": feature_globs,
        "step_dirs": _unique([_base_dir(g) for g in support if not _is_single_file(g)]) or None,
        "config_tags": tags or None,
        **_coverage(project, feature_globs, features),
        "commands": {
            "snippets": f"{cli} --dry-run --format snippets",
            "dry_run": f"{cli} --dry-run",
            "run_slices": f'{cli} --name "<title-regex>"',
            "run_all": f"{cli} --order random",
            "unused_steps": f"{cli} --dry-run --format usage",
        },
        "notes": [
            "Feature paths given on the cucumber-js CLI are added to the config paths, not substituted; "
            "slices are therefore selected with --name.",
            "Scenario names are regular expressions; escape regex metacharacters in slice titles.",
        ],
    }


def _playwright_bdd(project: Path, deps: dict, features: Path) -> dict:
    config_file = next((project / n for n in PLAYWRIGHT_CONFIGS if (project / n).is_file()), None)
    text = config_file.read_text(encoding="utf-8") if config_file else ""
    feature_globs = _js_values(text, "features")
    steps = _js_values(text, "steps")
    root = _js_values(text, "featuresRoot")
    missing = re.search(r"""\bmissingSteps\s*:\s*['"`]([^'"`]+)['"`]""", text)
    return {
        "framework": "playwright-bdd",
        "version": deps["playwright-bdd"],
        "installed": _installed(project, "playwright-bdd"),
        "config_file": config_file.name if config_file else None,
        "config_parse": "heuristic" if config_file else None,
        "config_feature_key": "defineBddConfig features",
        "feature_globs": feature_globs,
        "step_dirs": _unique([_base_dir(g) for g in steps if not _is_single_file(g)]) or None,
        "features_root": root[0] if root else None,
        "missing_steps": missing.group(1) if missing else "fail-on-gen",
        **_coverage(project, feature_globs, features),
        "commands": {
            "snippets": "npx bddgen",
            "dry_run": "npx bddgen",
            "run_slices": 'npx bddgen && npx playwright test --grep "<title-regex>"',
            "run_all": "npx bddgen && npx playwright test",
            "unused_steps": "npx bddgen export --unused-steps",
        },
        "notes": [
            "bddgen prints snippets for missing steps only when missingSteps is fail-on-gen (the default).",
            "--grep matches the full test title; slice titles are regular expressions, escape metacharacters.",
            "featuresRoot is the common parent of every feature path; when adding a feature path outside it, "
            "widen featuresRoot to a common parent directory as well.",
        ],
    }


def _installed(project: Path, *parts: str) -> bool:
    # npm workspaces hoist packages, so look upwards from the project root too.
    for base in (project, *project.parents):
        if (base / "node_modules").joinpath(*parts).is_dir():
            return True
    return False


def detect(project: Path, features: Path, framework: str | None) -> dict:
    package_file = project / "package.json"
    if not package_file.is_file():
        return {"detected": False, "reason": "package.json not found; pass the endpoint code root with --project"}
    try:
        package = json.loads(package_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"detected": False, "reason": f"package.json is not valid JSON ({exc}); fix it and rerun"}
    deps = _dependencies(package)
    found = [f for f, dep in (("playwright-bdd", "playwright-bdd"), ("cucumber-js", "@cucumber/cucumber")) if dep in deps]
    if framework:
        if framework not in found:
            return {"detected": False, "reason": f"{framework} is not in dependencies or devDependencies"}
        found = [framework]
    if not found:
        return {"detected": False, "reason": "neither playwright-bdd nor @cucumber/cucumber is in dependencies or devDependencies"}
    if len(found) > 1:
        return {"detected": False, "reason": "both playwright-bdd and @cucumber/cucumber are declared; rerun with --framework"}
    result = _playwright_bdd(project, deps, features) if found[0] == "playwright-bdd" else _cucumber(project, deps, features)
    return {"detected": True, **result}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect an endpoint project's BDD framework and print the /bdd commands as JSON."
    )
    parser.add_argument("--project", required=True, help="Endpoint code root that contains package.json")
    parser.add_argument("--features", required=True, help="Endpoint feature directory, e.g. specs/truth/features/backend")
    parser.add_argument("--framework", choices=("cucumber-js", "playwright-bdd"), help="Pick one when both are declared")
    args = parser.parse_args()
    project = Path(args.project)
    features = Path(args.features)
    if not project.is_dir():
        sys.stderr.write(f"error: '{project}' is not a directory; pass the endpoint code root with --project <dir>\n")
        return 2
    if not features.is_dir():
        sys.stderr.write(f"error: '{features}' is not a directory; pass the endpoint feature directory with --features <dir>\n")
        return 2
    try:
        result = detect(project.resolve(), features.resolve(), args.framework)
    except (OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: could not read the framework config ({exc}); fix the file and rerun\n")
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
