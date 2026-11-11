# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List every checkpoint of a features/acceptance directory with its trace key, preceding steps, When run and Then run.

A checkpoint is one maximal run of Then steps (And / But continue the previous keyword) inside a
Journey Example, numbered in order of appearance; a Then run that follows Given directly also counts.
Trace key: `@ac:<NNN>/<主題>:<Journey 序>-<檢查點序>`, where NNN is the plan number taken from the
directory path (specs/plans/<NNN>-<name>/features/acceptance), 主題 is the file name without `.feature`
and with whitespace replaced by `_`, and Journey 序 counts Examples in file order.
Exit 2 when the path does not reveal the plan number.

Usage:
    uv run scripts/list_checkpoints.py --dir <specs/plans/<NNN>-<name>/features/acceptance>
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


def render(steps: list[Step]) -> list[str]:
    if not steps:
        return ["    （無）"]
    return ["    " + line.strip() if not line.strip().startswith("|") else "      " + line.strip()
            for st in steps for line in st.lines]


def main() -> int:
    parser = argparse.ArgumentParser(description="List every checkpoint of a features/acceptance directory with its trace key, preceding steps, When run and Then run.")
    parser.add_argument("--dir", required=True, help="Path to specs/plans/<NNN>-<name>/features/acceptance")
    args = parser.parse_args()
    root = Path(args.dir)
    files = sorted(root.glob("*.feature")) if root.is_dir() else []
    if not files:
        sys.stderr.write(f"error: no *.feature files in '{root}'; pass --dir <specs/plans/<NNN>-<name>/features/acceptance>\n")
        return 2
    nnn = plan_number(root)
    if nnn is None:
        sys.stderr.write(f"error: cannot read the plan number from '{root}'; pass --dir <specs/plans/<NNN>-<name>/features/acceptance>\n")
        return 2
    total = 0
    journeys = 0
    for f in files:
        count, cps = parse_file(f, nnn)
        journeys += count
        for c in cps:
            total += 1
            sys.stdout.write(f"## {c.key}\n")
            sys.stdout.write(f"- 檔案：{c.file}\n- Journey：{c.journey}\n- 前置步驟：\n")
            sys.stdout.write("\n".join(render(c.before)) + "\n")
            sys.stdout.write("- When 段：\n" + "\n".join(render(c.when)) + "\n")
            sys.stdout.write("- Then 段：\n" + "\n".join(render(c.then)) + "\n\n")
    sys.stdout.write(f"files={len(files)} journeys={journeys} checkpoints={total}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
