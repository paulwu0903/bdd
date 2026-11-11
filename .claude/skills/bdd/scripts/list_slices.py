# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Resolve a /bdd scope inside one endpoint feature directory into its ordered slices as JSON.

A slice is one Example / Scenario / Scenario Outline. A scope is the endpoint directory itself, a
feature file in it, or `<feature file>:<line>` where the line is a `Rule:` line (every slice under
that Rule) or an Example / Scenario / Scenario Outline line (that slice only). --scope may be given
several times (e.g. the feature files of one endpoint in a /tasks phase); slices are merged without
duplicates. Slices are listed in
file-name order, then in the order they appear in each file. For every slice the DSL patterns its
steps use (Background steps included) are matched against the endpoint dsl.md.

Exit codes: 0 ok; 1 some step matches no DSL pattern (an upstream gap: hand back to /dsl-refine);
2 bad arguments or a scope outside the endpoint directory.

Usage:
    uv run scripts/list_slices.py --feature-dir specs/truth/features/<endpoint> --dsl-root specs/truth/features/<endpoint> --scope <dir | file | file:line> [--scope ...]
    uv run scripts/list_slices.py --feature-dir <features/<endpoint>> --dsl <features/<endpoint>/dsl.md> --scope <dir | file | file:line> [--scope ...]
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


KEYWORDS = ("Given", "When", "Then")
CONTINUATIONS = ("And", "But", "*")
SLICE_KEYWORDS = ("Scenario Outline", "Scenario Template", "Example", "Scenario")
# Same value shapes as gherkin-and-dsl's verify_features.py: quoted string, Outline placeholder, number.
STRICT_VALUE = r'"[^"]*"|<[^>]*>|-?\d+(?:\.\d+)?'
LOOSE_VALUE = r".+?"
TRACE_TAG = re.compile(r"^@(ac|spec):")


class Pattern:
    def __init__(self, keyword: str, text: str) -> None:
        self.keyword = keyword
        self.text = text
        parts = re.split(r"\{[^}]*\}", text)
        self.strict = re.compile("^" + f"({STRICT_VALUE})".join(re.escape(p) for p in parts) + "$")
        self.loose = re.compile("^" + f"({LOOSE_VALUE})".join(re.escape(p) for p in parts) + "$")


def split_row(line: str) -> list[str]:
    inner = line.strip().strip("|")
    return [c.strip() for c in re.split(r"(?<!\\)\|", inner)]


def parse_dsl(text: str) -> dict[str, list[Pattern]]:
    # Pattern = first backticked cell of each row under `## Given|When|Then 句型`.
    tables: dict[str, list[Pattern]] = {k: [] for k in KEYWORDS}
    section = None
    for line in text.splitlines():
        if line.startswith("#"):
            m = re.match(r"^## (Given|When|Then) 句型", line)
            section = m.group(1) if m else None
            continue
        if section is None or not line.startswith("|"):
            continue
        m = re.fullmatch(r"`([^`]+)`", split_row(line)[0])
        if m:
            tables[section].append(Pattern(section, m.group(1)))
    return tables


def match_pattern(tables: dict[str, list[Pattern]], keyword: str, text: str) -> Pattern | None:
    for attr in ("strict", "loose"):
        hits = [p for p in tables.get(keyword, []) if getattr(p, attr).match(text)]
        if hits:
            return hits[0]
    return None


def parse_tags(line: str) -> list[str]:
    text = re.split(r"\s#", line.strip(), maxsplit=1)[0]
    return ["@" + t.strip() for t in text.split("@") if t.strip()]


def header(stripped: str) -> tuple[str, str] | None:
    # Returns (kind, title) for Feature / Rule / Background / slice header lines.
    for kind in ("Feature", "Rule", "Background", *SLICE_KEYWORDS):
        if stripped.startswith(kind + ":"):
            return kind, stripped[len(kind) + 1:].strip()
    return None


def parse_feature(path: Path, tables: dict[str, list[Pattern]]) -> tuple[list[dict], list[dict]]:
    """Return (slices, rules) of one feature file; each slice carries its matched patterns."""
    slices: list[dict] = []
    rules: list[dict] = []
    feature_bg: list[tuple[str, str, int]] = []
    rule_bg: list[tuple[str, str, int]] = []
    current_rule: dict | None = None
    target: list | None = None  # where step lines go: a background list or the open slice's steps
    pending_tags: list[str] = []
    prev_kw = None
    lines = path.read_text(encoding="utf-8").splitlines()
    in_doc = False
    for no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if stripped.startswith('"""') or stripped.startswith("```"):
            in_doc = not in_doc
            continue
        if in_doc or not stripped or stripped.startswith("#") or stripped.startswith("|"):
            continue
        if stripped.startswith("@"):
            pending_tags += parse_tags(stripped)
            continue
        h = header(stripped)
        if h:
            kind, title = h
            prev_kw = None
            if kind == "Feature":
                target = None
            elif kind == "Rule":
                current_rule = {"line": no, "title": title, "slices": []}
                rules.append(current_rule)
                rule_bg = []
                target = None
            elif kind == "Background":
                target = rule_bg if current_rule else feature_bg
            elif kind in SLICE_KEYWORDS:
                item = {
                    "file": str(path),
                    "line": no,
                    "keyword": kind,
                    "title": title,
                    "rule": current_rule["title"] if current_rule else None,
                    "rule_line": current_rule["line"] if current_rule else None,
                    "tags": pending_tags,
                    "trace_tags": [t for t in pending_tags if TRACE_TAG.match(t)],
                    "_steps": list(feature_bg) + list(rule_bg),
                }
                slices.append(item)
                if current_rule:
                    current_rule["slices"].append(item)
                target = item["_steps"]
            pending_tags = []
            continue
        if stripped.startswith("Examples:") or stripped.startswith("Scenarios:"):
            pending_tags = []
            target = None
            continue
        m = re.match(r"^(Given|When|Then|And|But|\*)\s+(.*)$", stripped)
        if m and target is not None:
            kw = m.group(1)
            if kw in CONTINUATIONS:
                kw = prev_kw or "Given"
            prev_kw = kw
            target.append((kw, m.group(2).strip(), no))
    for item in slices:
        used, unmatched, seen = [], [], set()
        for kw, text, no in item.pop("_steps"):
            p = match_pattern(tables, kw, text)
            if p is None:
                unmatched.append({"keyword": kw, "text": text, "line": no})
            elif (p.keyword, p.text) not in seen:
                seen.add((p.keyword, p.text))
                used.append({"keyword": p.keyword, "pattern": p.text})
        item["patterns"] = used
        item["unmatched_steps"] = unmatched
    return slices, rules


def parse_scope(scope: str) -> tuple[Path, int | None]:
    m = re.match(r"^(.*\.feature):(\d+)$", scope)
    if m:
        return Path(m.group(1)), int(m.group(2))
    return Path(scope), None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve a /bdd scope inside one endpoint feature directory into its ordered slices as JSON."
    )
    parser.add_argument("--feature-dir", required=True, help="Endpoint directory, e.g. specs/truth/features/backend")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dsl", help="The endpoint's single dsl.md")
    source.add_argument("--dsl-root", help="Endpoint directory whose <module>/dsl.md files are merged (specs/truth/features/<endpoint>)")
    parser.add_argument("--scope", required=True, action="append",
                        help="The endpoint directory, a feature file in it, or <feature file>:<line>; repeatable")
    args = parser.parse_args()

    feature_dir = Path(args.feature_dir)
    dsls = [Path(args.dsl)] if args.dsl else sorted(Path(args.dsl_root).rglob("dsl.md"))
    if not feature_dir.is_dir():
        sys.stderr.write(f"error: '{feature_dir}' is not a directory; pass the endpoint feature directory with --feature-dir\n")
        return 2
    if not dsls or not all(d.is_file() for d in dsls):
        sys.stderr.write("error: no endpoint dsl.md found; pass --dsl <dsl.md> or --dsl-root <endpoint directory>, or run /dsl-refine first\n")
        return 2
    root = feature_dir.resolve()
    tables: dict[str, list[Pattern]] = {}
    for d in dsls:
        for kw, rows in parse_dsl(d.read_text(encoding="utf-8")).items():
            tables.setdefault(kw, []).extend(rows)
    parsed: dict[Path, tuple[list[dict], list[dict]]] = {}
    slices: list[dict] = []
    seen_slices: set[tuple[str, int]] = set()
    for scope in args.scope:
        scope_path, scope_line = parse_scope(scope)
        target = scope_path.resolve()
        if target != root and root not in target.parents:
            sys.stderr.write(
                f"error: scope '{scope}' is outside '{feature_dir}'; a /bdd scope must stay inside one endpoint directory\n"
            )
            return 2
        if target.is_dir():
            if target != root:
                sys.stderr.write(f"error: scope '{scope}' must be the endpoint directory itself, a feature file, or file:line\n")
                return 2
            # Module folders (specs/truth/features/<endpoint>/<module>/) are included.
            files = sorted(root.rglob("*.feature"))
        elif target.is_file() and target.suffix == ".feature":
            files = [target]
        else:
            sys.stderr.write(f"error: '{scope_path}' is not a feature file or directory; check the scope path\n")
            return 2
        picked: list[dict] = []
        for f in files:
            if f not in parsed:
                parsed[f] = parse_feature(f, tables)
            file_slices, rules = parsed[f]
            if scope_line is None:
                picked += file_slices
                continue
            hit_rule = next((r for r in rules if r["line"] == scope_line), None)
            hit_slice = next((x for x in file_slices if x["line"] == scope_line), None)
            if hit_rule:
                picked += hit_rule["slices"]
            elif hit_slice:
                picked.append(hit_slice)
            else:
                sys.stderr.write(
                    f"error: line {scope_line} of '{f}' is not a Rule or Example / Scenario Outline line; "
                    "point the scope at the header line of the block\n"
                )
                return 2
        for x in picked:
            key = (x["file"], x["line"])
            if key not in seen_slices:
                seen_slices.add(key)
                slices.append(x)

    cwd = Path.cwd().resolve()
    for s in slices:
        p = Path(s["file"]).resolve()
        s["file"] = str(p.relative_to(cwd)) if cwd in p.parents else str(p)
    union, seen = [], set()
    for s in slices:
        for p in s["patterns"]:
            key = (p["keyword"], p["pattern"])
            if key not in seen:
                seen.add(key)
                union.append(p)
    gaps = [{"file": s["file"], **u} for s in slices for u in s["unmatched_steps"]]
    result = {
        "feature_dir": str(feature_dir),
        "scope": args.scope,
        "slice_count": len(slices),
        "slices": slices,
        "patterns_used": union,
        "unmatched_steps": gaps,
    }
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if gaps:
        sys.stderr.write(f"{len(gaps)} step(s) match no dsl.md pattern; this is an upstream gap, hand back to /dsl-refine\n")
        return 1
    if not slices:
        sys.stderr.write("error: the scope contains no Example / Scenario / Scenario Outline\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
