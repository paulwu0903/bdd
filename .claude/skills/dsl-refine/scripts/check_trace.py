# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check trace coverage between one plan's acceptance checkpoints and the truth endpoint feature files.

Checkpoints and trace keys follow list_checkpoints.py (`@ac:<NNN>/<主題>:<J>-<C>`). Endpoint feature
files are every *.feature under <truth>/features; their trace tags are the `@ac:` / `@spec:` tags on the
tag lines directly above an Example / Scenario Outline.

  - `@ac:<NNN>/…` of this plan: checked against this plan's checkpoints; every checkpoint no endpoint
    covers is `UNCOVERED <key>`.
  - `@ac:<MMM>/…` of another plan: checked against <plans-root>/<MMM>-*/features/acceptance.
  - `@spec:<NNN>/<FR|NFR-nnn>`: checked against <truth>/requirements.md (`- **NNN/FR-nnn**` entries), so
    a tag left on a deleted requirement is caught. When requirements.md does not exist the `@spec` ids
    are not checked (a NOTE line says so); only their form is.
  - A trace tag without the `NNN/` prefix, or of any other malformed form, is dangling.
  - This plan's own FR / NFR ids (spec.md items, prefixed with NNN/) and the ids its spec.md
    `## 既有需求異動` table MODIFYs that no `@spec` tag points to are listed as `SPEC-UNTAGGED <id>`
    (informational: covered by a checkpoint, or measurement-only).

Output (stdout): `UNCOVERED <key>` and `DANGLING <file>:<line> <tag> (<reason>)` lines, `SPEC-UNTAGGED`
lines, a coverage table for this plan (`<key> <endpoints>`, `@spec:<id> <endpoints>`) and a summary line.
Exit 1 when any checkpoint is uncovered or any tag is dangling; exit 2 on bad input.

Usage:
    uv run scripts/check_trace.py --plan <specs/plans/NNN-name> [--truth <specs/truth>] [--plans-root <specs/plans>]
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


def plan_number(acceptance: Path) -> str | None:
    # <NNN>-<name>/features/acceptance -> NNN
    d = acceptance.resolve()
    if d.name != "acceptance" or d.parent.name != "features":
        return None
    m = re.match(r"^(\d{3})-", d.parent.parent.name)
    return m.group(1) if m else None


def parse_file(path: Path, nnn: str) -> tuple[int, list[Checkpoint]]:
    theme = f"{nnn}/{theme_of(path)}"
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


AC_TAG = re.compile(r"^@ac:(\d{3})/[^\s:@/]+:\d+-\d+$")
SPEC_TAG = re.compile(r"^@spec:(\d{3}/(?:FR|NFR)-\d+[a-z]?)$")
REQ_ENTRY = re.compile(r"^- \*\*(\d{3}/(?:N?FR|SC)-\d+[a-z]?)\*\*")
SPEC_ITEM = re.compile(r"^\s*-\s+\*\*((?:FR|NFR)-\d+[a-z]?)\*\*")
CHANGE_ROW = re.compile(r"^\|\s*\d+\s*\|\s*(MODIFY|DELETE)\s*\|\s*`(\d{3}/(?:N?FR|SC)-\d+[a-z]?)`")
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


def acceptance_keys(acceptance: Path, nnn: str) -> list[str] | None:
    files = sorted(acceptance.glob("*.feature")) if acceptance.is_dir() else []
    if not files:
        return None
    keys: list[str] = []
    for f in files:
        keys += [c.key for c in parse_file(f, nnn)[1]]
    return keys


def own_spec_ids(spec: Path, nnn: str) -> list[str]:
    # This plan's FR / NFR items plus the existing ids its 既有需求異動 table MODIFYs.
    ids: list[str] = []
    if not spec.is_file():
        return ids
    in_changes = False
    for line in spec.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_changes = line.strip() == "## 既有需求異動"
            continue
        m = CHANGE_ROW.match(line) if in_changes else SPEC_ITEM.match(line)
        if not m:
            continue
        rid = m.group(2) if in_changes else f"{nnn}/{m.group(1)}"
        if in_changes and m.group(1) != "MODIFY":
            continue
        if re.search(r"/N?FR-", rid) and rid not in ids:
            ids.append(rid)
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Check trace coverage between one plan's acceptance checkpoints and the truth endpoint feature files.")
    parser.add_argument("--plan", required=True, help="Plan directory specs/plans/<NNN>-<name>")
    parser.add_argument("--truth", help="Truth directory (default: <plan>/../../truth)")
    parser.add_argument("--plans-root", help="Directory holding every plan (default: <plan>/..)")
    args = parser.parse_args()
    plan = Path(args.plan).resolve()
    m = re.match(r"^(\d{3})-", plan.name)
    if not plan.is_dir() or not m:
        sys.stderr.write(f"error: '{args.plan}' is not a plan directory; pass --plan specs/plans/<NNN>-<name>\n")
        return 2
    nnn = m.group(1)
    truth = Path(args.truth).resolve() if args.truth else plan.parent.parent / "truth"
    plans_root = Path(args.plans_root).resolve() if args.plans_root else plan.parent
    keys = acceptance_keys(plan / "features" / "acceptance", nnn)
    if keys is None:
        sys.stderr.write(f"error: no *.feature files in '{plan / 'features' / 'acceptance'}'; run /spec-by-example first\n")
        return 2
    features_root = truth / "features"
    endpoint_files = sorted(features_root.rglob("*.feature")) if features_root.is_dir() else []
    if not endpoint_files:
        sys.stderr.write(f"error: no endpoint *.feature files under '{features_root}'; pass --truth <specs/truth>\n")
        return 2
    requirements = truth / "requirements.md"
    req_ids: set[str] | None = None
    if requirements.is_file():
        req_ids = {m.group(1) for line in requirements.read_text(encoding="utf-8").splitlines() if (m := REQ_ENTRY.match(line))}
    other_keys: dict[str, set[str] | None] = {}

    def keys_of(mmm: str) -> set[str] | None:
        # Checkpoint keys of another plan's frozen acceptance, cached; None when it has none.
        if mmm not in other_keys:
            dirs = sorted(plans_root.glob(f"{mmm}-*/features/acceptance"))
            found = acceptance_keys(dirs[0], mmm) if dirs else None
            other_keys[mmm] = set(found) if found is not None else None
        return other_keys[mmm]

    spec_ids = own_spec_ids(plan / "spec.md", nnn)
    spec_tagged: dict[str, set[str]] = {i: set() for i in spec_ids}
    covered: dict[str, set[str]] = {k: set() for k in keys}
    known = set(keys)
    problems: list[str] = []
    for f in endpoint_files:
        rel = f.relative_to(features_root)
        endpoint = rel.parts[0] if len(rel.parts) > 1 else "."
        for n, tag in endpoint_tags(f):
            reason = None
            if tag.startswith("@spec:"):
                sm = SPEC_TAG.match(tag)
                if not sm:
                    reason = "needs @spec:<NNN>/<FR|NFR-nnn>"
                elif req_ids is not None and sm.group(1) not in req_ids:
                    reason = "no such requirement in truth/requirements.md"
                elif sm.group(1) in spec_tagged:
                    spec_tagged[sm.group(1)].add(endpoint)
            else:
                am = AC_TAG.match(tag)
                if not am:
                    reason = "needs @ac:<NNN>/<主題>:<J>-<C>"
                elif am.group(1) == nnn:
                    if tag in known:
                        covered[tag].add(endpoint)
                    else:
                        reason = f"no such checkpoint in plan {nnn}"
                else:
                    other = keys_of(am.group(1))
                    if other is None:
                        reason = f"plan {am.group(1)} has no acceptance"
                    elif tag not in other:
                        reason = f"no such checkpoint in plan {am.group(1)}"
            if reason:
                problems.append(f"DANGLING {rel}:{n} {tag} ({reason})")
    uncovered = [k for k in keys if not covered[k]]
    for k in uncovered:
        sys.stdout.write(f"UNCOVERED {k}\n")
    for p in problems:
        sys.stdout.write(p + "\n")
    if req_ids is None:
        sys.stdout.write(f"NOTE {requirements} not found; @spec ids were not checked against requirements\n")
    untagged = [i for i in spec_ids if not spec_tagged[i]]
    for i in untagged:
        sys.stdout.write(f"SPEC-UNTAGGED {i}\n")
    for k in keys:
        sys.stdout.write(f"{k} {','.join(sorted(covered[k])) or '-'}\n")
    for i in spec_ids:
        if spec_tagged[i]:
            sys.stdout.write(f"@spec:{i} {','.join(sorted(spec_tagged[i]))}\n")
    sys.stdout.write(
        f"plan={nnn} checkpoints={len(keys)} uncovered={len(uncovered)} dangling={len(problems)} "
        f"endpoint_files={len(endpoint_files)} spec_ids={len(spec_ids)} spec_untagged={len(untagged)}\n"
    )
    return 1 if uncovered or problems else 0


if __name__ == "__main__":
    sys.exit(main())
