# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Print the next executable batch of pending tasks from a tasks.md, with its Phase, Checkpoint and the
Independent Tests of the User Stories its Checkpoint cites, taken from spec.md. Each printed task has the
phase's '**Phase Must Read**:' entries merged in front of its own Must Read, so the task text is self-contained.
Document paths of Must Read and Optional entries are printed from the repository root: a path starting with
`specs/` already is; any other path is resolved from the plan directory named by the tasks.md header
(`**Plan**: `specs/plans/<NNN>-<name>``, or the older `**Feature Directory**:`). Entries whose document does not
exist are reported on stderr (impact-audit.md is exempt until its 盤點 task writes it).

Usage:
    uv run scripts/next_batch.py --tasks <tasks.md> --spec <spec.md> [--range <T010-T030 | T010- | -T030 | T015 | phase:2 | phase:2-3>]
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


_require()

_PHASE = re.compile(r"^## Phase (\d+): (.+)$")
_SECTION = re.compile(r"^### (.+)$")
_TASK = re.compile(r"^- \[( |X|x)\] T(\d{3}) (.*)$")
_CHECKPOINT = re.compile(r"^\*\*Checkpoint\*\*: (.+)$")
_SHARED_HEAD = re.compile(r"^\*\*Phase Must Read\*\*:\s*$")
_SHARED_ITEM = re.compile(r"^- (`.+)$")
_CITED_STORY = re.compile(r"使用者故事 (\d+)")
_ALL_STORIES = "各使用者故事"
_PHASE_STORY = re.compile(r"\bUser Story (\d+)\b")
_STORY = re.compile(r"^### User Story (\d+)\b")
_INDEPENDENT = re.compile(r"^\*\*Independent Test\*\*: (.+)$")
_RANGE_IDS = re.compile(r"^(?:T(\d{3}))?-(?:T(\d{3}))?$")
_RANGE_ONE = re.compile(r"^T(\d{3})$")
_RANGE_PHASE = re.compile(r"^phase:(\d+)(?:-(\d+))?$")
_PATH = re.compile(r"`([^`]+)`")
_PLAN_HEADER = re.compile(r"^\*\*(?:Plan|Feature Directory)\*\*: `([^`]+)`\s*$", re.M)
_ENTRY = re.compile(r"^(    - `)([^`]+)(`.*)$")


def _locate(tasks_path: Path, text: str) -> tuple[Path, str | None]:
    # Repository root and the plan directory (relative to it) named by the tasks.md header.
    header = _PLAN_HEADER.search(text)
    plan = header.group(1).strip().rstrip("/") if header else None
    here = tasks_path.resolve().parent
    if plan and here.as_posix().endswith("/" + plan):
        return Path(here.as_posix()[: -len(plan) - 1]), plan
    root = next((p for p in [here, *here.parents] if (p / "specs").is_dir()), Path.cwd())
    if plan:
        return root, plan
    # No header: tasks.md sits in the plan directory itself.
    return root, here.relative_to(root).as_posix() if here.is_relative_to(root) else None


def _resolve(block: list[str], root: Path, plan: str | None) -> tuple[list[str], list[str]]:
    # Rewrite each contract entry's document to its repository-root path; collect documents that do not exist.
    out, missing = [], []
    for line in block:
        m = _ENTRY.match(line)
        if not m:
            out.append(line)
            continue
        doc = m.group(2)
        if not doc.startswith("specs/") and plan:
            doc = f"{plan}/{doc}"
        clean = re.sub(r":\d+$", "", re.split(r"[?#]", doc, maxsplit=1)[0])
        if not (root / clean).exists() and not clean.endswith("impact-audit.md"):
            missing.append(doc)
        out.append(m.group(1) + doc + m.group(3))
    return out, missing


def _parse(text: str) -> tuple[list[dict], list[dict]]:
    # Split tasks.md into phases (title, checkpoint) and tasks (id, done, parallel, section, block).
    phases: list[dict] = []
    tasks: list[dict] = []
    section = None
    for line in text.splitlines():
        m = _PHASE.match(line)
        if m:
            phases.append({"number": int(m.group(1)), "title": line[3:].strip(), "checkpoint": None,
                           "shared": [], "in_shared": False})
            section = None
            continue
        if phases and _SHARED_HEAD.match(line):
            phases[-1]["in_shared"] = True
            continue
        if phases and phases[-1]["in_shared"]:
            m = _SHARED_ITEM.match(line)
            if m:
                phases[-1]["shared"].append(m.group(1))
                continue
            phases[-1]["in_shared"] = False
        if not phases:
            continue
        m = _CHECKPOINT.match(line)
        if m:
            phases[-1]["checkpoint"] = m.group(1).strip()
            continue
        m = _SECTION.match(line)
        if m:
            section = m.group(1).strip()
            continue
        m = _TASK.match(line)
        if m:
            tasks.append({
                "id": int(m.group(2)),
                "done": m.group(1) != " ",
                "parallel": "[P]" in m.group(3),
                "phase": phases[-1]["number"],
                "section": section,
                "block": [line],
            })
            continue
        if tasks and line.startswith("  ") and tasks[-1]["phase"] == phases[-1]["number"]:
            tasks[-1]["block"].append(line)
    return phases, tasks


def _independent_tests(text: str) -> dict[int, str]:
    # Map each '### User Story K' in spec.md to the '**Independent Test**:' line inside its section.
    tests: dict[int, str] = {}
    story = None
    for line in text.splitlines():
        m = _STORY.match(line)
        if m:
            story = int(m.group(1))
            continue
        if line.startswith("## ") or line.startswith("### "):
            story = None
            continue
        m = _INDEPENDENT.match(line)
        if m and story is not None and story not in tests:
            tests[story] = m.group(1).strip()
    return tests


def _merge_shared(block: list[str], shared: list[str]) -> list[str]:
    # Put the phase's shared Must Read entries first under the task's own Must Read (created if absent).
    if not shared:
        return block
    entries = [f"    - {s}" for s in shared]
    if "  - Must Read:" in block:
        i = block.index("  - Must Read:") + 1
        own = []
        while i + len(own) < len(block) and block[i + len(own)].startswith("    - "):
            own.append(block[i + len(own)])
        merged = entries + [o for o in own if o not in entries]
        return block[:i] + merged + block[i + len(own):]
    return block[:1] + ["  - Must Read:"] + entries + block[1:]


def _cited_stories(checkpoint: str | None, title: str, all_stories: list[int]) -> list[int]:
    # Stories whose Independent Test the phase end must run: those the Checkpoint cites ("各使用者故事" = all),
    # falling back to a 'User Story n' phase title for tasks.md files in the older per-story layout.
    if checkpoint:
        if _ALL_STORIES in checkpoint:
            return all_stories
        cited = sorted({int(n) for n in _CITED_STORY.findall(checkpoint)})
        if cited:
            return cited
    story = _PHASE_STORY.search(title)
    return [int(story.group(1))] if story else []


def _in_range(task: dict, spec: str | None) -> bool:
    # A task is executable only inside the --range; no range means every task.
    if spec is None:
        return True
    m = _RANGE_ONE.match(spec)
    if m:
        return task["id"] == int(m.group(1))
    m = _RANGE_IDS.match(spec)
    if m:
        low = int(m.group(1)) if m.group(1) else 1
        high = int(m.group(2)) if m.group(2) else 999
        return low <= task["id"] <= high
    m = _RANGE_PHASE.match(spec)
    if m:
        low = int(m.group(1))
        high = int(m.group(2)) if m.group(2) else low
        return low <= task["phase"] <= high
    raise ValueError(spec)


def _paths(task: dict) -> set[str]:
    # File paths are the backticked tokens after the last ' 於 ' of the task line.
    line = task["block"][0]
    _, sep, tail = line.rpartition(" 於 ")
    return set(_PATH.findall(tail)) if sep else set()


def _batch(tasks: list[dict], spec: str | None) -> list[dict]:
    # First pending task in range; a [P] task also takes the following pending [P] tasks of the same section,
    # stopping before the first one whose file paths are unknown or overlap the batch, so batched tasks stay independent.
    pending = [t for t in tasks if not t["done"] and _in_range(t, spec)]
    if not pending:
        return []
    head = pending[0]
    if not head["parallel"]:
        return [head]
    batch = [head]
    taken = _paths(head)
    if not taken:
        return batch
    start = tasks.index(head) + 1
    for t in tasks[start:]:
        if t["section"] != head["section"] or t["phase"] != head["phase"]:
            break
        if not t["parallel"]:
            break
        if not t["done"] and _in_range(t, spec):
            paths = _paths(t)
            if not paths or paths & taken:
                break
            taken |= paths
            batch.append(t)
    return batch


def _summary(phases: list[dict], tasks: list[dict]) -> str:
    lines = []
    for phase in phases:
        own = [t for t in tasks if t["phase"] == phase["number"]]
        done = sum(1 for t in own if t["done"])
        lines.append(f"{phase['title']} — {done}/{len(own)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the next executable batch of pending tasks from a tasks.md.")
    parser.add_argument("--tasks", required=True, help="Path to the tasks.md produced by the tasks skill")
    parser.add_argument("--spec", required=True, help="Path to the spec.md whose User Stories carry the Independent Test")
    parser.add_argument("--range", dest="range_spec", help="Limit to T010-T030, T010-, -T030, T015, phase:2 or phase:2-3")
    args = parser.parse_args()
    path = Path(args.tasks)
    if not path.is_file():
        sys.stderr.write(f"error: '{path}' is not a file; pass the path to an existing tasks.md\n")
        return 2
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        sys.stderr.write(f"error: '{spec_path}' is not a file; pass the path to the feature's spec.md\n")
        return 2
    text = path.read_text(encoding="utf-8")
    phases, tasks = _parse(text)
    root, plan = _locate(path, text)
    if not tasks:
        sys.stderr.write(f"error: no task lines like '- [ ] T001 ...' under '## Phase N:' headings in '{path}'\n")
        return 2
    try:
        batch = _batch(tasks, args.range_spec)
    except ValueError as exc:
        sys.stderr.write(f"error: --range '{exc}' is not T010-T030, T010-, -T030, T015, phase:2 or phase:2-3\n")
        return 2
    if not batch:
        any_pending = any(not t["done"] for t in tasks)
        sys.stdout.write(("RANGE_DONE" if any_pending else "ALL_DONE") + "\n" + _summary(phases, tasks) + "\n")
        return 0
    phase = next(p for p in phases if p["number"] == batch[0]["phase"])
    remaining = [t for t in tasks if t["phase"] == phase["number"] and not t["done"] and t not in batch]
    phase_end = not remaining
    out = [
        f"PHASE: {phase['title']}",
        f"SECTION: {batch[0]['section'] or '(none)'}",
        "TASKS: " + " ".join(f"T{t['id']:03d}" for t in batch),
        f"PHASE_END: {'yes' if phase_end else 'no'}",
    ]
    if phase_end:
        out.append(f"CHECKPOINT: {phase['checkpoint'] or '(none)'}")
        tests = _independent_tests(spec_path.read_text(encoding="utf-8"))
        for number in _cited_stories(phase["checkpoint"], phase["title"], sorted(tests)):
            independent = tests.get(number)
            if independent is None:
                sys.stderr.write(
                    f"error: phase '{phase['title']}' cites User Story {number}, but '{spec_path}' has no "
                    f"'**Independent Test**:' line under '### User Story {number} - ...'\n"
                )
                return 2
            out.append(f"INDEPENDENT_TEST (User Story {number}): {independent}")
    out.append(f"PLAN: {plan or '(unknown)'}")
    out.append("---")
    for t in batch:
        lines, missing = _resolve(_merge_shared(t["block"], phase["shared"]), root, plan)
        out.extend(lines)
        for doc in missing:
            sys.stderr.write(f"warning: T{t['id']:03d} cites `{doc}`, which does not exist under '{root}'; "
                             "check the tasks.md header **Plan** or the cited path\n")
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
