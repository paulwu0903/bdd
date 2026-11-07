# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""List API routes and calls in source code whose path is not a path of the OpenAPI contract (orphans).

Contract paths are the `paths` keys of the openapi file, prefixed with the path of its servers[0] url
(e.g. `http://127.0.0.1:3000/api` -> `/api`). Source candidates are string literals ('…', "…", `…`) of the
given directories that start with that prefix, or that start with `/` and whose first segment is the first
segment of a contract path (routes mounted under the prefix, client calls joined to a base URL). Before
comparing, the prefix and any query string are dropped and `:id`, `${…}` and `{param}` segments become one
placeholder; a `${…}` glued to the end of a segment (`/state${query}`) is treated as a query suffix.
Exit 1 when any orphan is found, 0 when none, 2 on unusable input.

Usage:
    uv run scripts/check_orphan_routes.py --openapi specs/truth/contracts/openapi.yaml --src <dir> [--src <dir> ...]
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


_require("yaml")

import yaml  # noqa: E402

SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
SKIP_DIRS = {"node_modules", "dist", "build", "coverage", ".features-gen"}
LITERAL = re.compile(r"'((?:\\.|[^'\\\n])*)'|\"((?:\\.|[^\"\\\n])*)\"|`((?:\\.|[^`\\])*)`")
PLACEHOLDER = "{}"


def normalize(path: str, prefix: str) -> str | None:
    """Contract-comparable form of a path: no prefix, no query, parameter segments as {}; None when not a path."""
    path = path.split("?", 1)[0].split("#", 1)[0]
    if prefix and (path == prefix or path.startswith(prefix + "/")):
        path = path[len(prefix):]
    if not path.startswith("/"):
        return None
    segments = []
    parts = path.strip("/").split("/")
    for index, seg in enumerate(parts):
        if not seg:
            continue
        if re.fullmatch(r"\$\{[^}]*\}|:[A-Za-z_]\w*|\{[^}]*\}", seg):
            segments.append(PLACEHOLDER)
            continue
        glued = re.match(r"^([^$]+)\$\{[^}]*\}$", seg)
        if glued and index == len(parts) - 1:
            segments.append(glued.group(1))  # `/state${query}`: the template is a query suffix
            continue
        if not re.fullmatch(r"[\w.~-]+", seg):
            return None
        segments.append(seg)
    return "/" + "/".join(segments) if segments else None


def main() -> int:
    parser = argparse.ArgumentParser(description="List API routes and calls in source code whose path is not a path of the OpenAPI contract (orphans).")
    parser.add_argument("--openapi", required=True, help="OpenAPI contract, e.g. specs/truth/contracts/openapi.yaml")
    parser.add_argument("--src", required=True, action="append", help="Source directory to scan, e.g. backend/src; repeat for several")
    args = parser.parse_args()
    spec_path = Path(args.openapi)
    if not spec_path.is_file():
        sys.stderr.write(f"error: '{spec_path}' does not exist; pass the truth contract (specs/truth/contracts/openapi.yaml)\n")
        return 2
    try:
        doc = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        sys.stderr.write(f"error: '{spec_path}' is not valid YAML ({exc}); fix the contract first\n")
        return 2
    paths = doc.get("paths") or {}
    if not isinstance(paths, dict) or not paths:
        sys.stderr.write(f"error: '{spec_path}' has no paths; pass an OpenAPI file with a paths section\n")
        return 2
    servers = doc.get("servers") or []
    url = servers[0].get("url", "") if servers and isinstance(servers[0], dict) else ""
    prefix = re.sub(r"^[a-zA-Z][\w+.-]*://[^/]+", "", url).rstrip("/")
    contract = {normalize(p, "") for p in paths}
    contract.discard(None)
    first_segments = {p.split("/")[1] for p in contract}

    dirs = [Path(d) for d in args.src]
    for d in dirs:
        if not d.is_dir():
            sys.stderr.write(f"error: '{d}' is not a directory; pass source roots such as backend/src and frontend/src\n")
            return 2
    orphans: list[tuple[str, int, str, str]] = []
    scanned = matched = 0
    for d in dirs:
        for f in sorted(d.rglob("*")):
            if not f.is_file() or f.suffix not in SOURCE_SUFFIXES or SKIP_DIRS & set(f.parts):
                continue
            scanned += 1
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in LITERAL.finditer(text):
                value = next(g for g in m.groups() if g is not None)
                if not value.startswith("/"):
                    continue
                prefixed = bool(prefix) and (value == prefix or value.startswith(prefix + "/"))
                norm = normalize(value, prefix)
                if norm is None:
                    continue
                if not prefixed and norm.split("/")[1] not in first_segments:
                    continue
                matched += 1
                if norm not in contract:
                    orphans.append((f.as_posix(), text.count("\n", 0, m.start()) + 1, value, norm))
    out = [f"contract: {len(contract)} paths under prefix '{prefix or '/'}'; scanned {scanned} files, {matched} path literals"]
    if orphans:
        out.append(f"ORPHANS ({len(orphans)}):")
        out += [f"- {file}:{line} `{value}` (as {norm})" for file, line, value, norm in orphans]
    else:
        out.append("ORPHANS (0)")
    sys.stdout.write("\n".join(out) + "\n")
    if orphans:
        sys.stderr.write("orphan routes or calls found: remove them (see the 移除 rule) or add the path to the contract through /api-plan\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
