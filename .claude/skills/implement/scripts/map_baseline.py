# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Map every failed or undefined scenario of baseline test reports to the plan's truth-delta features rows, and list what cannot be mapped.

Reports are cucumber-js JSON formatter output (a JSON array of features) or Playwright JSON reporter output
(an object with `suites`; playwright-bdd specs `<featuresRoot>/<module>/<file>.feature.spec.js`); the format
is detected per file. A failure maps to a truth-delta row of `## /dsl-refine — truth/features/` when
- the row names its feature file (whole file, `› Feature`, `› Rule: …`, or the Example with the same title), or
- the row is a dsl sentence (`<ep>/<module>/dsl.md › <Given|When|Then> › <sentence>`) of the same endpoint that
  the failing step's text matches.
Exit 1 when any failure is unmapped, 0 when every failure is mapped (or there is none), 2 on unusable input.

Usage:
    uv run scripts/map_baseline.py --plan <specs/plans/NNN-name> --report <report.json> [--report ...]
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


_require()

FEATURES_HEADING = "## /dsl-refine — truth/features/"
TRUTH_FEATURES = "specs/truth/features"
CUCUMBER_FAILED = {"failed", "undefined", "ambiguous", "pending"}
PLAYWRIGHT_FAILED = {"failed", "timedOut", "interrupted"}
STRICT_VALUE = r'"[^"]*"|<[^>]*>|-?\d+(?:\.\d+)?'
LOOSE_VALUE = r".+?"
HEADER_KW = re.compile(r"^(Feature|Rule|Background|Examples|Scenarios|Scenario Outline|Scenario Template|Example|Scenario):\s*(.*)$")
STEP_PREFIX = re.compile(r"^(?:Given|When|Then|And|But|\*)\s+")
OUTLINE_ROW_TITLE = re.compile(r"^Example #\d+")


def split_cells(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return [c.strip() for c in re.split(r"(?<!\\)\|", inner)]


def feature_rows(text: str) -> list[dict]:
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == FEATURES_HEADING), None)
    rows = []
    if start is None:
        return rows
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if not line.startswith("|"):
            continue
        cells = split_cells(line)
        if len(cells) != 4 or cells[0] not in ("ADD", "MODIFY", "DELETE"):
            continue
        location = " ".join(cells[1].replace("`", "").split())
        parts = location.split(" › ")
        row = {"action": cells[0], "location": location, "endpoint": parts[0].split("/", 1)[0]}
        if parts[0].endswith(".feature"):
            row["feature"] = f"{TRUTH_FEATURES}/{parts[0]}"
            rest = parts[1:]
            row["rule"] = rest[0][len("Rule: "):] if rest and rest[0].startswith("Rule: ") else None
            last = rest[-1] if rest else ""
            m = re.match(r"^(?:Example|Scenario|Scenario Outline|Scenario Template): (.*?)(?: #\d+)?$", last)
            row["example"] = m.group(1) if m else None
        else:
            loc = location.split(" › ", 2)
            if len(loc) == 3 and loc[1] in ("Given", "When", "Then"):
                pieces = re.split(r"\{[^}]*\}", loc[2])
                row["sentence"] = loc[2]
                row["regex"] = [re.compile("^" + f"(?:{v})".join(re.escape(p) for p in pieces) + "$") for v in (STRICT_VALUE, LOOSE_VALUE)]
        rows.append(row)
    return rows


def feature_titles(text: str) -> list[tuple[int, str, str | None]]:
    # (line, title, rule) of every Example in a feature file.
    out, rule, in_doc = [], None, False
    for n, raw in enumerate(text.split("\n"), start=1):
        s = raw.strip()
        if s.startswith('"""') or s.startswith("```"):
            in_doc = not in_doc
            continue
        m = None if in_doc else HEADER_KW.match(s)
        if not m:
            continue
        if m.group(1) == "Rule":
            rule = m.group(2).strip()
        elif m.group(1) in ("Example", "Scenario", "Scenario Outline", "Scenario Template"):
            out.append((n, m.group(2).strip(), rule))
    return out


class Truth:
    def __init__(self, root: Path):
        self.root = root
        base = root / TRUTH_FEATURES
        self.files = [p.relative_to(root).as_posix() for p in sorted(base.rglob("*.feature"))] if base.is_dir() else []
        self._titles: dict[str, list] = {}

    def resolve(self, raw: str) -> str | None:
        # A report path (relative, absolute, or a playwright-bdd generated spec) -> specs/truth/features/... path.
        path = raw.replace("\\", "/")
        path = re.sub(r"\.spec\.[cm]?[jt]s$", "", path)
        if TRUTH_FEATURES + "/" in path:
            return TRUTH_FEATURES + "/" + path.split(TRUTH_FEATURES + "/", 1)[1]
        path = path.split(".features-gen/", 1)[-1].lstrip("./")
        hits = [f for f in self.files if f == path or f.endswith("/" + path)]
        return hits[0] if len(hits) == 1 else None

    def titles(self, feature: str) -> list:
        if feature not in self._titles:
            path = self.root / feature
            self._titles[feature] = feature_titles(path.read_text(encoding="utf-8")) if path.is_file() else []
        return self._titles[feature]


def step_text(name: str) -> str:
    return STEP_PREFIX.sub("", name.strip())


def cucumber_failures(report: list, source: str) -> list[dict]:
    out = []
    for feature in report:
        uri = feature.get("uri", "")
        background_failure = None
        for element in feature.get("elements", []):
            failing = None
            status = None
            for step in element.get("steps", []):
                result = (step.get("result") or {}).get("status")
                if result in CUCUMBER_FAILED and failing is None:
                    hidden = step.get("hidden") or step.get("keyword", "").strip() in ("Before", "After")
                    failing = "(hook)" if hidden else step_text(step.get("name", ""))
                    status = result
            if element.get("type") == "background":
                background_failure = (failing, status) if failing else None
                continue
            if failing is None and background_failure:
                failing, status = background_failure
            background_failure = None
            if failing is None:
                continue
            out.append({"report": source, "uri": uri, "title": element.get("name", "").strip(), "titles": [],
                        "line": element.get("line"), "step": failing, "status": status})
    return out


def playwright_failures(report: dict, source: str) -> list[dict]:
    out = []

    def failed_step(steps: list) -> str | None:
        for step in steps or []:
            inner = failed_step(step.get("steps"))
            if inner:
                return inner
            if step.get("error"):
                return step.get("title")
        return None

    def walk(suite: dict, chain: list[str]) -> None:
        here = chain + ([suite["title"]] if suite.get("title") and not suite["title"].endswith((".js", ".ts")) else [])
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                results = test.get("results", [])
                last = results[-1] if results else {}
                outcome = test.get("status")
                if outcome in ("expected", "flaky", "skipped"):
                    continue
                if outcome != "unexpected" and last.get("status") not in PLAYWRIGHT_FAILED:
                    continue
                step = failed_step(last.get("steps"))
                out.append({"report": source, "uri": spec.get("file") or suite.get("file", ""), "title": spec.get("title", "").strip(),
                            "titles": here, "line": None, "step": step_text(step) if step else None,
                            "status": last.get("status", "failed")})
        for child in suite.get("suites", []):
            walk(child, here)

    for suite in report.get("suites", []):
        walk(suite, [])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Map every failed or undefined scenario of baseline test reports to the plan's truth-delta features rows, and list what cannot be mapped.")
    parser.add_argument("--plan", required=True, help="Plan package directory holding truth-delta.md, e.g. specs/plans/004-full-amount-gift")
    parser.add_argument("--report", required=True, action="append", help="cucumber-js JSON or Playwright JSON report; repeat for several")
    args = parser.parse_args()
    plan = Path(args.plan).resolve()
    delta = plan / "truth-delta.md"
    if not delta.is_file():
        sys.stderr.write(f"error: '{delta}' does not exist; pass the plan directory created by the truth-delta skill\n")
        return 2
    root = next((p for p in [plan, *plan.parents] if (p / "specs" / "truth").is_dir()), None)
    if root is None:
        sys.stderr.write(f"error: no specs/truth/ above '{plan}'; pass a plan directory inside the repository\n")
        return 2
    rows = feature_rows(delta.read_text(encoding="utf-8"))
    truth = Truth(root)
    failures: list[dict] = []
    for raw in args.report:
        path = Path(raw)
        if not path.is_file():
            sys.stderr.write(f"error: report '{path}' does not exist; run the suite with a JSON formatter "
                             "(cucumber-js `--format json:<file>`, Playwright `--reporter=json`) first\n")
            return 2
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"error: report '{path}' is not JSON ({exc}); pass the JSON formatter output, not the HTML report\n")
            return 2
        if isinstance(data, list):
            failures += cucumber_failures(data, path.as_posix())
        elif isinstance(data, dict) and "suites" in data:
            failures += playwright_failures(data, path.as_posix())
        else:
            sys.stderr.write(f"error: report '{path}' is neither cucumber-js JSON (an array of features) nor Playwright JSON (an object with suites)\n")
            return 2

    mapped, unmapped = [], []
    for failure in failures:
        feature = truth.resolve(failure["uri"])
        failure["feature"] = feature or failure["uri"]
        titles = truth.titles(feature) if feature else []
        candidates = [failure["title"]] + list(reversed(failure["titles"]))
        if failure["line"] is None:
            # Playwright: find the Example by title (an Outline row titled "Example #n" uses its parent's title).
            for title in candidates:
                hit = next((t for t in titles if t[1] == title), None)
                if hit:
                    failure["line"], failure["title"] = hit[0], hit[1]
                    break
        example = next((t for t in titles if t[0] == failure["line"]), None)
        if example is None and failure["line"] is not None:
            example = max((t for t in titles if t[0] <= failure["line"]), default=None, key=lambda t: t[0])
        rule = example[2] if example else None
        title = example[1] if example else failure["title"]
        endpoint = feature.split("/")[3] if feature else None
        hits = []
        for row in rows:
            if row.get("feature"):
                if row["feature"] != feature:
                    continue
                if row["example"] is not None and row["example"] != title:
                    continue
                if row["example"] is None and row["rule"] is not None and row["rule"] != rule:
                    continue
                hits.append(row)
            elif row.get("regex") and failure["step"] and row["endpoint"] == endpoint:
                if any(r.match(failure["step"]) for r in row["regex"]):
                    hits.append(row)
        failure["rows"] = [f"{r['action']} `{r['location']}`" for r in hits]
        (mapped if hits else unmapped).append(failure)

    def line(f: dict) -> str:
        where = f"{f['feature']}:{f['line']}" if f["line"] else f["feature"]
        step = f"；失敗步驟：{f['step']}" if f["step"] else ""
        return f"- {where} 「{f['title']}」 [{f['status']}]{step}（{f['report']}）"

    out = [f"MAPPED ({len(mapped)}):"]
    for f in mapped:
        out.append(line(f))
        out += [f"    -> {r}" for r in f["rows"]]
    out.append(f"UNMAPPED ({len(unmapped)}):")
    out += [line(f) for f in unmapped]
    sys.stdout.write("\n".join(out) + "\n")
    if unmapped:
        sys.stderr.write(f"{len(unmapped)} failure(s) map to no truth-delta row; rerun once to rule out flakiness, then hand back to /dsl-refine or confirm them as known failures\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
