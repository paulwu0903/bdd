# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check one endpoint's Gherkin feature files against its dsl.md for mechanical format violations.

Usage:
    uv run scripts/verify_features.py --feature-dir <features/<endpoint>> --dsl <features/<endpoint>/dsl.md>
    uv run scripts/verify_features.py --feature-dir specs/truth/features/<endpoint> --dsl-root specs/truth/features/<endpoint>
        [--only <feature file> ...] [--only-delta <specs/plans/NNN-name/truth-delta.md>]

Scope (--only / --only-delta): per-file checks (V1 tag / title presence and format, V2, V3, V5-V9) are
reported only for the listed feature files; every feature file is still parsed, and cross-file checks
(V1 duplicate title when either occurrence is listed, V4, V10, V11) are judged over the whole endpoint.
--only-delta takes the feature files named in the `## /dsl-refine — truth/features/` section of a
plan's truth-delta.md (paths relative to specs/truth/features/); files that no longer exist (deleted)
are skipped. Without either flag every feature file is checked.

Checks (one line per violation on stdout, exit 1 when any):
  V1 every Example / Scenario Outline has, on the tag lines directly above it, at least one trace tag
     `@ac:<主題>:<Journey 序>-<檢查點序>` or `@spec:<FR-nnn|NFR-nnn>`; every trace tag is well formed (with
     --dsl-root the plan prefix is required: `@ac:<NNN>/<主題>:<J>-<C>`, `@spec:<NNN>/<FR|NFR-nnn>`); trace tags
     sit only above Example / Scenario Outline; every title is non-empty and unique within the endpoint
  V2 every Example has Given, When and Then steps in that order (Background steps count first;
     And / But continue the previous keyword); an atomic Example has exactly one When step; an
     Example tagged `@journey` may interleave When and
     Then, but must start with Given, end with Then, and follow every run of When with Then
  V3 every step matches exactly one DSL pattern of its keyword's table in dsl.md
  V4 every DSL pattern is used at least once
  V5 quoting: string parameters are written in double quotes, integer parameters bare (per the
     type in the Gherkin 參數 cell); Data Table and Examples cells contain no double quotes
  V6 no technical wording in steps, step comments, Data Table cells or Examples cells
  V7 every step comment is `# 名稱=值` and 名稱 is a parameter or default-parameter name in dsl.md
  V8 a Data Table appears exactly on patterns whose Data Table 參數 cell declares columns
     (`• `欄位`：必填／選填；…`); headers use declared names; required columns are present
  V9 layout is Feature > Rule > Example: no plain Scenario, every Example sits under a Rule
  V10 (--dsl-root) a DSL pattern is defined in more than one row across the endpoint's dsl.md files
  V11 (--dsl-root) a `## 附錄` section appears in a dsl.md outside the 平臺共用 module
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


KEYWORDS = ("Given", "When", "Then")
ORDER = {"Given": 0, "When": 1, "Then": 2}
# Technical words that must not reach PM-readable text. ASCII words only need a left boundary,
# so "tokens" is caught while "TARGET" does not trip on "GET".
BANNED_ASCII = ["API", "JSON", "json", "token", "snapshot", "status", "HTTP", "Promise", "fixture",
                "Fixture", "mock", "request", "response", "POST", "GET", "PUT", "PATCH", "DELETE",
                "locator", "click", "world", "World", "undefined", "null"]
BANNED_TEXT = ["/api", "快照", "fill(", "expect("]
# Error-code identifiers such as OUT_OF_STOCK must be written as business reasons.
ERROR_CODE = re.compile(r"(?<![A-Za-z0-9_])[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+(?![A-Za-z0-9_])")
TRACE_TAG = re.compile(r"^@ac:[^\s:@]+:\d+-\d+$|^@spec:(?:\d{3}/)?(?:FR|NFR)-\d+$")
# Truth mode (--dsl-root): every trace tag carries the plan prefix NNN/.
PREFIXED_TAG = re.compile(r"^@ac:\d{3}/[^\s:@/]+:\d+-\d+$|^@spec:\d{3}/(?:FR|NFR)-\d+$")
SHARED_MODULE = "平臺共用"
DELTA_FEATURES = "## /dsl-refine — truth/features/"
JOURNEY_TAG = "@journey"
# Collapsed keyword runs of a journey: Given first, an optional check right after it, then When/Then pairs.
JOURNEY_SHAPE = re.compile(r"^GT?(WT)+$")
STRICT_VALUE = r'"[^"]*"|<[^>]*>|-?\d+(?:\.\d+)?'
LOOSE_VALUE = r".+?"


class Pattern:
    def __init__(self, keyword: str, text: str, params: dict[str, str], table: dict[str, str] | None) -> None:
        self.keyword = keyword
        self.text = text
        self.params = params  # Gherkin 參數 name -> type
        self.table = table  # Data Table column -> 必填/選填, None when not supported
        self.slots = re.findall(r"\{([^}]*)\}", text)
        self.strict = self._compile(STRICT_VALUE)
        self.loose = self._compile(LOOSE_VALUE)

    def _compile(self, value: str) -> re.Pattern:
        parts = re.split(r"\{[^}]*\}", self.text)
        body = f"({value})".join(re.escape(p) for p in parts)
        return re.compile("^" + body + "$")

    def slot_type(self, slot: str) -> str:
        if slot in self.params:
            return self.params[slot]
        base = re.sub(r"\s*\d+$", "", slot)
        return self.params.get(base, "")


def split_row(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [c.strip() for c in re.split(r"(?<!\\)\|", inner)]


def bullets(cell: str) -> dict[str, str]:
    # `• `名稱`：型別；語意` -> {名稱: 型別}
    out = {}
    for name, rest in re.findall(r"• `([^`]+)`：([^<]*)", cell):
        out[name] = re.split(r"[；;]", rest, maxsplit=1)[0].strip()
    return out


def parse_dsl(text: str) -> tuple[dict[str, list[Pattern]], set[str]]:
    tables: dict[str, list[Pattern]] = {k: [] for k in KEYWORDS}
    names: set[str] = set()
    section = None
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("#"):
            m = re.match(r"^## (Given|When|Then) 句型", line)
            section = m.group(1) if m else None
            continue
        if section is None or not line.startswith("|"):
            continue
        cells = split_row(line)
        if len(cells) < 6:
            continue
        m = re.fullmatch(r"`([^`]+)`", cells[0])
        if not m:
            continue
        params = bullets(cells[2])
        cols = re.findall(r"• `([^`]+)`：(必填|選填)", cells[3])
        names.update(params)
        names.update(bullets(cells[4]))
        pattern = Pattern(section, m.group(1), params, dict(cols) if cols else None)
        pattern.line = n
        tables[section].append(pattern)
    return tables, names


def parse_tags(line: str) -> list[str]:
    # Same split as the official Gherkin parser: text after whitespace + "#" is a comment.
    text = re.split(r"\s#", line.strip(), maxsplit=1)[0]
    return ["@" + t.strip() for t in text.split("@") if t.strip()]


def banned_in(text: str) -> list[str]:
    hits = [w for w in BANNED_ASCII if re.search(rf"(?<![A-Za-z]){re.escape(w)}", text)]
    hits += [w for w in BANNED_TEXT if w in text]
    hits += ERROR_CODE.findall(text)
    return hits


class Checker:
    def __init__(self, tables: dict[str, list[Pattern]], names: set[str], prefixed: bool = False,
                 only: set[Path] | None = None) -> None:
        self.tables = tables
        self.names = names
        self.prefixed = prefixed  # truth mode: trace tags must carry NNN/
        self.only = only  # None = every file is in scope for per-file checks
        self.in_scope = True
        self.scoped_files = 0
        self.errors: list[str] = []
        self.used: set[tuple[str, str]] = set()
        self.titles: dict[str, tuple[str, bool]] = {}  # Example title -> (first place seen, that file in scope)
        self.rules = 0
        self.examples = 0

    def err(self, code: str, where: str, msg: str) -> None:
        # Per-file violation: dropped for files outside the --only scope.
        if self.in_scope:
            self.errors.append(f"{code} {where}: {msg}")

    def cross(self, code: str, where: str, msg: str) -> None:
        # Cross-file violation: judged over the whole endpoint regardless of scope.
        self.errors.append(f"{code} {where}: {msg}")

    def check_banned(self, where: str, what: str, text: str) -> None:
        for w in banned_in(text):
            self.err("V6", where, f'{what} contains "{w}"')

    def check_file(self, path: Path, label: str) -> None:
        self.file = label
        self.in_scope = self.only is None or path.resolve() in self.only
        self.scoped_files += 1 if self.in_scope else 0
        self.feature_bg: list[str] = []
        self.rule_bg: list[str] = []
        self.rule_seen = False
        self.kind = None  # "bg_feature" | "bg_rule" | "example" | "outline"
        self.steps: list[str] = []
        self.own_steps = 0
        self.title = None
        self.last = None  # [pattern, where, header]
        self.in_examples = False
        self.pending_tags: list[str] = []
        self.tags: list[str] = []
        for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            self.line(n, raw.strip())
        self.close_block()

    def where(self, n: int) -> str:
        return f"{self.file}:{n}" + (f" ({self.title})" if self.title else "")

    def tag_line(self, n: int, s: str) -> None:
        tags = parse_tags(s)
        for t in tags:
            if not t.startswith(("@ac:", "@spec:")):
                continue
            if not TRACE_TAG.match(t):
                self.err("V1", self.where(n), f'trace tag "{t}" must be @ac:<主題>:<Journey 序>-<檢查點序> or @spec:<FR-nnn|NFR-nnn> with no spaces')
            elif self.prefixed and not PREFIXED_TAG.match(t):
                self.err("V1", self.where(n), f'trace tag "{t}" needs the plan prefix: @ac:<NNN>/<主題>:<J>-<C> or @spec:<NNN>/<FR-nnn|NFR-nnn>')
        self.pending_tags.extend(tags)

    def line(self, n: int, s: str) -> None:
        if not s:
            return
        if not s.startswith("|"):
            self.close_table()
            if not s.startswith("#"):
                self.in_examples = False
        head = re.match(r"^(Feature|Rule|Background|Scenario Outline|Scenario Template|Scenario|Example|Examples|Scenarios):\s*(.*)$", s)
        if head:
            self.header(n, head.group(1), head.group(2))
            return
        if s.startswith("@"):
            self.tag_line(n, s)
            return
        if s.startswith("|"):
            self.row(n, split_row(s))
            return
        if s.startswith("#"):
            if self.kind is not None:
                self.comment(n, s)
            return
        m = re.match(r"^(Given|When|Then|And|But) (.*)$", s)
        if m:
            self.step(n, m.group(1), m.group(2))

    def header(self, n: int, word: str, title: str) -> None:
        tags, self.pending_tags = self.pending_tags, []
        if word in ("Examples", "Scenarios"):
            self.in_examples = True
            return
        self.close_block()
        if word in ("Feature", "Rule", "Background"):
            for t in tags:
                if t.startswith(("@ac:", "@spec:")) or t == JOURNEY_TAG:
                    self.err("V1", f"{self.file}:{n}", f'{t} must sit directly above an Example or Scenario Outline, not above {word}')
        if word == "Feature":
            self.feature_bg, self.rule_bg, self.rule_seen = [], [], False
            return
        if word == "Rule":
            self.rule_seen, self.rule_bg = True, []
            self.rules += 1
            return
        if word == "Background":
            self.kind = "bg_rule" if self.rule_seen else "bg_feature"
            self.steps, self.own_steps = [], 0
            return
        self.examples += 1
        self.kind = "outline" if word in ("Scenario Outline", "Scenario Template") else "example"
        self.steps, self.own_steps = list(self.feature_bg + self.rule_bg), 0
        self.tags = tags
        self.title = title.strip() or None
        if word == "Scenario":
            self.err("V9", self.where(n), "use Rule > Example, not Scenario")
        if not self.rule_seen:
            self.err("V9", self.where(n), f"{word} is not under a Rule")
        if not title.strip():
            self.err("V1", f"{self.file}:{n}", f"{word} has no title")
        elif title.strip() in self.titles:
            first, first_in_scope = self.titles[title.strip()]
            if self.in_scope or first_in_scope:
                self.cross("V1", self.where(n), f"title is already used at {first}")
        else:
            self.titles[title.strip()] = (f"{self.file}:{n}", self.in_scope)
        if not any(TRACE_TAG.match(t) for t in tags):
            self.err("V1", self.where(n), f"{word} needs at least one trace tag (@ac:<主題>:<Journey 序>-<檢查點序> or @spec:<FR-nnn|NFR-nnn>) directly above it")

    def close_block(self) -> None:
        self.close_table()
        self.in_examples = False
        if self.kind == "bg_feature":
            self.feature_bg = list(self.steps)
        elif self.kind == "bg_rule":
            self.rule_bg = list(self.steps)
        elif self.kind in ("example", "outline"):
            where = f"{self.file} ({self.title})"
            if not self.own_steps:
                self.err("V2", where, "Example has no steps")
            for need in KEYWORDS:
                if need not in self.steps:
                    self.err("V2", where, f"missing {need}")
            if JOURNEY_TAG in self.tags:
                runs = "".join(k[0] for i, k in enumerate(self.steps) if i == 0 or self.steps[i - 1] != k)
                if not JOURNEY_SHAPE.match(runs):
                    self.err("V2", where, "journey must start with Given, end with Then, and follow every run of When with Then")
            else:
                ranks = [ORDER[k] for k in self.steps]
                if ranks != sorted(ranks):
                    self.err("V2", where, "Given/When/Then out of order; tag the Example @journey if it is an endpoint journey")
                if self.steps.count("When") > 1:
                    self.err("V2", where, f"an atomic Example has exactly one When step, found {self.steps.count('When')}; move setup into Given or split the Example")
        self.kind, self.title, self.steps, self.tags = None, None, [], []

    def step(self, n: int, kw: str, text: str) -> None:
        where = self.where(n)
        if self.kind is None:
            self.err("V2", where, f'step "{text}" is outside any Background or Example')
            return
        if kw in ("And", "But"):
            if not self.steps:
                self.err("V2", where, f"{kw} without a preceding Given/When/Then")
                return
            kw = self.steps[-1]
        self.steps.append(kw)
        self.own_steps += 1
        self.check_banned(where, "step", text)
        hits = [(p, p.strict.match(text)) for p in self.tables[kw]]
        hits = [(p, m) for p, m in hits if m]
        if len(hits) == 1:
            pattern, m = hits[0]
            self.used.add((kw, pattern.text))
            self.check_quotes(where, pattern, m)
            self.last = [pattern, where, None]
            return
        loose = [p for p in self.tables[kw] if p.loose.match(text)]
        if not hits and len(loose) == 1:
            self.used.add((kw, loose[0].text))
            self.err("V5", where, f'"{text}" matches "{loose[0].text}" only if parameters are re-quoted; quote strings, leave integers bare')
            self.last = [loose[0], where, None]
            return
        self.err("V3", where, f'"{text}" matches {len(hits)} {kw} patterns')
        self.last = None

    def check_quotes(self, where: str, pattern: Pattern, m: re.Match) -> None:
        for slot, value in zip(pattern.slots, m.groups()):
            kind = pattern.slot_type(slot)
            quoted = value.startswith('"')
            if kind.startswith("整數") and quoted:
                self.err("V5", where, f"integer parameter {{{slot}}} must not be quoted: {value}")
            elif kind.startswith("字串") and not quoted:
                self.err("V5", where, f"string parameter {{{slot}}} must be in double quotes: {value}")

    def row(self, n: int, cells: list[str]) -> None:
        where = self.where(n)
        what = "Examples cell" if self.in_examples else "table cell"
        for c in cells:
            if '"' in c:
                self.err("V5", where, f"{what} must not contain double quotes: {c}")
            self.check_banned(where, what, c)
        if self.in_examples:
            return
        if self.last is None:
            return
        if self.last[2] is None:
            self.last[2] = cells

    def close_table(self) -> None:
        if self.last is None:
            return
        pattern, where, header = self.last
        self.last = None
        if pattern.table is None:
            if header is not None:
                self.err("V8", where, f'data table given but pattern "{pattern.text}" does not support one')
            return
        if header is None:
            self.err("V8", where, f'pattern "{pattern.text}" requires a data table')
            return
        for h in header:
            if h not in pattern.table:
                self.err("V8", where, f'table column "{h}" is not declared in dsl.md')
        for col, need in pattern.table.items():
            if need == "必填" and col not in header:
                self.err("V8", where, f'required table column "{col}" is missing')

    def comment(self, n: int, s: str) -> None:
        where = self.where(n)
        m = re.match(r"^# ?([^=]+)=", s)
        if not m:
            self.err("V7", where, 'step comment is not "# 名稱=值"')
        elif m.group(1).strip() not in self.names:
            self.err("V7", where, f'comment name "{m.group(1).strip()}" is not a parameter or default-parameter name in dsl.md')
        self.check_banned(where, "step comment", s)


def delta_features(delta: Path, root: Path) -> list[Path]:
    # Feature files named in the features section of a truth-delta.md, resolved under root.
    files: list[Path] = []
    in_section = False
    for line in delta.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = line.strip() == DELTA_FEATURES
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = split_row(line)
        m = re.fullmatch(r"`([^`]+)`", cells[1]) if len(cells) > 1 else None
        if not m:
            continue
        rel = m.group(1).split(" › ", 1)[0].strip()
        if rel.endswith(".feature") and (root / rel) not in files:
            files.append(root / rel)
    return files


def duplicate_patterns(dsls: list[Path], root: Path) -> list[str]:
    # V10: the same keyword + pattern text defined in more than one dsl.md row.
    seen: dict[tuple[str, str], list[str]] = {}
    for d in dsls:
        tables, _ = parse_dsl(d.read_text(encoding="utf-8"))
        for kw, rows in tables.items():
            for p in rows:
                seen.setdefault((kw, p.text), []).append(f"{d.relative_to(root)}:{p.line}")
    return [f"V10 {kw} pattern defined {len(at)} times: {text} ({', '.join(at)})"
            for (kw, text), at in seen.items() if len(at) > 1]


def misplaced_appendix(dsls: list[Path], root: Path) -> list[str]:
    # V11: the shared-rules appendix belongs only to the 平臺共用 module.
    out = []
    for d in dsls:
        if d.parent.name == SHARED_MODULE:
            continue
        for n, line in enumerate(d.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("## 附錄"):
                out.append(f"V11 {d.relative_to(root)}:{n}: appendix belongs only in {SHARED_MODULE}/dsl.md; refer to it from the header instead")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Check one endpoint's Gherkin feature files against its dsl.md for mechanical format violations.")
    parser.add_argument("--feature-dir", required=True, help="Directory holding this endpoint's *.feature files")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dsl", help="Path to this endpoint's single dsl.md")
    source.add_argument("--dsl-root", help="Endpoint directory whose <module>/dsl.md files are merged (specs/truth/features/<endpoint>)")
    parser.add_argument("--only", nargs="+", metavar="FEATURE", help="Report per-file violations only for these feature files; cross-file checks still cover the whole endpoint")
    parser.add_argument("--only-delta", metavar="TRUTH_DELTA", help="Like --only, taking the feature files listed in the features section of this truth-delta.md")
    args = parser.parse_args()
    fdir = Path(args.feature_dir)
    dsls = [Path(args.dsl)] if args.dsl else sorted(Path(args.dsl_root).rglob("dsl.md"))
    if not dsls or not all(d.is_file() for d in dsls):
        sys.stderr.write("error: no dsl.md found; pass --dsl <dsl.md> or --dsl-root <endpoint directory holding <module>/dsl.md>\n")
        return 2
    # With --dsl-root the feature files of every module folder are checked; with --dsl only the directory itself.
    features = (sorted(fdir.rglob("*.feature")) if args.dsl_root else sorted(fdir.glob("*.feature"))) if fdir.is_dir() else []
    if not features:
        sys.stderr.write(f"error: no *.feature files in '{fdir}'; pass --feature-dir <directory holding the feature files>\n")
        return 2
    only: set[Path] | None = None
    if args.only or args.only_delta:
        only = set()
        all_resolved = {f.resolve() for f in features}
        for name in args.only or []:
            path = Path(name).resolve()
            if path not in all_resolved:
                sys.stderr.write(f"error: --only file '{name}' is not a *.feature under '{fdir}'; pass feature files of this endpoint\n")
                return 2
            only.add(path)
        if args.only_delta:
            delta = Path(args.only_delta)
            if not delta.is_file():
                sys.stderr.write(f"error: '{delta}' is not a file; pass --only-delta <specs/plans/NNN-name/truth-delta.md>\n")
                return 2
            # Delta paths are <endpoint>/<module>/<file>.feature relative to specs/truth/features/.
            truth_features = fdir.resolve().parent
            only |= {f.resolve() for f in delta_features(delta, truth_features) if f.resolve() in all_resolved}
    base = fdir.resolve().parent if args.dsl_root else fdir.resolve()
    tables, names = {}, set()
    for d in dsls:
        t, n = parse_dsl(d.read_text(encoding="utf-8"))
        for kw, rows in t.items():
            tables.setdefault(kw, []).extend(rows)
        names |= n
    checker = Checker(tables, names, prefixed=bool(args.dsl_root), only=only)
    for f in features:
        label = str(f.resolve().relative_to(base)) if args.dsl_root else f.name
        checker.check_file(f, label)
    errors = checker.errors
    for kw, rows in tables.items():
        for text in dict.fromkeys(p.text for p in rows):
            if (kw, text) not in checker.used:
                errors.append(f"V4 {kw} pattern never used: {text}")
    if args.dsl_root:
        root = Path(args.dsl_root).resolve().parent
        resolved = [d.resolve() for d in dsls]
        errors += duplicate_patterns(resolved, root) + misplaced_appendix(resolved, root)
    for e in errors:
        sys.stdout.write(e + "\n")
    counts = "/".join(f"{k}:{len(v)}" for k, v in tables.items())
    scope = f"checked={checker.scoped_files} " if only is not None else ""
    sys.stdout.write(
        f"features={len(features)} {scope}patterns={counts} "
        f"rules={checker.rules} examples={checker.examples} violations={len(errors)}\n"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
