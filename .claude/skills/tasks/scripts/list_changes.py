# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""List a plan's truth-delta rows with the static impact /tasks needs to cut phases and task paths, as JSON.

For every row of the five truth-delta sections it reports action, location, summary and reason. Rows of the
features section are resolved further:
- feature rows (`<ep>/<module>/<file>.feature[ › Rule: … › Example: …]`): the feature file under
  specs/truth/features, the Examples in scope with their line numbers and tags, and a suggested attribution
  (User Story, 既有需求異動 #n or 全域 NFR) from the `@spec` ids; DELETE rows are read from the Base commit;
- dsl rows (`<ep>/<module>/dsl.md › <Given|When|Then> › <sentence>`): the Examples of
  specs/truth/features/<ep>/**/*.feature whose steps (Background included) use the sentence; for MODIFY and
  DELETE rows also the step files under <ep>/tests/bdd/modules/ registering it (dsl `{name}` converted to
  cucumber `{int}` / `{string}` by the Gherkin 參數 column; DELETE sentences take that column from the Base
  commit) and the relative imports of those step files (helpers and fixtures).
Contracts DELETE `operationId` rows list the files of backend/src and frontend/src that contain the operation
path (taken from the Base openapi, prefixed with its servers[0] path) or the operationId.
It also lists spec.md's User Stories with priority, the section each requirement id is written in, and the
entries of `## 既有需求異動`.

Exit 1 when a step of an affected Example matches no dsl.md pattern of its endpoint, or a features row cannot
be resolved (upstream gap: hand back to /dsl-refine or the truth-delta check); exit 2 on unusable input.

Usage:
    uv run scripts/list_changes.py --plan <specs/plans/NNN-name>
"""
import argparse
import json
import re
import subprocess
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

# Section key -> heading of its table in truth-delta.md (same as the truth-delta skill's template).
SECTIONS = {
    "requirements": "## /specify — truth/requirements.md",
    "techstack": "## /technical-research — truth/techstack.md",
    "contracts": "## /api-plan — truth/contracts/",
    "data": "## /data-plan — truth/data/",
    "features": "## /dsl-refine — truth/features/",
}
TRUTH_FEATURES = "specs/truth/features"
TRUTH_OPENAPI = "specs/truth/contracts/openapi.yaml"
PRODUCT_DIRS = ("backend/src", "frontend/src")
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
KEYWORDS = ("Given", "When", "Then")
STRICT_VALUE = r'"[^"]*"|<[^>]*>|-?\d+(?:\.\d+)?'
LOOSE_VALUE = r".+?"
HEADER_KW = re.compile(r"^(Feature|Rule|Background|Examples|Scenarios|Scenario Outline|Scenario Template|Example|Scenario):\s*(.*)$")
STEP_KW = re.compile(r"^(Given|When|Then|And|But|\*)\s+(.*)$")
EXAMPLE_WORDS = ("Example", "Scenario", "Scenario Outline", "Scenario Template")
STORY_HEAD = re.compile(r"^### User Story (\d+) - (.+?)\s*\(Priority: (P\d+)\)\s*$")
REQ_ID = re.compile(r"\*\*((?:\d{3}/)?(?:N?FR|SC)-\d+)\*\*")
SPEC_TAG = re.compile(r"^@spec:(?:(\d{3})/)?((?:N?FR|SC)-\d+)$")
REGISTRATION = re.compile(r"\b(Given|When|Then|given|when|then)\(\s*(['\"`])((?:\\.|(?!\2)[^\\])*)\2")
IMPORT = re.compile(
    r"(?:^|\n)\s*(?:import|export)\s[^;]*?from\s+(['\"])([^'\"]+)\1|(?:^|\n)\s*import\s+(['\"])([^'\"]+)\3"
    r"|\bimport\(\s*(['\"])([^'\"]+)\5\s*\)"
)


# ---------------------------------------------------------------------------
# git access (Base contents)

class Git:
    def __init__(self, root: Path, base: str | None):
        self.root, self.base, self.ok = root, base, False
        if base and self._run("rev-parse", "--show-toplevel").returncode == 0:
            self.ok = self._run("cat-file", "-e", f"{base}^{{commit}}").returncode == 0

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        except FileNotFoundError:
            return subprocess.CompletedProcess(args, 127, "", "git not found")

    def show(self, rel: str) -> str | None:
        if not self.ok:
            return None
        shown = self._run("show", f"{self.base}:{rel}")
        return shown.stdout if shown.returncode == 0 else None

    def files(self, rel: str) -> list[str]:
        if not self.ok:
            return []
        listed = self._run("ls-tree", "-r", "-z", "--name-only", self.base, "--", rel)
        return [n for n in listed.stdout.split("\0") if n]


# ---------------------------------------------------------------------------
# truth-delta.md

def header_value(text: str, name: str) -> str | None:
    m = re.search(rf"^\*\*{name}\*\*: `?([^`\n]+?)`?[ \t]*$", text, re.M)
    return m.group(1).strip() if m else None


def split_cells(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [c.strip() for c in re.split(r"(?<!\\)\|", inner)]


def normalize(location: str) -> str:
    return " ".join(location.replace("`", "").split())


def section_rows(text: str, heading: str) -> list[dict]:
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return []
    rows = []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.startswith("## "):
            break
        if not line.startswith("|") or re.match(r"^\|\s*(-|動作\s*\|)", line):
            continue
        cells = split_cells(line)
        if len(cells) != 4 or cells[0] not in ("ADD", "MODIFY", "DELETE"):
            continue
        rows.append({"line": i + 1, "action": cells[0], "location": normalize(cells[1]), "summary": cells[2], "reason": cells[3]})
    return rows


# ---------------------------------------------------------------------------
# Feature files

def parse_tags(line: str) -> list[str]:
    # Same split as the official Gherkin parser: text after whitespace + "#" is a comment.
    text = re.split(r"\s#", line.strip(), maxsplit=1)[0]
    return ["@" + t.strip() for t in text.split("@") if t.strip()]


def parse_feature(rel: str, text: str) -> dict:
    """Examples with line, tags and steps (own and Background), keyed like the truth-delta skill's semantic units."""
    feature_tags: list[str] = []
    pending: list[str] = []
    rule = None
    rule_tags: dict[str, list[str]] = {}
    rules: dict[str, int] = {}
    backgrounds: dict[str | None, list[tuple[int, str, str]]] = {None: []}
    examples: list[dict] = []
    used_keys: set[str] = {f"{rel} › Feature"}
    target: list | None = None
    prev_kw = None
    in_doc = False

    def unique(key: str) -> str:
        n, out = 2, key
        while out in used_keys:
            out, n = f"{key} #{n}", n + 1
        used_keys.add(out)
        return out

    for n, raw in enumerate(text.split("\n"), start=1):
        s = raw.strip()
        if s.startswith('"""') or s.startswith("```"):
            in_doc = not in_doc
            continue
        if in_doc or not s or s.startswith("#") or s.startswith("|"):
            continue
        if s.startswith("@"):
            pending += parse_tags(s)
            continue
        head = HEADER_KW.match(s)
        if head:
            word, title = head.group(1), head.group(2).strip()
            prev_kw = None
            if word == "Feature":
                feature_tags, target = pending, None
            elif word == "Rule":
                rule = title
                rules[rule] = n
                rule_tags[rule] = pending
                unique(f"{rel} › Rule: {rule}")
                backgrounds.setdefault(rule, [])
                target = None
            elif word == "Background":
                target = backgrounds.setdefault(rule, [])
            elif word in EXAMPLE_WORDS:
                label = f"{word}: {title}"
                key = unique(f"{rel} › Rule: {rule} › {label}" if rule else f"{rel} › {label}")
                example = {"key": key, "title": title, "keyword": word, "rule": rule, "line": n,
                           "tags": pending, "inherited_tags": feature_tags + (rule_tags.get(rule, []) if rule else []),
                           "steps": []}
                examples.append(example)
                target = example["steps"]
            pending = []
            continue
        step = STEP_KW.match(s)
        if step and target is not None:
            kw = step.group(1)
            if kw in ("And", "But", "*"):
                kw = prev_kw or "Given"
            prev_kw = kw
            target.append((n, kw, step.group(2).strip()))
    for example in examples:
        bg = backgrounds.get(None, []) + (backgrounds.get(example["rule"], []) if example["rule"] else [])
        example["background_steps"] = bg
    return {"examples": examples, "rules": rules, "feature_tags": feature_tags}


def example_brief(example: dict, feature: str) -> dict:
    return {"feature": feature, "line": example["line"], "title": example["title"], "keyword": example["keyword"],
            "rule": example["rule"], "tags": example["tags"], "inherited_tags": example["inherited_tags"]}


# ---------------------------------------------------------------------------
# dsl.md

class Pattern:
    def __init__(self, keyword: str, text: str, integers: set[str], dsl: str) -> None:
        self.keyword, self.text, self.integers, self.dsl = keyword, text, integers, dsl
        parts = re.split(r"\{[^}]*\}", text)
        self.strict = re.compile("^" + f"(?:{STRICT_VALUE})".join(re.escape(p) for p in parts) + "$")
        self.loose = re.compile("^" + f"(?:{LOOSE_VALUE})".join(re.escape(p) for p in parts) + "$")

    def matches(self, step_text: str) -> bool:
        return bool(self.strict.match(step_text) or self.loose.match(step_text))

    def expression(self) -> str:
        # Same conversion as <ep>/tests/bdd/check-structure.ts: 整數 -> {int}, otherwise {string}.
        return re.sub(r"\{([^}]+)\}", lambda m: "{int}" if m.group(1) in self.integers else "{string}", self.text)


def integer_params(cell: str) -> set[str]:
    names: set[str] = set()
    for item in cell.split("<br>"):
        m = re.match(r"^•\s*(.+?)：(整數|字串)", item.strip())
        if m and m.group(2) == "整數":
            names.update(re.findall(r"`([^`]+)`", m.group(1)))
    return names


def parse_dsl(text: str, dsl: str) -> list[Pattern]:
    patterns: list[Pattern] = []
    keyword = None
    for line in text.split("\n"):
        heading = re.match(r"^## (Given|When|Then) 句型", line)
        if heading:
            keyword = heading.group(1)
            continue
        if line.startswith("## "):
            keyword = None
        row = re.match(r"^\| `([^`]+)` \|", line)
        if keyword and row:
            cells = split_cells(line)
            patterns.append(Pattern(keyword, row.group(1), integer_params(cells[2] if len(cells) > 2 else ""), dsl))
    return patterns


def loose_expression(expression: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", expression)


# ---------------------------------------------------------------------------
# Step files

def unescape(literal: str) -> str:
    return re.sub(r"\\(.)", r"\1", literal)


def registrations(root: Path, endpoint: str) -> list[dict]:
    found = []
    modules = root / endpoint / "tests" / "bdd" / "modules"
    if not modules.is_dir():
        return found
    for path in sorted(modules.rglob("*.ts")):
        text = path.read_text(encoding="utf-8")
        for m in REGISTRATION.finditer(text):
            found.append({"file": path.relative_to(root).as_posix(), "line": text.count("\n", 0, m.start(3)) + 1,
                          "keyword": m.group(1), "expression": unescape(m.group(3))})
    return found


def resolve_import(source: Path, spec: str) -> Path | None:
    base = (source.parent / spec).resolve()
    candidates = [base]
    if base.suffix in (".js", ".mjs", ".cjs"):
        candidates.append(base.with_suffix(".ts"))
    candidates += [base.with_name(base.name + s) for s in (".ts", ".tsx", ".js")]
    candidates += [base / "index.ts", base / "index.tsx"]
    return next((c for c in candidates if c.is_file()), None)


def relative_imports(root: Path, rel: str) -> list[dict]:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    out = []
    for m in IMPORT.finditer(text):
        spec = m.group(2) or m.group(4) or m.group(6)
        if not spec or not spec.startswith("."):
            continue
        target = resolve_import(path, spec)
        resolved = None
        if target is not None:
            try:
                resolved = target.relative_to(root.resolve()).as_posix()
            except ValueError:
                resolved = target.as_posix()
        out.append({"import": spec, "file": resolved})
    return out


# ---------------------------------------------------------------------------
# spec.md

def parse_spec(text: str, prefix: str) -> tuple[list[dict], dict[str, str], list[dict]]:
    stories: list[dict] = []
    where: dict[str, str] = {}
    changes: list[dict] = []
    current = None
    in_changes = False
    change_header: list[str] | None = None
    for line in text.split("\n"):
        m = STORY_HEAD.match(line)
        if m:
            stories.append({"number": int(m.group(1)), "title": m.group(2).strip(), "priority": m.group(3)})
            current, in_changes = f"User Story {m.group(1)}", False
            continue
        if line.startswith("## "):
            in_changes = line[3:].strip().startswith("既有需求異動")
            change_header = None
            current = "全域 NFR" if ("Global Requirements" in line or "System Constraints" in line) else None
            continue
        if line.startswith("### ") and current and current.startswith("User Story"):
            current = None
        if in_changes:
            s = line.strip()
            if s.startswith("|"):
                cells = split_cells(s)
                if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    continue
                num = re.match(r"^#?\s*(\d+)$", cells[0].replace("`", "").replace("*", "")) if cells else None
                if num and change_header:
                    changes.append({"number": int(num.group(1)), "fields": dict(zip(change_header, cells)), "text": s})
                elif not num:
                    change_header = cells
                continue
            num = re.match(r"^(?:[-*]\s+)?\**#(\d+)\**", s)
            if num:
                changes.append({"number": int(num.group(1)), "text": s})
            continue
        for rid in REQ_ID.findall(line):
            full = rid if "/" in rid else f"{prefix}/{rid}"
            if current and full not in where:
                where[full] = current
    return stories, where, changes


def suggest_attribution(spec_ids: list[str], prefix: str, where: dict[str, str], priority: dict[int, int],
                        changes: list[dict]) -> str | None:
    stories = sorted({int(where[r].split()[-1]) for r in spec_ids if where.get(r, "").startswith("User Story")})
    if stories:
        best = min(stories, key=lambda n: (priority.get(n, 99), n))
        return f"US{best}"
    for rid in spec_ids:
        if not rid.startswith(prefix + "/"):
            for change in changes:
                if rid in change["text"] or rid.split("/", 1)[1] in change["text"]:
                    return f"既有需求異動 #{change['number']}"
    if any(where.get(r) == "全域 NFR" for r in spec_ids):
        return "全域 NFR"
    return None


def spec_ids_of(examples: list[dict]) -> list[str]:
    ids = []
    for example in examples:
        for tag in example["tags"] + example["inherited_tags"]:
            m = SPEC_TAG.match(tag)
            if m:
                full = f"{m.group(1)}/{m.group(2)}" if m.group(1) else m.group(2)
                if full not in ids:
                    ids.append(full)
    return ids


# ---------------------------------------------------------------------------
# Resolution

class Context:
    def __init__(self, root: Path, git: Git, prefix: str):
        self.root, self.git, self.prefix = root, git, prefix
        self.problems: list[str] = []
        self.warnings: list[str] = []
        self._features: dict[str, dict] = {}
        self._patterns: dict[str, list[Pattern]] = {}
        self._regs: dict[str, list[dict]] = {}
        self.checked: set[tuple[str, int]] = set()

    def feature_files(self, endpoint: str) -> list[str]:
        d = self.root / TRUTH_FEATURES / endpoint
        return [p.relative_to(self.root).as_posix() for p in sorted(d.rglob("*.feature"))] if d.is_dir() else []

    def feature(self, rel: str) -> dict | None:
        if rel not in self._features:
            path = self.root / rel
            short = rel[len(TRUTH_FEATURES) + 1:]
            self._features[rel] = parse_feature(short, path.read_text(encoding="utf-8")) if path.is_file() else None
        return self._features[rel]

    def patterns(self, endpoint: str) -> list[Pattern]:
        if endpoint not in self._patterns:
            d = self.root / TRUTH_FEATURES / endpoint
            found = []
            for dsl in sorted(d.rglob("dsl.md")) if d.is_dir() else []:
                found += parse_dsl(dsl.read_text(encoding="utf-8"), dsl.relative_to(self.root).as_posix())
            self._patterns[endpoint] = found
        return self._patterns[endpoint]

    def regs(self, endpoint: str) -> list[dict]:
        if endpoint not in self._regs:
            self._regs[endpoint] = registrations(self.root, endpoint)
        return self._regs[endpoint]

    def check_steps(self, endpoint: str, feature: str, example: dict) -> None:
        # Every step of an affected Example (Background included) must match a dsl.md pattern of its endpoint.
        patterns = self.patterns(endpoint)
        for line, kw, text in example["background_steps"] + example["steps"]:
            if (feature, line) in self.checked:
                continue
            self.checked.add((feature, line))
            if not any(p.keyword == kw and p.matches(text) for p in patterns):
                self.problems.append(f"{feature}:{line} step '{kw} {text}' matches no {kw} pattern of "
                                     f"{TRUTH_FEATURES}/{endpoint}/**/dsl.md; hand back to /dsl-refine")


def resolve_feature_row(ctx: Context, row: dict, where: dict[str, str], priority: dict[int, int], changes: list[dict]) -> None:
    parts = row["location"].split(" › ")
    rel_short, rest = parts[0], " › ".join(parts[1:])
    endpoint = rel_short.split("/", 1)[0]
    feature = f"{TRUTH_FEATURES}/{rel_short}"
    row.update({"kind": "feature", "endpoint": endpoint, "feature": feature})
    if row["action"] == "DELETE":
        text = ctx.git.show(feature)
        if text is None:
            ctx.warnings.append(f"{row['location']}: Base content unavailable (no git or Base commit); Example lines unknown")
            row.update({"source": None, "scope": "file" if not rest else "part", "examples": []})
            return
        parsed, source = parse_feature(rel_short, text), "base"
    else:
        parsed, source = ctx.feature(feature), "work"
        if parsed is None:
            ctx.problems.append(f"truth-delta line {row['line']}: {feature} does not exist; run the truth-delta check")
            return
    examples = parsed["examples"]
    if not rest:
        scope, chosen = "file", examples
    elif rest == "Feature":
        scope, chosen = "feature-header", examples
    elif rest.startswith("Rule: ") and rest[6:] in parsed["rules"] and " › " not in rest:
        scope, chosen = "rule", [e for e in examples if e["rule"] == rest[6:]]
        row["rule_line"] = parsed["rules"][rest[6:]]
    else:
        key = f"{rel_short} › {rest}"
        chosen = [e for e in examples if e["key"] == key]
        scope = "example"
        if not chosen:
            ctx.problems.append(f"truth-delta line {row['line']}: `{row['location']}` names no Example of {feature} "
                                f"({'Base' if source == 'base' else 'working tree'}); fix the location or run the truth-delta check")
            row.update({"source": source, "scope": scope, "examples": []})
            return
        row["line_no"] = chosen[0]["line"]
    row.update({"source": source, "scope": scope, "examples": [example_brief(e, feature) for e in chosen]})
    if row["action"] != "DELETE":
        for example in chosen:
            ctx.check_steps(endpoint, feature, example)
    if row["action"] == "ADD":
        ids = spec_ids_of(chosen)
        row["spec_ids"] = ids
        row["suggested_attribution"] = suggest_attribution(ids, ctx.prefix, where, priority, changes)
        row["needs_judgement"] = row["suggested_attribution"] is None or any(
            t.startswith("@ac:") for e in chosen for t in e["tags"] + e["inherited_tags"])


def examples_using(ctx: Context, endpoint: str, pattern: Pattern, texts: dict[str, str] | None = None) -> list[dict]:
    # Examples (of the working tree, or of the given {feature: text}) whose own or Background steps match the pattern.
    used = []
    files = texts if texts is not None else {f: None for f in ctx.feature_files(endpoint)}
    for feature, text in files.items():
        parsed = parse_feature(feature[len(TRUTH_FEATURES) + 1:], text) if text is not None else ctx.feature(feature)
        for example in parsed["examples"] if parsed else []:
            hits = [(line, "background" if (line, kw, t) in example["background_steps"] else "step")
                    for line, kw, t in example["background_steps"] + example["steps"]
                    if kw == pattern.keyword and pattern.matches(t)]
            if hits:
                used.append({**example_brief(example, feature), "step_lines": [h[0] for h in hits],
                             "via": sorted({h[1] for h in hits})})
    return used


def resolve_dsl_row(ctx: Context, row: dict) -> None:
    parts = row["location"].split(" › ", 2)
    dsl_short = parts[0]
    endpoint = dsl_short.split("/", 1)[0]
    dsl = f"{TRUTH_FEATURES}/{dsl_short}"
    row.update({"kind": "dsl", "endpoint": endpoint, "dsl": dsl})
    if len(parts) < 3 or parts[1] not in KEYWORDS:
        row["kind"] = "dsl-doc"  # 說明 or 附錄 of a dsl.md: no sentence to trace
        return
    keyword, sentence = parts[1], parts[2]
    row.update({"keyword": keyword, "sentence": sentence})
    current = next((p for p in ctx.patterns(endpoint) if p.keyword == keyword and p.text == sentence), None)
    base = None
    if row["action"] in ("MODIFY", "DELETE"):
        base_text = ctx.git.show(dsl)
        if base_text is None:
            for name in ctx.git.files(f"{TRUTH_FEATURES}/{endpoint}"):
                if name.endswith("/dsl.md"):
                    hit = next((p for p in parse_dsl(ctx.git.show(name) or "", name) if p.keyword == keyword and p.text == sentence), None)
                    if hit:
                        base = hit
                        break
        else:
            base = next((p for p in parse_dsl(base_text, dsl) if p.keyword == keyword and p.text == sentence), None)
    if row["action"] != "DELETE" and current is None:
        ctx.problems.append(f"truth-delta line {row['line']}: `{row['location']}` is not a {keyword} sentence of {dsl}; "
                            "hand back to /dsl-refine or run the truth-delta check")
        return
    pattern = current if row["action"] != "DELETE" else base
    if pattern is None:
        ctx.warnings.append(f"{row['location']}: Base content unavailable; Gherkin 參數 types unknown, matching registrations loosely")
        pattern = Pattern(keyword, sentence, set(), dsl)
    row["expression"] = pattern.expression()
    row["examples_using"] = examples_using(ctx, endpoint, pattern)
    if row["action"] == "DELETE":
        # A current step still matching the deleted sentence must match another sentence, or the dsl has a gap.
        for example in row["examples_using"]:
            for line in example["step_lines"]:
                ctx.checked.discard((example["feature"], line))
        for feature in {e["feature"] for e in row["examples_using"]}:
            parsed = ctx.feature(feature)
            for example in parsed["examples"] if parsed else []:
                if any(e["feature"] == feature and e["line"] == example["line"] for e in row["examples_using"]):
                    ctx.check_steps(endpoint, feature, example)
        if ctx.git.ok:
            texts = {name: ctx.git.show(name) or "" for name in ctx.git.files(f"{TRUTH_FEATURES}/{endpoint}") if name.endswith(".feature")}
            row["base_examples_using"] = examples_using(ctx, endpoint, pattern, texts)
    else:
        for example in row["examples_using"]:
            parsed = ctx.feature(example["feature"])
            full = next(e for e in parsed["examples"] if e["line"] == example["line"])
            ctx.check_steps(endpoint, example["feature"], full)
    if row["action"] == "ADD":
        return
    expressions = {pattern.expression()}
    if base is not None:
        expressions.add(base.expression())
    regs = []
    for reg in ctx.regs(endpoint):
        if reg["expression"] in expressions:
            regs.append({**reg, "match": "exact"})
        elif loose_expression(reg["expression"]) == loose_expression(pattern.expression()):
            regs.append({**reg, "match": "parameter types differ"})
    row["registrations"] = regs
    files = sorted({r["file"] for r in regs})
    row["step_files"] = files
    row["imports"] = {f: relative_imports(ctx.root, f) for f in files}
    if not regs:
        ctx.warnings.append(f"{row['location']}: no step file under {endpoint}/tests/bdd/modules registers `{pattern.expression()}`")


def openapi_operations(text: str) -> tuple[str, dict[str, tuple[str, str]]]:
    doc = yaml.safe_load(text) or {}
    servers = doc.get("servers") or []
    url = servers[0].get("url", "") if servers and isinstance(servers[0], dict) else ""
    prefix = re.sub(r"^[a-z]+://[^/]+", "", url).rstrip("/")
    ops = {}
    for path, item in (doc.get("paths") or {}).items():
        for method, op in (item or {}).items():
            if isinstance(op, dict) and op.get("operationId"):
                ops[op["operationId"]] = (method.upper(), path)
    return prefix, ops


def path_regex(prefix: str, path: str) -> re.Pattern:
    segments = []
    for seg in path.strip("/").split("/"):
        segments.append(r"[^/'\"`\s?]+" if re.fullmatch(r"\{[^}]+\}", seg) else re.escape(seg))
    body = "/" + "/".join(segments)
    return re.compile(rf"(?<![\w/.-])(?:{re.escape(prefix)})?{body}(?![\w/-])" if prefix else rf"(?<![\w/.-]){body}(?![\w/-])")


def resolve_contract_row(ctx: Context, row: dict) -> None:
    m = re.match(r"^\S+\.(?:ya?ml|json) › operationId (\S+)$", row["location"])
    if row["action"] != "DELETE" or not m:
        return
    op_id = m.group(1)
    base_text = ctx.git.show(TRUTH_OPENAPI)
    method = path = None
    prefix = ""
    if base_text is None:
        ctx.warnings.append(f"{row['location']}: Base openapi unavailable; searching the operationId only")
    else:
        try:
            prefix, ops = openapi_operations(base_text)
        except yaml.YAMLError as exc:
            ctx.warnings.append(f"Base {TRUTH_OPENAPI} is not valid YAML ({exc}); searching the operationId only")
            ops = {}
        if op_id in ops:
            method, path = ops[op_id]
        else:
            ctx.warnings.append(f"{row['location']}: operationId not found in the Base openapi; searching the operationId only")
    row.update({"kind": "operation", "operation_id": op_id, "method": method, "path": path,
                "full_path": (prefix + path) if path else None})
    path_re = path_regex(prefix, path) if path else None
    id_re = re.compile(rf"(?<![\w$]){re.escape(op_id)}(?![\w$])")
    hits = []
    for top in PRODUCT_DIRS:
        d = ctx.root / top
        for f in sorted(d.rglob("*")) if d.is_dir() else []:
            if not f.is_file() or f.suffix not in SOURCE_SUFFIXES or "node_modules" in f.parts:
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").split("\n"), start=1):
                matched = [k for k, r in (("path", path_re), ("operationId", id_re)) if r is not None and r.search(line)]
                if matched:
                    hits.append({"file": f.relative_to(ctx.root).as_posix(), "line": n, "matched": matched, "text": line.strip()[:200]})
    row["code_hits"] = hits
    row["code_files"] = sorted({h["file"] for h in hits})


def find_root(start: Path) -> Path | None:
    for p in [start, *start.parents]:
        if (p / "specs" / "truth").is_dir():
            return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="List a plan's truth-delta rows with the static impact /tasks needs to cut phases and task paths, as JSON.")
    parser.add_argument("--plan", required=True, help="Plan package directory, e.g. specs/plans/004-full-amount-gift")
    args = parser.parse_args()
    plan = Path(args.plan).resolve()
    delta = plan / "truth-delta.md"
    if not delta.is_file():
        sys.stderr.write(f"error: '{delta}' does not exist; create it with the truth-delta skill (scripts/init_delta.py)\n")
        return 2
    root = find_root(plan)
    if root is None:
        sys.stderr.write(f"error: no specs/truth/ above '{plan}'; pass a plan directory inside the repository\n")
        return 2
    prefix_m = re.match(r"^(\d{3})-", plan.name)
    if not prefix_m:
        sys.stderr.write(f"error: plan directory '{plan.name}' is not named <NNN>-<name>\n")
        return 2
    prefix = prefix_m.group(1)
    text = delta.read_text(encoding="utf-8")
    base = header_value(text, "Base")
    git = Git(root, base)
    ctx = Context(root, git, prefix)
    if not git.ok:
        ctx.warnings.append(f"Base '{base}' is not readable through git; DELETE rows are resolved without Base contents")

    spec_path = plan / "spec.md"
    stories, where, changes = ([], {}, [])
    if spec_path.is_file():
        stories, where, changes = parse_spec(spec_path.read_text(encoding="utf-8"), prefix)
    else:
        ctx.warnings.append(f"{spec_path.relative_to(root)} not found; stories and attribution are empty")
    priority = {s["number"]: int(s["priority"][1:]) for s in stories}

    sections = {}
    for key, heading in SECTIONS.items():
        rows = section_rows(text, heading)
        for row in rows:
            if key == "features":
                if row["location"].split(" › ", 1)[0].endswith(".feature"):
                    resolve_feature_row(ctx, row, where, priority, changes)
                else:
                    resolve_dsl_row(ctx, row)
            elif key == "contracts":
                resolve_contract_row(ctx, row)
        sections[key] = rows

    result = {
        "plan": plan.relative_to(root).as_posix(),
        "base": base,
        "base_available": git.ok,
        "sections": sections,
        "stories": stories,
        "requirement_sections": where,
        "existing_requirement_changes": changes,
        "warnings": ctx.warnings,
        "problems": ctx.problems,
    }
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for w in ctx.warnings:
        sys.stderr.write(f"warning: {w}\n")
    if ctx.problems:
        sys.stderr.write("upstream problems found; hand back to /dsl-refine (or fix truth-delta.md):\n  " + "\n  ".join(ctx.problems) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
