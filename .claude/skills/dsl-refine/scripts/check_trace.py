# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check two-way trace coverage between acceptance checkpoints, spec requirements and endpoint feature files.

Checkpoints and trace keys follow the same definition as list_checkpoints.py. Endpoint feature files
are every *.feature under --features-dir outside the acceptance directory; their trace tags are the
`@ac:` tags on the tag lines directly above an Example / Scenario Outline.

With --spec, `@spec:<FR-nnn|NFR-nnn>` tags are also checked: a tag whose id is not defined in spec.md
(a line starting with `- **FR-nnn**` or `- **NFR-nnn**`) is dangling, and every defined id that no
`@spec` tag points to is listed as `SPEC-UNTAGGED <id>` for a human to confirm it is covered by an
acceptance checkpoint or is a measurement-only requirement (informational, not a failure).

Output (stdout): one line per uncovered checkpoint (`UNCOVERED <key>`) and per dangling tag
(`DANGLING <file>:<line> <tag>`), then `SPEC-UNTAGGED` lines, a coverage table `<key> <endpoints>`
and a summary line. Exit 1 when any checkpoint is uncovered or any tag is dangling.

Usage:
    uv run scripts/check_trace.py --acceptance-dir <features/acceptance> --features-dir <features> [--spec <spec.md>]
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


HEADER = re.compile(r"^(Feature|Rule|Background|Scenario Outline|Scenario Template|Scenario|Example|Examples|Scenarios):\s*(.*)$")
STEP = re.compile(r"^(Given|When|Then|And|But)\s")


class Step:
    def __init__(self, keyword: str, lines: list[str]) -> None:
        self.keyword = keyword  # Given / When / Then after resolving And / But
        self.lines = lines  # leading comments, the step line, and its table or doc string


class Checkpoint:
    def __init__(self, key: str, file: str, journey: str, before: list[Step], when: list[Step], then: list[Step]) -> None:
        self.key, self.file, self.journey = key, file, journey
        self.before, self.when, self.then = before, when, then


def theme_of(path: Path) -> str:
    return re.sub(r"\s+", "_", path.stem)


def parse_file(path: Path) -> tuple[int, list[Checkpoint]]:
    theme = theme_of(path)
    feature_bg: list[Step] = []
    rule_bg: list[Step] = []
    journeys: list[tuple[str, list[Step]]] = []
    target: list[Step] | None = None
    pending: list[str] = []
    in_bg = None  # "feature" | "rule" | None
    rule_seen = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s:
            continue
        head = HEADER.match(s)
        if head:
            word = head.group(1)
            pending = []
            if word == "Feature":
                continue
            if word == "Rule":
                rule_seen, rule_bg, target, in_bg = True, [], None, None
            elif word == "Background":
                in_bg = "rule" if rule_seen else "feature"
                target = rule_bg if rule_seen else feature_bg
            elif word in ("Examples", "Scenarios"):
                target = None
            else:
                steps: list[Step] = list(feature_bg) + list(rule_bg)
                journeys.append((head.group(2).strip(), steps))
                target, in_bg = steps, None
            continue
        if target is None:
            continue
        if s.startswith("#") or s.startswith("@"):
            pending.append(raw.rstrip())
            continue
        m = STEP.match(s)
        if m:
            kw = m.group(1)
            if kw in ("And", "But"):
                kw = target[-1].keyword if target else "Given"
            target.append(Step(kw, pending + [raw.rstrip()]))
            pending = []
            continue
        if target:
            target[-1].lines.append(raw.rstrip())  # data table row or doc string line
    out: list[Checkpoint] = []
    for j, (title, steps) in enumerate(journeys, 1):
        n = 0
        i = 0
        while i < len(steps):
            if steps[i].keyword != "Then":
                i += 1
                continue
            start = i
            while i < len(steps) and steps[i].keyword == "Then":
                i += 1
            w = start
            while w > 0 and steps[w - 1].keyword == "When":
                w -= 1
            n += 1
            out.append(Checkpoint(f"@ac:{theme}:{j}-{n}", path.name, title, steps[:w], steps[w:start], steps[start:i]))
    return len(journeys), out



TRACE_TAG = re.compile(r"^@ac:[^\s:@]+:\d+-\d+$")
SPEC_TAG = re.compile(r"^@spec:((?:FR|NFR)-\d+)$")
SPEC_ID = re.compile(r"^\s*-\s+\*\*((?:FR|NFR)-\d+)\*\*")
SCENARIO = re.compile(r"^(Scenario Outline|Scenario Template|Scenario|Example):")


def endpoint_tags(path: Path) -> list[tuple[int, str]]:
    # Trace tags on the consecutive tag lines directly above an Example / Scenario Outline.
    found: list[tuple[int, str]] = []
    pending: list[tuple[int, str]] = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = raw.strip()
        if s.startswith("@"):
            text = re.split(r"\s#", s, maxsplit=1)[0]
            pending += [(n, "@" + t.strip()) for t in text.split("@") if t.strip()]
            continue
        if not s or s.startswith("#"):
            continue
        if SCENARIO.match(s):
            found += [(ln, t) for ln, t in pending if t.startswith(("@ac:", "@spec:"))]
        pending = []
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Check two-way trace coverage between a features/acceptance directory and its endpoint feature files.")
    parser.add_argument("--acceptance-dir", required=True, help="Path to specs/<NNN>-<name>/features/acceptance")
    parser.add_argument("--features-dir", required=True, help="Path to specs/<NNN>-<name>/features holding the endpoint directories")
    parser.add_argument("--spec", help="Path to spec.md; enables @spec:<FR|NFR-nnn> tag checks")
    args = parser.parse_args()
    acc, root = Path(args.acceptance_dir), Path(args.features_dir)
    acc_files = sorted(acc.glob("*.feature")) if acc.is_dir() else []
    if not acc_files:
        sys.stderr.write(f"error: no *.feature files in '{acc}'; pass --acceptance-dir <features/acceptance>\n")
        return 2
    if not root.is_dir():
        sys.stderr.write(f"error: '{root}' is not a directory; pass --features-dir <features directory>\n")
        return 2
    keys: list[str] = []
    for f in acc_files:
        keys += [c.key for c in parse_file(f)[1]]
    acc_resolved = acc.resolve()
    endpoint_files = sorted(p for p in root.rglob("*.feature") if acc_resolved not in p.resolve().parents)
    if not endpoint_files:
        sys.stderr.write(f"error: no endpoint *.feature files under '{root}' outside '{acc}'; write the endpoint features first\n")
        return 2
    known = set(keys)
    spec_ids: list[str] = []
    if args.spec:
        spec_path = Path(args.spec)
        if not spec_path.is_file():
            sys.stderr.write(f"error: '{spec_path}' is not a file; pass --spec <path to spec.md>\n")
            return 2
        for line in spec_path.read_text(encoding="utf-8").splitlines():
            m = SPEC_ID.match(line)
            if m and m.group(1) not in spec_ids:
                spec_ids.append(m.group(1))
    spec_tagged: dict[str, set[str]] = {i: set() for i in spec_ids}
    covered: dict[str, set[str]] = {k: set() for k in keys}
    problems: list[str] = []
    for f in endpoint_files:
        rel = f.relative_to(root)
        endpoint = rel.parts[0] if len(rel.parts) > 1 else "."
        for n, tag in endpoint_tags(f):
            if tag.startswith("@spec:"):
                m = SPEC_TAG.match(tag)
                if not args.spec:
                    continue
                if not m or m.group(1) not in spec_tagged:
                    problems.append(f"DANGLING {rel}:{n} {tag}")
                else:
                    spec_tagged[m.group(1)].add(endpoint)
            elif not TRACE_TAG.match(tag) or tag not in known:
                problems.append(f"DANGLING {rel}:{n} {tag}")
            else:
                covered[tag].add(endpoint)
    for k in keys:
        if not covered[k]:
            problems.append(f"UNCOVERED {k}")
    for p in problems:
        sys.stdout.write(p + "\n")
    untagged = [i for i in spec_ids if not spec_tagged[i]]
    for i in untagged:
        sys.stdout.write(f"SPEC-UNTAGGED {i}\n")
    for k in keys:
        sys.stdout.write(f"{k} {','.join(sorted(covered[k])) or '-'}\n")
    for i in spec_ids:
        if spec_tagged[i]:
            sys.stdout.write(f"@spec:{i} {','.join(sorted(spec_tagged[i]))}\n")
    uncovered = sum(1 for k in keys if not covered[k])
    sys.stdout.write(
        f"checkpoints={len(keys)} uncovered={uncovered} "
        f"dangling={len(problems) - uncovered} endpoint_files={len(endpoint_files)} "
        f"spec_ids={len(spec_ids)} spec_untagged={len(untagged)}\n"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
