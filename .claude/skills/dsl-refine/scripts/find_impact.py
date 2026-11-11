# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List the truth feature Examples and dsl.md rows a plan's MODIFY / DELETE may affect, as truth-delta 部位.

Searches every endpoint under <truth>/features with three signals:
  tag      an Example / Scenario Outline tagged `@spec:<id>` for an id under change
  literal  a feature unit (Feature description, Background, Rule title, Example title, step, `# 名稱=值`
           comment, Data Table or Examples cell) or a dsl.md row / 說明 / 附錄 containing a changed literal
  usage    an Example whose step uses a dsl.md pattern whose row the literal signal hit (the row's
           default parameters or implementation semantics change for every user), endpoint-wide
Ids default to the MODIFY / DELETE rows of the plan spec.md `## 既有需求異動` table; --id overrides.
Literals come only from --term (written by the caller). A numeric literal does not match inside a
longer number ("200" does not hit "2000").

Output (stdout): a Markdown table `| 部位 | 信號 | 證據 |`, one row per unit in truth-delta features
部位 form (`<端點>/<模組>/<檔>.feature › Rule: <規則> › Example: <標題>`, `<端點>/<模組>/dsl.md › <Given|When|Then> › <句型>`),
then a summary line. These are candidates for /truth-delta 判定影響, not decisions. Exit 0; exit 2 on bad input.

Usage:
    uv run scripts/find_impact.py --plan <specs/plans/NNN-name> [--id <NNN/FR-nnn> ...] [--term <literal> ...] [--truth <specs/truth>]
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


CHANGE_ROW = re.compile(r"^\|\s*\d+\s*\|\s*(MODIFY|DELETE)\s*\|\s*`(\d{3}/(?:N?FR|SC)-\d+[a-z]?)`")
RULE_KW = re.compile(r"^\s*Rule:\s*(.*)$")
EXAMPLE_KW = re.compile(r"^\s*(Example|Scenario Outline|Scenario Template|Scenario):\s*(.*)$")
STEP_KW = re.compile(r"^\s*(Given|When|Then|And|But)\s+(.*)$")
DSL_ROW = re.compile(r"^\| `([^`]+)` \|")


class Unit:
    def __init__(self, loc: str) -> None:
        self.loc = loc
        self.lines: list[tuple[int, str]] = []
        self.tags: list[str] = []
        self.steps: list[tuple[int, str, str]] = []  # (line, resolved keyword, text)


def changed_ids(spec: Path) -> list[str]:
    ids: list[str] = []
    if not spec.is_file():
        return ids
    in_changes = False
    for line in spec.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_changes = line.strip() == "## 既有需求異動"
            continue
        m = CHANGE_ROW.match(line) if in_changes else None
        if m and m.group(2) not in ids:
            ids.append(m.group(2))
    return ids


def term_regex(term: str) -> re.Pattern:
    # Digits at either end must not continue into a longer number.
    left = r"(?<!\d)" if term[:1].isdigit() else ""
    right = r"(?!\d)" if term[-1:].isdigit() else ""
    return re.compile(left + re.escape(term) + right)


def feature_units(rel: str, text: str) -> list[Unit]:
    # Same unit boundaries as truth-delta's check_delta.py, so 部位 can be recorded as is.
    units = [Unit(f"{rel} › Feature")]
    rule, pending, last_kw = None, [], "Given"
    for n, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if s.startswith("@"):
            pending += ["@" + t.strip() for t in re.split(r"\s#", s, maxsplit=1)[0].split("@") if t.strip()]
            continue
        m_rule, m_ex = RULE_KW.match(raw), EXAMPLE_KW.match(raw)
        if m_rule:
            rule = m_rule.group(1).strip()
            units.append(Unit(f"{rel} › Rule: {rule}"))
        elif m_ex:
            label = f"{m_ex.group(1)}: {m_ex.group(2).strip()}"
            units.append(Unit(f"{rel} › Rule: {rule} › {label}" if rule else f"{rel} › {label}"))
            units[-1].tags = pending
        pending = []
        unit = units[-1]
        unit.lines.append((n, s))
        step = STEP_KW.match(raw)
        if step:
            kw = step.group(1)
            kw = last_kw if kw in ("And", "But") else kw
            last_kw = kw
            unit.steps.append((n, kw, step.group(2).strip()))
    return units


def dsl_units(rel: str, text: str) -> list[tuple[Unit, str | None, str | None]]:
    # (unit, keyword, pattern) per dsl.md row, plus the 說明 and 附錄 blocks with keyword None.
    out: list[tuple[Unit, str | None, str | None]] = []
    intro, appendix, keyword = Unit(f"{rel} › 說明"), None, None
    for n, line in enumerate(text.splitlines(), 1):
        heading = re.match(r"^## (Given|When|Then) 句型", line)
        if heading:
            keyword = heading.group(1)
            continue
        if line.startswith("## "):
            keyword = None
            if line.startswith("## 附錄"):
                appendix = Unit(f"{rel} › 附錄")
        if appendix is not None:
            appendix.lines.append((n, line))
            continue
        row = DSL_ROW.match(line)
        if keyword and row:
            u = Unit(f"{rel} › {keyword} › {row.group(1)}")
            u.lines.append((n, line))
            out.append((u, keyword, row.group(1)))
        elif keyword is None:
            intro.lines.append((n, line))
    out.append((intro, None, None))
    if appendix is not None:
        out.append((appendix, None, None))
    return out


def pattern_regex(pattern: str) -> re.Pattern:
    parts = re.split(r"\{[^}]*\}", pattern)
    return re.compile("^" + "(.+?)".join(re.escape(p) for p in parts) + "$")


def main() -> int:
    parser = argparse.ArgumentParser(description="List truth feature Examples and dsl.md rows a plan's MODIFY / DELETE may affect.")
    parser.add_argument("--plan", required=True, help="Plan directory specs/plans/<NNN>-<name>")
    parser.add_argument("--id", action="append", default=[], help="Requirement id under change, e.g. 002/FR-002 (default: spec.md 既有需求異動)")
    parser.add_argument("--term", action="append", default=[], help="Literal value that changes, e.g. 200 (repeatable)")
    parser.add_argument("--truth", help="Truth directory (default: <plan>/../../truth)")
    args = parser.parse_args()
    plan = Path(args.plan).resolve()
    if not plan.is_dir() or not re.match(r"^\d{3}-", plan.name):
        sys.stderr.write(f"error: '{args.plan}' is not a plan directory; pass --plan specs/plans/<NNN>-<name>\n")
        return 2
    ids = args.id or changed_ids(plan / "spec.md")
    terms = [t for t in args.term if t.strip()]
    if not ids and not terms:
        sys.stderr.write("error: nothing to search; spec.md has no 既有需求異動 rows, pass --id <NNN/FR-nnn> or --term <literal>\n")
        return 2
    truth = Path(args.truth).resolve() if args.truth else plan.parent.parent / "truth"
    root = truth / "features"
    if not root.is_dir():
        sys.stderr.write(f"error: '{root}' is not a directory; pass --truth <specs/truth>\n")
        return 2
    regexes = [(t, term_regex(t)) for t in terms]
    hits: dict[str, list[tuple[str, str]]] = {}  # loc -> [(signal, evidence)]

    def hit(loc: str, signal: str, evidence: str) -> None:
        if (signal, evidence) not in hits.setdefault(loc, []):
            hits[loc].append((signal, evidence))

    endpoints = sorted(d for d in root.iterdir() if d.is_dir())
    for endpoint in endpoints:
        hot_patterns: list[tuple[str, str, re.Pattern]] = []
        for d in sorted(endpoint.rglob("dsl.md")):
            rel = str(d.relative_to(root))
            for unit, kw, pattern in dsl_units(rel, d.read_text(encoding="utf-8")):
                for term, rx in regexes:
                    lines = [n for n, s in unit.lines if rx.search(s)]
                    if lines:
                        hit(unit.loc, "literal", f'"{term}" @ {rel}:{lines[0]}')
                        if kw:
                            hot_patterns.append((kw, pattern, pattern_regex(pattern)))
        for f in sorted(endpoint.rglob("*.feature")):
            rel = str(f.relative_to(root))
            for unit in feature_units(rel, f.read_text(encoding="utf-8")):
                for rid in ids:
                    if f"@spec:{rid}" in unit.tags:
                        hit(unit.loc, "tag", f"@spec:{rid} @ {rel}:{unit.lines[0][0]}")
                for term, rx in regexes:
                    lines = [n for n, s in unit.lines if rx.search(s)]
                    if lines:
                        hit(unit.loc, "literal", f'"{term}" @ {rel}:{lines[0]}')
                for n, kw, text in unit.steps:
                    for pkw, pattern, prx in hot_patterns:
                        if pkw == kw and prx.match(text):
                            hit(unit.loc, "usage", f"{kw} `{pattern}` @ {rel}:{n}")
    sys.stdout.write("| 部位 | 信號 | 證據 |\n|---|---|---|\n")
    for loc in sorted(hits):
        signals = ", ".join(dict.fromkeys(s for s, _ in hits[loc]))
        evidence = "<br>".join(e for _, e in hits[loc])
        sys.stdout.write(f"| `{loc}` | {signals} | {evidence} |\n")
    count = {s: sum(1 for v in hits.values() if any(x == s for x, _ in v)) for s in ("tag", "literal", "usage")}
    sys.stdout.write(
        f"ids={','.join(ids) or '-'} terms={len(terms)} candidates={len(hits)} "
        f"tag={count['tag']} literal={count['literal']} usage={count['usage']}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
