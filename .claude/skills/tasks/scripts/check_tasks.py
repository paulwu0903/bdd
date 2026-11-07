# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check a tasks.md (v2) against its plan's truth-delta.md: header, phase kinds and order, task forms, markers, checkpoints, shared blocks, contracts, NFR table, dependencies and truth-delta coverage.

Phases run Setup -> Foundational? -> Truth Impact Audit (iff truth-delta has a MODIFY or DELETE row) -> MODIFY
(`MODIFY <依據> › <端點>`, provider endpoint first) -> DELETE (`DELETE <依據> › <端點>`, consumer endpoint first;
a DELETE titled `（由 Phase <M> 取代）` sits after ADD Phase M) -> ADD (`` `specs/truth/features/<端點>/<模組>/<檔>.feature` (USn | 既有需求異動 #n | 全域 NFR) ``)
-> NFR 重構 -> Acceptance Gates, followed by the Dependencies & Execution Order and Parallel Example sections.
Every truth-delta row is covered as the shared tasks format spec §6 requires: features ADD -> an ADD Phase of
that file; features MODIFY / DELETE -> a MODIFY / DELETE Phase whose Phase Must Read cites the row's location in
truth-delta.md; techstack -> an `環境` task naming the package or item; data -> a `基礎` task naming the table.

With --structure-only every check that needs real files is skipped (truth-delta rows and coverage, spec.md
stories and NFR ids, existence of cited documents, parts and scope lines), so a fictional example can be checked.

Usage:
    uv run scripts/check_tasks.py --tasks <tasks.md> --plan <specs/plans/NNN-name> [--structure-only]
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

# --- task lines and markers -------------------------------------------------------------------------------------
_TASK_LINE = re.compile(r"^- \[(?: |X|x)\] T(\d{3}) (?P<p>\[P\] )?(?:\[US(?P<us>\d+)\] )?(?P<rest>.*)$")
_TASK_LIKE = re.compile(r"^- \[.?\] ")
_MARKERS = ("環境", "基礎", "盤點", "/bdd realign", "/bdd red", "/bdd green", "/bdd refactor", "移除", "重構", "驗證")
_MARKER = re.compile(r"^`(" + "|".join(re.escape(m) for m in _MARKERS) + r")` (.*)$")
_PATHS = r"`[^`]+`(?:、`[^`]+`)*"
_SCOPE_ITEM = r"`specs/truth/features/[^`/]+/[^`]+?\.feature(?::\d+)?`"
_SCOPES = rf"{_SCOPE_ITEM}(?:、{_SCOPE_ITEM})*"
_SENTENCE = {
    "/bdd realign": (re.compile(rf"^對齊 ({_SCOPES}) 的測試碼於 ({_PATHS})$"), "對齊 `<feature>:<行>`、… 的測試碼於 `路徑`"),
    "/bdd red": (re.compile(rf"^撰寫 ({_SCOPES}) 的 step 於 ({_PATHS})$"), "撰寫 `<範疇>` 的 step 於 `路徑`"),
    "/bdd green": (re.compile(rf"^實作 ({_SCOPES}) 的行為於 ({_PATHS})$"), "實作 `<範疇>` 的行為於 `路徑`"),
    "/bdd refactor": (re.compile(rf"^整理 ({_SCOPES}) 的程式碼於 ({_PATHS})$"), "整理 `<範疇>` 的程式碼於 `路徑`"),
    "移除": (re.compile(rf"^移除 (.+?) 的測試與產品行為於 ({_PATHS})$"), "移除 <被刪除的行為> 的測試與產品行為於 `路徑`"),
    "盤點": (re.compile(r"^盤點 (\S+) 受 truth 異動影響的 feature、step、helper、fixture 與產品行為於 (`[^`]+`)$"),
             "盤點 <端點> 受 truth 異動影響的 feature、step、helper、fixture 與產品行為於 `specs/plans/<NNN>-<name>/impact-audit.md`"),
}
_ENDS_WITH_PATHS = re.compile(rf"於 {_PATHS}$")
_SCOPED = ("/bdd realign", "/bdd red", "/bdd green", "/bdd refactor")
_KIND_MARKERS = {
    "setup": {"環境"}, "foundational": {"基礎"}, "audit": {"盤點"},
    "modify": {"/bdd realign", "/bdd green", "/bdd refactor", "基礎", "環境"},
    "delete": {"移除", "基礎", "環境"},
    "add": {"/bdd red", "/bdd green", "/bdd refactor"}, "nfr": {"重構"}, "gates": {"驗證"},
}
_KIND_LABEL = {"setup": "Setup", "foundational": "Foundational", "audit": "Truth Impact Audit", "modify": "MODIFY Phase",
               "delete": "DELETE Phase", "add": "ADD Phase", "nfr": "NFR 重構", "gates": "Acceptance Gates"}
_CHANGE_KINDS = ("modify", "delete", "add")

# --- phases, shared block, checkpoint ---------------------------------------------------------------------------
_PHASE = re.compile(r"^## Phase (\d+): (.+)$")
_MODIFY_PHASE = re.compile(r"^MODIFY (\S.*?) › ([^\s›（]+)$")
_DELETE_PHASE = re.compile(r"^DELETE (\S.*?) › ([^\s›（]+)(?:（由 Phase (\d+) 取代）)?$")
_ADD_PHASE = re.compile(r"^`(specs/truth/features/([^`/]+)/[^`]+\.feature)` \((?:US(\d+)|既有需求異動 #(\d+)|(全域 NFR))\)$")
_CHECKPOINT = re.compile(r"^\*\*Checkpoint\*\*:\s*(.*)$")
_BLOCK_HEAD = "**Phase Must Read**:"
_BLOCK_ITEM = re.compile(r"^- `([^`]+)`(?: -> (.+))?$")
_RANK = {"setup": 0, "foundational": 1, "audit": 2, "modify": 3, "delete": 4, "add": 5, "nfr": 6, "gates": 7}
_SUITE_TAIL = "整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠"
_GREEN_CHECKPOINT = re.compile(rf"^({_PATHS}) 全綠；{_SUITE_TAIL}")
_DELETE_CHECKPOINT = re.compile(rf"^({_PATHS}) 已無殘留的測試與產品行為；{_SUITE_TAIL}")
_AUDIT_CHECKPOINT = "`impact-audit.md` 涵蓋 truth-delta 的全部 MODIFY、DELETE 列，且沒有 tasks.md 未涵蓋的影響"
_PROVIDER_RANK = {"backend": 0, "frontend": 2}  # other endpoints sit between

# --- contract lines and parts -----------------------------------------------------------------------------------
_CONTRACT_LINE = re.compile(r"^    - `([^`]+)` -> (.+)$")
_DOC_ONLY_LINE = re.compile(r"^    - `([^`]+)`$")
_PART = re.compile(r"`([^`]+)`")
_PARTS_ONLY = re.compile(r"^`[^`]+`(?:, `[^`]+`)*$")
_VERSION = re.compile(r"\d+\.\d+\.\d+")
_BACKTICK_SPAN = re.compile(r"`[^`]*`")
_REQ_ID = re.compile(r"^(?:\d{3}/)?(FR|NFR|SC)-\d+$")
_RESEARCH_SECTION = re.compile(r"^(R\d+\. [^›]+?)(?: › .+)?$")
_TABLE_COLUMN = re.compile(r"^Table (\w+)\.(\w+)$")
_TABLE = re.compile(r"^Table (\w+)$")
_TABLE_GROUP = re.compile(r"^TableGroup (\S+)(?: › (.+))?$")
_SCHEMA = re.compile(r"^schemas\.(\w+)$")
_OPERATION = re.compile(r"^operationId (\S+)$")
_DSL_ROW = re.compile(r"^\| `([^`]+)` \|")
_SLICE_HEAD = re.compile(r"^\s*(?:Scenario Outline|Scenario Template|Example|Scenario):\s*(.+)$")
_RULE_HEAD = re.compile(r"^\s*Rule:\s*(.+)$")
_DSL_APPENDIX = "附錄：共通規則"

# --- header, NFR table, trailing sections -----------------------------------------------------------------------
_TITLE = re.compile(r"^# Tasks: (\S.*)$")
_PLAN_LINE = re.compile(r"^\*\*Plan\*\*: `([^`]+)`$")
_TRUTH_LINE = re.compile(r"^\*\*Truth\*\*: `([^`]+)`$")
_PLAN_PATH = re.compile(r"^specs/plans/(\d{3})-[^/\s]+$")
_FEATURE_DIR_LINE = re.compile(r"^\*\*Feature Directory\*\*:")
_INPUT_DOCS_LINE = re.compile(r"^\*\*Input Documents\*\*:")
_NFR_HEADER = ["NFR", "驗證來源", "判定"]
_NFR_ID = re.compile(r"^(?:\d{3}/)?NFR-\d+$")
_NFR_LIST = re.compile(r"^列 (T\d{3}(?:、T\d{3})*)$")
_DEPS_HEAD = "## Dependencies & Execution Order"
_DEPS_SUBSECTIONS = ("### Phase Dependencies", "### Feature Dependencies", "### Within Each Feature Phase",
                     "### Parallel Opportunities")
_FEATURE_DEPS_HEADER = ["Phase", "feature", "依賴 Phase", "依據"]
_PARALLEL_HEAD = re.compile(r"^## Parallel Example:(.*)$")

# --- spec.md, truth-delta.md, feature files ---------------------------------------------------------------------
_STORY_HEAD = re.compile(r"^### User Story (\d+) - .+\(Priority: P(\d+)\)\s*$")
_NFR_BOLD = re.compile(r"\*\*((?:\d{3}/)?NFR-\d+)\*\*")
_DELTA_SECTIONS = {
    "requirements": "## /specify — truth/requirements.md",
    "techstack": "## /technical-research — truth/techstack.md",
    "contracts": "## /api-plan — truth/contracts/",
    "data": "## /data-plan — truth/data/",
    "features": "## /dsl-refine — truth/features/",
}
_HEADER_KW = re.compile(r"^(Feature|Rule|Background|Examples|Scenarios|Scenario Outline|Scenario Template|Example|Scenario):\s*(.*)$")


def _tid(task: dict) -> str:
    return f"T{task['id']:03d}"


def _split_row(line: str) -> list[str]:
    # Cells of a markdown table row; escaped pipes stay inside their cell.
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return [c.strip() for c in re.split(r"(?<!\\)\|", inner)]


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def _table_after(lines: list[str], header: list[str]) -> tuple[bool, list[list[str]]]:
    # Find the first table whose header cells equal `header`; return whether found and its body rows.
    for index, line in enumerate(lines):
        if line.startswith("|") and _split_row(line) == header:
            rows = []
            for row in lines[index + 1:]:
                if not row.startswith("|"):
                    break
                cells = _split_row(row)
                if not _is_separator_row(cells):
                    rows.append(cells)
            return True, rows
    return False, []


def _normalize(location: str) -> str:
    return " ".join(location.replace("`", "").split())


def _scope_file(item: str) -> str:
    return re.sub(r":\d+$", "", item)


def _classify_phase(title: str) -> dict:
    # Map a phase title to its kind with the endpoint, feature, attribution and replacement it names.
    info = {"kind": None, "feature": None, "endpoint": None, "story": None, "change": None, "global": False,
            "basis": None, "replaced_by": None}
    fixed = {"Setup": "setup", "Foundational": "foundational", "Truth Impact Audit": "audit", "NFR 重構": "nfr",
             "Acceptance Gates": "gates"}
    if title in fixed:
        info["kind"] = fixed[title]
        return info
    m = _MODIFY_PHASE.match(title)
    if m:
        info.update(kind="modify", basis=m.group(1), endpoint=m.group(2))
        return info
    m = _DELETE_PHASE.match(title)
    if m:
        info.update(kind="delete", basis=m.group(1), endpoint=m.group(2),
                    replaced_by=int(m.group(3)) if m.group(3) else None)
        return info
    m = _ADD_PHASE.match(title)
    if m:
        info.update(kind="add", feature=m.group(1), endpoint=m.group(2),
                    story=int(m.group(3)) if m.group(3) else None,
                    change=int(m.group(4)) if m.group(4) else None, **{"global": bool(m.group(5))})
    return info


def _parse_entry(raw: str, match: re.Match, violations: list[str], where: str) -> tuple[str, list[str]] | None:
    # Turn one contract item into (doc, parts) and check the part format; parts are backticked ids only.
    doc = match.group(1)
    rest = match.group(2) if match.lastindex and match.lastindex >= 2 else None
    if rest is None:
        return doc, []
    outside = _BACKTICK_SPAN.sub("", rest)
    if "（" in outside or "(" in outside:
        violations.append(f"{where} 契約行含括號說明：{raw.strip()}")
    elif _VERSION.search(outside):
        violations.append(f"{where} 契約行含版本號：{raw.strip()}")
    elif not _PARTS_ONLY.match(rest.strip()):
        violations.append(f"{where} 部位須為以「, 」分隔的反引號識別碼：{raw.strip()}")
    return doc, _PART.findall(rest)


def _parse_tasks(text: str, violations: list[str]) -> tuple[list[dict], list[dict], dict]:
    # Split tasks.md into header facts, phases (with shared block, checkpoints, raw lines) and tasks (with contracts).
    tasks: list[dict] = []
    phases: list[dict] = []
    header = {"title": None, "plan": None, "truth": None, "feature_dir": False, "input_docs": False, "trailing": [],
              "lines": text.splitlines()}
    phase = None
    task = None
    section = None
    in_block = False
    in_trailing = False
    for lineno, line in enumerate(header["lines"], start=1):
        head = _PHASE.match(line)
        if head:
            title = head.group(2).strip()
            phase = {"number": int(head.group(1)), "title": title, "line": lineno, "tasks": [], "checkpoints": [],
                     "block": None, "content_started": False, "lines": [], **_classify_phase(title)}
            phases.append(phase)
            task, section, in_block = None, None, False
            if in_trailing:
                violations.append(f"Phase {phase['number']}: Phase 須排在 Dependencies & Execution Order 與 Parallel Example 之前")
            continue
        if line.startswith("## "):
            # Any other level-2 heading closes the phase list; trailing sections are never parsed as tasks.
            header["trailing"].append((lineno, line))
            phase, task, section, in_block = None, None, None, False
            in_trailing = True
            continue
        if in_trailing:
            header["trailing"].append((lineno, line))
            continue
        if phase is None:
            for regex, key in ((_TITLE, "title"), (_PLAN_LINE, "plan"), (_TRUTH_LINE, "truth")):
                m = regex.match(line)
                if m:
                    header[key] = m.group(1).strip()
            if _FEATURE_DIR_LINE.match(line):
                header["feature_dir"] = True
            if _INPUT_DOCS_LINE.match(line):
                header["input_docs"] = True
            if _TASK_LIKE.match(line):
                violations.append(f"tasks.md: 任務不在任何 Phase 底下：{line.strip()}")
            continue
        phase["lines"].append(line)
        label = f"Phase {phase['number']}"
        # Phase Must Read block.
        if line.strip() == _BLOCK_HEAD:
            if phase["content_started"]:
                violations.append(f"{label}: **Phase Must Read** 須放在 Phase 說明之後、第一個 ### 小節或任務之前")
            if phase["block"] is not None:
                violations.append(f"{label}: **Phase Must Read** 只能有一個")
            phase["block"] = phase["block"] or []
            in_block, task, section = True, None, None
            continue
        if in_block:
            if not line.strip():
                in_block = False
                continue
            item = _BLOCK_ITEM.match(line)
            if item and not _TASK_LIKE.match(line):
                entry = _parse_entry(line, item, violations, f"{label}: Phase Must Read")
                if entry:
                    phase["block"].append(entry)
                continue
            in_block = False
            if not _TASK_LIKE.match(line) and not line.startswith("#"):
                violations.append(f"{label}: Phase Must Read 的項目須為「- `文件`」或「- `文件` -> `部位`, …」：{line.strip()}")
                continue
        if line.startswith("### "):
            phase["content_started"] = True
            task, section = None, None
            continue
        checkpoint = _CHECKPOINT.match(line)
        if checkpoint:
            phase["checkpoints"].append({"text": checkpoint.group(1).strip(), "after_tasks": len(phase["tasks"])})
            task, section = None, None
            continue
        match = _TASK_LINE.match(line)
        if match:
            phase["content_started"] = True
            task = {"id": int(match.group(1)), "parallel": bool(match.group("p")),
                    "us": int(match.group("us")) if match.group("us") else None,
                    "rest": match.group("rest"), "phase": phase, "sections": {}, "entries": {}, "why": None}
            tasks.append(task)
            phase["tasks"].append(task)
            section = None
            continue
        if _TASK_LIKE.match(line):
            phase["content_started"] = True
            violations.append(f"Phase {phase['number']}: 任務列格式須為「- [ ] Txxx [P] [USn] `標記` …」：{line.strip()}")
            task, section = None, None
            continue
        if task is None or not line.startswith("  "):
            if line.strip():
                task, section = None, None
            continue
        tid = _tid(task)
        stripped = line.strip()
        if stripped in ("- Must Read:", "- Optional:"):
            section = stripped[2:-1]
            if section in task["sections"]:
                violations.append(f"{tid}: {section} 重複出現")
            task["sections"][section] = True
            task["entries"].setdefault(section, [])
        elif stripped.startswith("- Why:"):
            task["sections"]["Why"] = True
            task["why"] = stripped[len("- Why:"):].strip()
            section = None
        elif section and line.startswith("    - "):
            if stripped == "- 無":
                violations.append(f"{tid}: {section} 不寫「無」；沒有內容時整段省略")
                task["entries"][section].append(None)
                continue
            item = _CONTRACT_LINE.match(line) or _DOC_ONLY_LINE.match(line)
            if not item:
                violations.append(f"{tid}: {section} 的項目須為「`文件`」或「`文件` -> `部位`, …」：{stripped}")
                task["entries"][section].append(None)
                continue
            task["entries"][section].append(_parse_entry(line, item, violations, f"{tid}: {section}"))
        else:
            violations.append(f"{tid}: 無法辨識的契約行，只允許 Must Read、Optional 與 Why：{stripped}")
            section = None
    return tasks, phases, header


# ---------------------------------------------------------------------------------------------------------------
# Plan inputs: truth-delta rows, spec.md, feature Example lines

def _delta_rows(text: str) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {}
    lines = text.split("\n")
    for key, heading in _DELTA_SECTIONS.items():
        rows[key] = []
        start = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
        if start is None:
            continue
        for line in lines[start + 1:]:
            if line.startswith("## "):
                break
            if not line.startswith("|"):
                continue
            cells = _split_row(line)
            if len(cells) == 4 and cells[0] in ("ADD", "MODIFY", "DELETE"):
                rows[key].append({"action": cells[0], "location": _normalize(cells[1])})
    return rows


def _parse_spec(text: str) -> dict[int, int]:
    # Story priorities by story number.
    return {int(m.group(1)): int(m.group(2)) for line in text.splitlines() if (m := _STORY_HEAD.match(line))}


def _example_lines(rel: str, text: str) -> tuple[dict[str, int], set[int]]:
    # Example keys (as the truth-delta skill writes them) -> line, and every Example header line.
    keys: dict[str, int] = {}
    used = {f"{rel} › Feature"}
    rule = None
    lines: set[int] = set()
    in_doc = False
    for n, raw in enumerate(text.split("\n"), start=1):
        s = raw.strip()
        if s.startswith('"""') or s.startswith("```"):
            in_doc = not in_doc
            continue
        if in_doc:
            continue
        m = _HEADER_KW.match(s)
        if not m:
            continue
        word, title = m.group(1), m.group(2).strip()
        if word == "Rule":
            rule = title
            used.add(f"{rel} › Rule: {rule}")
        elif word in ("Example", "Scenario", "Scenario Outline", "Scenario Template"):
            base = f"{rel} › Rule: {rule} › {word}: {title}" if rule else f"{rel} › {word}: {title}"
            key, k = base, 2
            while key in used:
                key, k = f"{base} #{k}", k + 1
            used.add(key)
            keys[key] = n
            lines.add(n)
    return keys, lines


class _Docs:
    # Lazily load the headings and keys of each document that a contract may cite.
    def __init__(self, plan_dir: Path, root: Path, delta_locations: set[str]) -> None:
        self.plan_dir = plan_dir
        self.repo_root = root
        self.delta_locations = delta_locations
        self._cache: dict[str, object] = {}

    def path(self, rel: str) -> Path:
        # A path starting with specs/ is relative to the repository root, any other to the plan directory.
        clean = re.split(r"[?#]", rel, maxsplit=1)[0]
        clean = re.sub(r":\d+$", "", clean)
        return (self.repo_root if clean.startswith("specs/") else self.plan_dir) / clean

    def exists(self, rel: str) -> bool:
        # impact-audit.md is written by the Audit task, so it does not exist while planning.
        return rel.endswith("impact-audit.md") or self.path(rel).exists()

    def text(self, rel: str) -> str | None:
        if rel not in self._cache:
            path = self.path(rel)
            self._cache[rel] = path.read_text(encoding="utf-8") if path.is_file() else None
        return self._cache[rel]  # type: ignore[return-value]

    def headings(self, rel: str, levels: tuple[str, ...]) -> set[str] | None:
        text = self.text(rel)
        if text is None:
            return None
        found = set()
        for line in text.splitlines():
            for prefix in levels:
                if line.startswith(prefix):
                    found.add(line[len(prefix):].strip())
        return found

    def dbml(self, rel: str) -> tuple[dict[str, set[str]], set[str]] | None:
        # Tables with their columns, and TableGroup names.
        text = self.text(rel)
        if text is None:
            return None
        tables: dict[str, set[str]] = {}
        groups: set[str] = set()
        current = None
        for line in text.splitlines():
            group = re.match(r"^TableGroup (\S+)\s*\{", line)
            if group:
                groups.add(group.group(1))
                current = None
                continue
            head = re.match(r"^Table (\w+)\s*\{", line)
            if head:
                current = head.group(1)
                tables[current] = set()
                continue
            if current is None:
                continue
            if line.startswith("}"):
                current = None
                continue
            column = re.match(r"^  (\w+) ", line)
            if column and not line.startswith(("  indexes", "  checks", "  Note")):
                tables[current].add(column.group(1))
        return tables, groups

    def openapi(self, rel: str) -> tuple[set[str], set[str]] | None:
        # Keys under `paths` and `components.schemas`, read by indentation so no YAML library is needed.
        text = self.text(rel)
        if text is None:
            return None
        lines = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]

        def children(start: int, indent: int) -> list[tuple[int, str]]:
            found: list[tuple[int, str]] = []
            child_indent = None
            for index in range(start + 1, len(lines)):
                line = lines[index]
                level = len(line) - len(line.lstrip(" "))
                if level <= indent:
                    break
                if child_indent is None:
                    child_indent = level
                if level == child_indent:
                    key = re.match(r"^\s*(['\"]?)(.+?)\1:(?:\s|$)", line)
                    if key:
                        found.append((index, key.group(2)))
            return found

        paths: set[str] = set()
        schemas: set[str] = set()
        for index, line in enumerate(lines):
            if line.startswith("paths:"):
                paths.update(key for _, key in children(index, 0))
            if line.startswith("components:"):
                for child, key in children(index, 0):
                    if key == "schemas":
                        indent = len(lines[child]) - len(lines[child].lstrip(" "))
                        schemas.update(k for _, k in children(child, indent))
        return paths, schemas


def _check_feature_part(doc: str, part: str, docs: _Docs) -> str | None:
    # dsl.md parts are pattern texts or the appendix; feature parts are `Rule: <name>` or an Example title.
    text = docs.text(doc)
    if text is None:
        return f"{doc} 不存在"
    if doc.endswith("/dsl.md"):
        if part == _DSL_APPENDIX:
            return None if "## 附錄" in text else f"{doc} 沒有附錄段"
        patterns = {m.group(1) for line in text.splitlines() if (m := _DSL_ROW.match(line))}
        return None if part in patterns else f"{doc} 沒有句型 {part}"
    rules = {m.group(1).strip() for line in text.splitlines() if (m := _RULE_HEAD.match(line))}
    titles = {m.group(1).strip() for line in text.splitlines() if (m := _SLICE_HEAD.match(line))}
    if part.startswith("Rule: "):
        return None if part[len("Rule: "):].strip() in rules else f"{doc} 沒有 {part}"
    return None if part in titles else f"{doc} 沒有 Example {part}"


def _check_section_part(doc: str, part: str, docs: _Docs, levels: tuple[str, ...]) -> str | None:
    # `章節 › 子項`: the first segment is a heading, later segments appear in the document text.
    headings = docs.headings(doc, levels)
    if headings is None:
        return f"{doc} 不存在"
    segments = [s.strip() for s in part.split(" › ")]
    if segments[0] not in headings:
        return f"{doc} 沒有章節 {segments[0]}"
    text = docs.text(doc) or ""
    for segment in segments[1:]:
        if segment not in text:
            return f"{doc} 的章節 {segments[0]} 找不到子項 {segment}"
    return None


def _check_part(doc: str, part: str, docs: _Docs) -> str | None:
    # Return a reason when the cited part cannot be found in the document; None when found or unchecked.
    if doc.endswith("truth-delta.md"):
        return None if _normalize(part) in docs.delta_locations else f"{doc} 沒有部位為 {part} 的列"
    if doc.endswith("impact-audit.md"):
        return None
    if doc.endswith(".feature") or doc.endswith("/dsl.md"):
        return _check_feature_part(doc, part, docs)
    if doc.endswith("spec.md"):
        if _REQ_ID.match(part):
            text = docs.text(doc)
            if text is None:
                return f"{doc} 不存在"
            if part.split("/")[-1] not in text:
                return f"{doc} 找不到 {part}"
        return None
    if doc.endswith("research.md"):
        match = _RESEARCH_SECTION.match(part)
        if match:
            headings = docs.headings(doc, ("## ",))
            if headings is None:
                return f"{doc} 不存在"
            if match.group(1).strip() not in headings:
                return f"{doc} 沒有 ## {match.group(1).strip()}"
        return None
    if doc.endswith(".dbml"):
        column, table, group = _TABLE_COLUMN.match(part), _TABLE.match(part), _TABLE_GROUP.match(part)
        if not (column or table or group):
            return None
        loaded = docs.dbml(doc)
        if loaded is None:
            return f"{doc} 不存在"
        tables, groups = loaded
        if group:
            if group.group(1) not in groups:
                return f"{doc} 沒有 TableGroup {group.group(1)}"
            if group.group(2) and group.group(2).strip() not in (docs.text(doc) or ""):
                return f"{doc} 的 TableGroup {group.group(1)} 找不到子段 {group.group(2).strip()}"
            return None
        name = (column or table).group(1)
        if name not in tables:
            return f"{doc} 沒有 Table {name}"
        if column and column.group(2) not in tables[name]:
            return f"{doc} 的 Table {name} 沒有欄位 {column.group(2)}"
        return None
    if doc.endswith("openapi.yaml"):
        schema, operation = _SCHEMA.match(part), _OPERATION.match(part)
        if operation:
            text = docs.text(doc)
            if text is None:
                return f"{doc} 不存在"
            return None if re.search(rf"operationId:\s*['\"]?{re.escape(operation.group(1))}['\"]?\s*$", text, re.M) \
                else f"{doc} 沒有 operationId {operation.group(1)}"
        if part.startswith("/") or schema:
            loaded = docs.openapi(doc)
            if loaded is None:
                return f"{doc} 不存在"
            paths, schemas = loaded
            if part.startswith("/") and part not in paths:
                return f"{doc} 的 paths 沒有 {part}"
            if schema and schema.group(1) not in schemas:
                return f"{doc} 的 components.schemas 沒有 {schema.group(1)}"
        return None
    if doc.endswith("frontend.md") or doc.endswith("plan.md") or doc.endswith("techstack.md"):
        return _check_section_part(doc, part, docs, ("## ", "### ", "#### "))
    return None


# ---------------------------------------------------------------------------------------------------------------
# Checks

def _check_header(header: dict, plan_dir: Path, structure_only: bool, violations: list[str]) -> None:
    # Title, Plan and Truth lines; the obsolete Feature Directory and Input Documents lines.
    plan = header["plan"]
    if header["title"] is None:
        violations.append("tasks.md: 檔首須為「# Tasks: <plan 目錄名>」")
    if plan is None:
        violations.append("tasks.md: 檔首須有「**Plan**: `specs/plans/<NNN>-<name>`」")
    elif not _PLAN_PATH.match(plan):
        violations.append(f"tasks.md: **Plan** `{plan}` 須為 `specs/plans/<NNN>-<name>`")
    else:
        name = plan.rsplit("/", 1)[1]
        if header["title"] is not None and header["title"] != name:
            violations.append(f"tasks.md: 標題「# Tasks: {header['title']}」須為 plan 目錄名 {name}")
        if not structure_only and name != plan_dir.resolve().name:
            violations.append(f"tasks.md: **Plan** `{plan}` 與 --plan 的目錄 {plan_dir.resolve().name} 不符")
    if header["truth"] != "specs/truth":
        violations.append("tasks.md: 檔首須有「**Truth**: `specs/truth`」")
    if header["feature_dir"]:
        violations.append("tasks.md: **Feature Directory** 已由 **Plan** 與 **Truth** 取代，刪除該行")
    if header["input_docs"]:
        violations.append("tasks.md: **Input Documents** 已廢止，刪除該行；契約文件以實際存在與否檢查")


def _endpoint_rank(endpoint: str | None) -> int:
    return _PROVIDER_RANK.get(endpoint or "", 1)


def _check_phase_order(phases: list[dict], priority: dict[int, int] | None, has_change_rows: bool | None,
                       violations: list[str]) -> None:
    # Numbering, kind order (with the replaced-DELETE exception), uniqueness, required phases, and ordering within kinds.
    by_number = {p["number"]: p for p in phases}
    last_rank, seen = -1, set()
    for index, phase in enumerate(phases, start=1):
        label = f"Phase {phase['number']}"
        if phase["number"] != index:
            violations.append(f"{label}: Phase 編號不連續，預期 Phase {index}")
        kind = phase["kind"]
        if kind is None:
            violations.append(f"{label}: 標題「{phase['title']}」不是 Setup、Foundational、Truth Impact Audit、"
                              "MODIFY <依據> › <端點>、DELETE <依據> › <端點>、`specs/truth/features/<端點>/<模組>/<檔>.feature` "
                              "(USn | 既有需求異動 #n | 全域 NFR)、NFR 重構 或 Acceptance Gates")
            continue
        rank = _RANK[kind]
        if kind == "delete" and phase["replaced_by"] is not None:
            target = by_number.get(phase["replaced_by"])
            if target is None or target["kind"] != "add":
                violations.append(f"{label}: （由 Phase {phase['replaced_by']} 取代）須指向一個 ADD Phase")
            elif phase["replaced_by"] >= phase["number"]:
                violations.append(f"{label}: 被取代的 DELETE 須排在取代它的 Phase {phase['replaced_by']} 之後")
            rank = _RANK["add"]
        if rank < last_rank or (kind not in _CHANGE_KINDS and kind in seen):
            violations.append(f"{label}: Phase 順序須為 Setup → Foundational（可省略）→ Truth Impact Audit → MODIFY → DELETE → "
                              "ADD → NFR 重構 → Acceptance Gates（被取代的 DELETE 排在取代它的 ADD 之後），且除異動 Phase 外各至多一個")
        if kind == "setup" and index != 1:
            violations.append(f"{label}: Setup 須為 Phase 1")
        seen.add(kind)
        last_rank = max(last_rank, rank)
    for kind in ("setup", "nfr", "gates"):
        if kind not in seen:
            violations.append(f"tasks.md: 缺少 {_KIND_LABEL[kind]} Phase")
    if not seen & set(_CHANGE_KINDS):
        violations.append("tasks.md: 缺少 MODIFY、DELETE 或 ADD Phase")
    if phases and phases[-1]["kind"] != "gates":
        violations.append("tasks.md: 須以 Acceptance Gates Phase 收尾")
    needs_audit = has_change_rows if has_change_rows is not None else bool(seen & {"modify", "delete"})
    if needs_audit and "audit" not in seen:
        violations.append("tasks.md: truth-delta 有 MODIFY 或 DELETE 列，須設 Truth Impact Audit Phase")
    if not needs_audit and "audit" in seen:
        violations.append("tasks.md: truth-delta 只有 ADD 列，不設 Truth Impact Audit Phase")
    if has_change_rows is not None and not has_change_rows and seen & {"modify", "delete"}:
        violations.append("tasks.md: truth-delta 沒有 MODIFY 或 DELETE 列，不設 MODIFY、DELETE Phase")

    # MODIFY: provider endpoint first within one basis; DELETE: consumer endpoint first within one basis.
    for kind, sign, word in (("modify", 1, "提供方（backend）先於使用方（frontend）"), ("delete", -1, "使用方（frontend）先於提供方（backend）")):
        last: dict[str, int] = {}
        for phase in phases:
            if phase["kind"] != kind or (kind == "delete" and phase["replaced_by"] is not None):
                continue
            rank = sign * _endpoint_rank(phase["endpoint"])
            if phase["basis"] in last and rank < last[phase["basis"]]:
                violations.append(f"Phase {phase['number']}: 同一依據「{phase['basis']}」的 {kind.upper()} Phase 須{word}")
            last[phase["basis"]] = max(rank, last.get(phase["basis"], rank))
    # ADD: story priority, (既有需求異動 #n) after stories, (全域 NFR) last; one attribution contiguous; provider first.
    seen_files: dict[str, int] = {}
    last_key: tuple | None = None
    closed: set = set()
    previous: object = "start"
    last_ep_rank = -1
    for phase in (p for p in phases if p["kind"] == "add"):
        label = f"Phase {phase['number']}"
        if phase["endpoint"] == "acceptance":
            violations.append(f"{label}: acceptance 是驗收依據，不建 ADD Phase")
        if phase["feature"] in seen_files:
            violations.append(f"{label}: `{phase['feature']}` 已在 Phase {seen_files[phase['feature']]} 出現，每個 feature 檔只占一個 ADD Phase")
        seen_files.setdefault(phase["feature"], phase["number"])
        if phase["global"]:
            group, key = "全域 NFR", (2, 0, 0)
        elif phase["change"] is not None:
            group, key = f"既有需求異動 #{phase['change']}", (1, phase["change"], 0)
        else:
            group = f"US{phase['story']}"
            key = (0, priority.get(phase["story"], 99), phase["story"]) if priority else (0, 0, 0)
        if last_key is not None and key < last_key:
            violations.append(f"{label}: ADD Phase 須依故事優先序排列，(既有需求異動 #n) 排在故事之後，(全域 NFR) 最後")
        elif group != previous and group in closed:
            violations.append(f"{label}: 同一歸屬 ({group}) 的 ADD Phase 須連續排列")
        if group != previous:
            closed.add(previous)
            last_ep_rank = -1
        rank = _endpoint_rank(phase["endpoint"])
        if rank < last_ep_rank:
            violations.append(f"{label}: 同一歸屬 ({group}) 內提供方端點（backend）的 ADD Phase 須排在使用方（frontend）之前")
        last_ep_rank = max(last_ep_rank, rank)
        last_key = key if last_key is None else max(key, last_key)
        previous = group


def _check_tasks_in_phases(phases: list[dict], plan: str | None, violations: list[str]) -> None:
    # Marker per phase kind, sentence patterns, [P] and [US] labels, and the task form of each phase kind.
    change_phases = [p for p in phases if p["kind"] in ("modify", "delete") and p["replaced_by"] is None]
    package_phase = change_phases[-1]["number"] if change_phases else None
    for phase in phases:
        kind = phase["kind"]
        label = f"Phase {phase['number']}"
        for task in phase["tasks"]:
            tid = _tid(task)
            task["step"], task["paths"], task["scopes"], task["sentence"] = None, [], [], ""
            marker = _MARKER.match(task["rest"])
            if not marker:
                violations.append(f"{tid}: 缺少步驟標記，任務描述須以 " + "、".join(f"`{m}`" for m in _MARKERS) + " 之一開頭")
                continue
            step, sentence = marker.group(1), marker.group(2)
            task["step"], task["sentence"] = step, sentence
            if kind is not None and step not in _KIND_MARKERS[kind]:
                allowed = "、".join(f"`{m}`" for m in _MARKERS if m in _KIND_MARKERS[kind])
                violations.append(f"{tid}: {_KIND_LABEL[kind]} 只放 {allowed} 任務，不放 `{step}`")
            if step == "環境" and kind in ("modify", "delete") and phase["number"] != package_phase:
                violations.append(f"{tid}: 套件移除的 `環境` 任務只放在最後一個 MODIFY、DELETE Phase（Phase {package_phase}）的末尾")
            if task["parallel"] and step not in ("環境", "基礎"):
                violations.append(f"{tid}: [P] 只用於 `環境` 與 `基礎` 任務")
            if step in _SENTENCE:
                regex, shape = _SENTENCE[step]
                match = regex.match(sentence)
                if not match:
                    violations.append(f"{tid}: {step} 句型須為「{shape}」：{sentence}")
                    continue
                if step in _SCOPED:
                    task["scopes"] = _PART.findall(match.group(1))
                    task["paths"] = _PART.findall(match.group(2))
                elif step == "移除":
                    task["paths"] = _PART.findall(match.group(2))
                else:  # 盤點
                    task["endpoint"] = match.group(1)
                    path = match.group(2).strip("`")
                    if plan and path != f"{plan}/impact-audit.md":
                        violations.append(f"{tid}: `盤點` 的產出路徑須為 `{plan}/impact-audit.md`，現為 `{path}`")
                if step in _SCOPED and kind == "add":
                    for scope in task["scopes"]:
                        if _scope_file(scope) != phase["feature"]:
                            violations.append(f"{tid}: {step} 的範疇須為本 Phase 的 `{phase['feature']}`（或其 `:行`），現為 `{scope}`")
                if step in _SCOPED and kind == "modify":
                    for scope in task["scopes"]:
                        if not scope.startswith(f"specs/truth/features/{phase['endpoint']}/"):
                            violations.append(f"{tid}: {step} 的範疇須為本 Phase 端點 {phase['endpoint']} 的 feature，現為 `{scope}`")
            elif step in ("環境", "基礎", "重構") and "於 `" in sentence and not _ENDS_WITH_PATHS.search(sentence):
                violations.append(f"{tid}: `{step}` 任務的路徑須以「於 `路徑`」收尾、多個路徑以「、」分隔：{sentence}")
            if step == "驗證":
                for ref in _PART.findall(sentence):
                    if ref.startswith("features/"):
                        violations.append(f"{tid}: `驗證` 的全套路徑須為 `specs/truth/{ref}`，現為 `{ref}`")
            if kind == "add" and phase["story"] is not None:
                if task["us"] != phase["story"]:
                    violations.append(f"{tid}: (US{phase['story']}) 的 ADD Phase 任務須標 [US{phase['story']}]")
            elif task["us"] is not None:
                violations.append(f"{tid}: 只有 (USn) ADD Phase 的任務標 [US]")
        steps = [t["step"] for t in phase["tasks"]]
        shown = "、".join(str(s) for s in steps) or "無"
        if kind == "add":
            if steps != ["/bdd red", "/bdd green", "/bdd refactor"]:
                violations.append(f"{label}: ADD Phase 須依序恰好三個任務 `/bdd red`、`/bdd green`、`/bdd refactor`，現為 {shown}")
            else:
                _check_same_scope(phase, violations)
                red, green, refactor = phase["tasks"]
                if red["paths"] and green["paths"] and refactor["paths"]:
                    expected = set(red["paths"]) | set(green["paths"])
                    got = set(refactor["paths"])
                    if got != expected:
                        missing = [p for p in green["paths"] + red["paths"] if p not in got]
                        extra = [p for p in refactor["paths"] if p not in expected]
                        detail = []
                        if missing:
                            detail.append("缺少 " + "、".join(dict.fromkeys(missing)))
                        if extra:
                            detail.append("多出 " + "、".join(dict.fromkeys(extra)))
                        violations.append(f"{_tid(refactor)}: refactor 的路徑須恰為 red 與 green 路徑的聯集：{'；'.join(detail)}")
        elif kind == "modify":
            tail = steps[3:]
            env_at = tail.index("環境") if "環境" in tail else len(tail)
            if steps[:3] != ["/bdd realign", "/bdd green", "/bdd refactor"] or any(s != "基礎" for s in tail[:env_at]) \
                    or any(s != "環境" for s in tail[env_at:]):
                violations.append(f"{label}: MODIFY Phase 須依序恰好 `/bdd realign`、`/bdd green`、`/bdd refactor`，之後只可接 `基礎`"
                                  f"（及最後的套件移除 `環境`），現為 {shown}")
            else:
                _check_same_scope(phase, violations)
        elif kind == "delete":
            removes = 0
            while removes < len(steps) and steps[removes] == "移除":
                removes += 1
            tail = steps[removes:]
            env_at = tail.index("環境") if "環境" in tail else len(tail)
            if removes == 0 or any(s != "基礎" for s in tail[:env_at]) or any(s != "環境" for s in tail[env_at:]):
                violations.append(f"{label}: DELETE Phase 須先有一個以上的 `移除`，之後只可接 `基礎`（及最後的套件移除 `環境`），現為 {shown}")
        elif kind == "audit":
            endpoints = [t.get("endpoint") for t in phase["tasks"] if t["step"] == "盤點"]
            if not endpoints:
                violations.append(f"{label}: Truth Impact Audit 須為每個受影響端點各有一個 `盤點` 任務")
            for ep in {e for e in endpoints if e and endpoints.count(e) > 1}:
                violations.append(f"{label}: 端點 {ep} 的 `盤點` 任務重複，每個端點恰好一個")
            affected = {p["endpoint"] for p in phases if p["kind"] in ("modify", "delete")}
            for ep in sorted(affected - set(endpoints)):
                violations.append(f"{label}: 缺少端點 {ep} 的 `盤點` 任務（有 {ep} 的 MODIFY 或 DELETE Phase）")
            for ep in sorted({e for e in endpoints if e} - affected):
                violations.append(f"{label}: 端點 {ep} 沒有 MODIFY 或 DELETE Phase，不設 `盤點` 任務")
        elif kind == "gates" and not phase["tasks"]:
            violations.append(f"{label}: Acceptance Gates 須至少有一個 `驗證` 任務")


def _check_same_scope(phase: dict, violations: list[str]) -> None:
    first = phase["tasks"][0]
    for task in phase["tasks"][1:3]:
        if task["scopes"] and first["scopes"] and set(task["scopes"]) != set(first["scopes"]):
            violations.append(f"{_tid(task)}: {task['step']} 的範疇須與 {_tid(first)} {first['step']} 相同")
    phase["scope"] = first["scopes"]


def _check_checkpoints(phases: list[dict], violations: list[str]) -> None:
    # Every Phase but Acceptance Gates ends with one Checkpoint; change and Audit Phases use the fixed wording.
    add_phases = [p for p in phases if p["kind"] == "add"]
    last_of_story = {}
    for p in add_phases:
        if p["story"] is not None:
            last_of_story[p["story"]] = p["number"]
    last_global = max((p["number"] for p in add_phases if p["global"]), default=None)
    first_story = min(last_of_story, default=None)
    for phase in phases:
        label = f"Phase {phase['number']}"
        points = phase["checkpoints"]
        kind = phase["kind"]
        if kind == "gates":
            if points:
                violations.append(f"{label}: Acceptance Gates 不寫 Checkpoint")
            continue
        if len(points) != 1:
            violations.append(f"{label}: 須在 Phase 末尾恰好一個 **Checkpoint**，現有 {len(points)} 個")
            continue
        text = points[0]["text"]
        if points[0]["after_tasks"] != len(phase["tasks"]):
            violations.append(f"{label}: **Checkpoint** 須在本 Phase 所有任務之後")
        if not text:
            violations.append(f"{label}: **Checkpoint** 不得為空")
            continue
        if kind == "audit" and text != _AUDIT_CHECKPOINT:
            violations.append(f"{label}: Truth Impact Audit 的 Checkpoint 須為「{_AUDIT_CHECKPOINT}」")
        if kind in ("add", "modify"):
            m = _GREEN_CHECKPOINT.match(text)
            if not m:
                violations.append(f"{label}: Checkpoint 須以「`<範疇>` 全綠；{_SUITE_TAIL}」開頭")
            elif phase.get("scope") and set(_PART.findall(m.group(1))) != set(phase["scope"]):
                violations.append(f"{label}: Checkpoint 的範疇須與本 Phase 任務的範疇相同（{'、'.join(phase['scope'])}）")
        if kind == "delete" and not _DELETE_CHECKPOINT.match(text):
            violations.append(f"{label}: DELETE Phase 的 Checkpoint 須以「`<被移除的部位>` 已無殘留的測試與產品行為；{_SUITE_TAIL}」開頭")
        cites = "Independent Test" in text
        if kind == "add" and phase["story"] is not None and last_of_story.get(phase["story"]) == phase["number"]:
            if not cites or f"使用者故事 {phase['story']}" not in text:
                violations.append(f"{label}: US{phase['story']} 最後一個 ADD Phase 的 Checkpoint 須引用 `spec.md` 使用者故事 {phase['story']} 的 Independent Test")
            elif phase["story"] == first_story and "MVP 可展示" not in text:
                violations.append(f"{label}: 第一個故事最後一個 ADD Phase 的 Checkpoint 須加「；MVP 可展示」")
        elif kind == "add" and phase["global"] and phase["number"] == last_global:
            pass
        elif cites:
            violations.append(f"{label}: 只有故事的最後一個 ADD Phase（與最後一個 (全域 NFR) Phase）引用 Independent Test")


def _entry_key_set(entries: list[tuple[str, list[str]] | None]) -> tuple[set[str], set[tuple[str, str]]]:
    whole: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for entry in entries:
        if entry is None:
            continue
        doc, parts = entry
        if not parts:
            whole.add(doc)
        pairs.update((doc, p) for p in parts)
    return whole, pairs


def _delta_parts(block: list | None) -> list[str]:
    # truth-delta.md locations cited by a shared block (full `specs/plans/.../truth-delta.md` or plan-relative).
    out = []
    for entry in block or []:
        if entry and (entry[0] == "truth-delta.md" or entry[0].endswith("/truth-delta.md")):
            out.extend(_normalize(p) for p in entry[1])
    return out


def _check_blocks_and_contracts(phases: list[dict], tasks: list[dict], docs: _Docs | None, delta: dict | None,
                                violations: list[str]) -> None:
    # Phase Must Read requirements per kind, task contract shape, no repeats of the block, red without dsl patterns,
    # Why wording, and (with real files) that every cited document and part exists.
    def check_refs(where: str, entries: list[tuple[str, list[str]] | None]) -> None:
        if docs is None:
            return
        for entry in entries:
            if entry is None:
                continue
            doc, parts = entry
            if not docs.exists(doc):
                violations.append(f"{where} `{doc}` 不存在")
                continue
            for part in parts:
                reason = _check_part(doc, part, docs)
                if reason:
                    violations.append(f"{where} `{doc}` -> `{part}`：{reason}")

    for phase in phases:
        label = f"Phase {phase['number']}"
        block = phase["block"]
        kind = phase["kind"]
        if block is not None and not block:
            violations.append(f"{label}: **Phase Must Read** 須至少一個項目；沒有內容時整段省略")
        if kind in ("add", "modify", "delete", "audit") and block is None:
            violations.append(f"{label}: {_KIND_LABEL[kind]} 須有 **Phase Must Read**")
        elif kind == "add":
            whole, pairs = _entry_key_set(block)
            if phase["feature"] not in whole:
                violations.append(f"{label}: Phase Must Read 須含 `{phase['feature']}`")
            dsl = f"specs/truth/features/{phase['endpoint']}/平臺共用/dsl.md"
            if (dsl, _DSL_APPENDIX) not in pairs:
                violations.append(f"{label}: Phase Must Read 須含 `{dsl}` -> `{_DSL_APPENDIX}`")
        elif kind in ("modify", "delete", "audit"):
            cited = _delta_parts(block)
            if not cited:
                violations.append(f"{label}: Phase Must Read 須以 `truth-delta.md` -> `<部位>` 列出本 Phase 處理的每一列")
            if kind != "audit":
                _, pairs = _entry_key_set(block)
                if not any(doc.endswith("impact-audit.md") and part == phase["endpoint"] for doc, part in pairs):
                    violations.append(f"{label}: Phase Must Read 須含 `impact-audit.md` -> `{phase['endpoint']}`")
            if delta is not None:
                wanted = {"modify": ("MODIFY",), "delete": ("DELETE",), "audit": ("MODIFY", "DELETE")}[kind]
                rows = {r["location"]: r["action"] for section in delta.values() for r in section}
                for part in cited:
                    if part in rows and rows[part] not in wanted:
                        violations.append(f"{label}: truth-delta 的 `{part}` 是 {rows[part]} 列，不放在 {_KIND_LABEL[kind]}")
                if kind == "audit":
                    for section in delta.values():
                        for row in section:
                            if row["action"] in wanted and row["location"] not in cited:
                                violations.append(f"{label}: Phase Must Read 缺少 truth-delta 的 {row['action']} 列 `{row['location']}`")
        check_refs(f"{label}: Phase Must Read", block or [])

    for index, task in enumerate(tasks, start=1):
        tid = _tid(task)
        if task["id"] != index:
            violations.append(f"{tid}: 編號不連續，預期 T{index:03d}")
        if "Why" not in task["sections"]:
            violations.append(f"{tid}: 缺少 Why")
        block_whole, block_pairs = _entry_key_set(task["phase"]["block"] or [])
        for label in ("Must Read", "Optional"):
            if label not in task["sections"]:
                continue
            entries = task["entries"].get(label, [])
            if not entries:
                violations.append(f"{tid}: {label} 須至少一個項目；沒有內容時整段省略")
            for entry in entries:
                if entry is None:
                    continue
                doc, parts = entry
                if doc in block_whole:
                    violations.append(f"{tid}: {label} `{doc}` 已在 Phase Must Read 列出整份，不重複列")
                    continue
                for part in parts:
                    if (doc, part) in block_pairs:
                        violations.append(f"{tid}: {label} `{doc}` -> `{part}` 已在 Phase Must Read 列出，不重複列")
                if task.get("step") == "/bdd red" and doc.endswith("/dsl.md"):
                    if not parts:
                        violations.append(f"{tid}: red 的 {label} 不列 `{doc}` 整份；句型由 Phase 的 feature 檔決定")
                    for part in parts:
                        if part != _DSL_APPENDIX:
                            violations.append(f"{tid}: red 的 {label} 不列 dsl.md 句型 `{part}`；dsl.md 只引 `{_DSL_APPENDIX}`")
            check_refs(f"{tid}: {label}", entries)
        why = task.get("why")
        if why is not None:
            if not why:
                violations.append(f"{tid}: Why 不得為空")
            if "`" in why:
                violations.append(f"{tid}: Why 含程式識別碼：{why}")
            # A semicolon joins clauses of one sentence; only a second full stop starts another sentence.
            if why.count("。") >= 2 or (why.count("。") == 1 and not why.endswith("。")):
                violations.append(f"{tid}: Why 超過一句：{why}")


def _check_scope_lines(phases: list[dict], docs: _Docs, violations: list[str]) -> None:
    # Every scope file exists; every `:line` points at an Example header line of that file.
    for phase in phases:
        for task in phase["tasks"]:
            for scope in task.get("scopes", []):
                path = docs.path(scope)
                if not path.is_file():
                    violations.append(f"{_tid(task)}: 範疇 `{_scope_file(scope)}` 不存在")
                    continue
                m = re.search(r":(\d+)$", scope)
                if m:
                    _, lines = _example_lines("", path.read_text(encoding="utf-8"))
                    if int(m.group(1)) not in lines:
                        violations.append(f"{_tid(task)}: 範疇 `{scope}` 的行號不是 Example 的標題行")


def _check_coverage(phases: list[dict], tasks: list[dict], delta: dict[str, list[dict]], root: Path,
                    violations: list[str]) -> None:
    # Tasks format spec §6: every truth-delta row is covered by the phase or task its section requires.
    add_files = {p["feature"]: p for p in phases if p["kind"] == "add"}
    cited = {kind: set() for kind in ("modify", "delete")}
    for phase in phases:
        if phase["kind"] in cited:
            cited[phase["kind"]].update(_delta_parts(phase["block"]))
    added: set[str] = set()
    for row in delta["features"]:
        path = row["location"].split(" › ", 1)[0]
        if row["action"] == "ADD":
            if path.endswith(".feature"):
                feature = f"specs/truth/features/{path}"
                added.add(feature)
                if feature not in add_files:
                    violations.append(f"truth-delta features ADD `{row['location']}`：缺少以 `{feature}` 為標題的 ADD Phase")
            continue
        kind = row["action"].lower()
        if row["location"] not in cited[kind]:
            violations.append(f"truth-delta features {row['action']} `{row['location']}`：沒有 {row['action']} Phase 在 Phase Must Read 列出此部位")
        if kind == "modify" and path.endswith(".feature") and " › " in row["location"]:
            feature = f"specs/truth/features/{path}"
            file = root / feature
            if not file.is_file():
                continue
            keys, _ = _example_lines(path, file.read_text(encoding="utf-8"))
            line = keys.get(row["location"])
            if line is None:
                continue
            scopes = {s for p in phases if p["kind"] == "modify" and row["location"] in _delta_parts(p["block"])
                      for s in p.get("scope", [])}
            if f"{feature}:{line}" not in scopes and feature not in scopes:
                violations.append(f"truth-delta features MODIFY `{row['location']}`：列出它的 MODIFY Phase 範疇須含 `{feature}:{line}`")
    for feature, phase in add_files.items():
        if feature not in added:
            violations.append(f"Phase {phase['number']}: `{feature}` 在 truth-delta 沒有 ADD 列，不建 ADD Phase")
    env = [t["sentence"] for t in tasks if t.get("step") == "環境"]
    for row in delta["techstack"]:
        name = row["location"].split(" / ", 1)[-1].strip()
        if not any(name in s for s in env):
            violations.append(f"truth-delta techstack {row['action']} `{row['location']}`：沒有 `環境` 任務的句子包含 {name}")
    for row in delta["data"]:
        m = re.search(r" › (?:Table|Enum|TableGroup) \"?([^\s.\"]+)", row["location"])
        if not m:
            continue
        name = m.group(1)
        want = ("foundational",) if row["action"] == "ADD" else ("modify", "delete")
        found = [t for t in tasks if t.get("step") == "基礎" and name in t["sentence"] and t["phase"]["kind"] in want]
        if not found:
            where = "Foundational" if row["action"] == "ADD" else "MODIFY 或 DELETE Phase"
            violations.append(f"truth-delta data {row['action']} `{row['location']}`：{where} 沒有 `基礎` 任務的句子包含 {name}")


def _check_nfr_table(phases: list[dict], nfr_ids: list[str] | None, prefix: str | None, violations: list[str]) -> None:
    # The NFR 重構 verdict table: every required NFR once, a valid verdict, and every 重構 task referenced.
    def norm(nfr: str) -> str:
        return nfr.split("/", 1)[1] if prefix and nfr.startswith(prefix + "/") else nfr

    for phase in phases:
        if phase["kind"] != "nfr":
            continue
        label = f"Phase {phase['number']}"
        found, rows = _table_after(phase["lines"], _NFR_HEADER)
        if not found:
            violations.append(f"{label}: NFR 重構須有判定表，表頭為「| NFR | 驗證來源 | 判定 |」")
            continue
        refactors = {_tid(t): t for t in phase["tasks"] if t.get("step") == "重構"}
        referenced: set[str] = set()
        counts: dict[str, int] = {}
        for cells in rows:
            if len(cells) != 3:
                violations.append(f"{label}: NFR 判定表每列須有 3 欄：| {' | '.join(cells)} |")
                continue
            nfr, source, verdict = cells
            if not _NFR_ID.match(nfr):
                violations.append(f"{label}: NFR 判定表的 NFR 欄須為 NFR-nnn 或 <NNN>/NFR-nnn：{nfr}")
                continue
            counts[norm(nfr)] = counts.get(norm(nfr), 0) + 1
            if not source:
                violations.append(f"{label}: {nfr} 的驗證來源不得為空")
            listed = _NFR_LIST.match(verdict)
            if verdict == "已由 feature 驗證":
                continue
            if verdict.startswith("不需任務："):
                if not verdict[len("不需任務："):].strip():
                    violations.append(f"{label}: {nfr} 的判定「不需任務：」後須寫理由")
                continue
            if listed:
                for ref in listed.group(1).split("、"):
                    referenced.add(ref)
                    if ref not in refactors:
                        violations.append(f"{label}: {nfr} 的判定 {verdict} 指向的 {ref} 不是本 Phase 的 `重構` 任務")
                continue
            violations.append(f"{label}: {nfr} 的判定須為「已由 feature 驗證」、「不需任務：<理由>」或「列 Txxx」：{verdict}")
        for nfr, count in counts.items():
            if count > 1:
                violations.append(f"{label}: {nfr} 在判定表出現 {count} 次，每條 NFR 恰好一列")
        if nfr_ids is not None:
            required = [norm(n) for n in nfr_ids]
            for nfr in required:
                if nfr not in counts:
                    violations.append(f"{label}: 判定表缺少 {nfr}（本 plan spec.md 的 NFR 或被 MODIFY 的 NFR）")
            for nfr in counts:
                if nfr not in required:
                    violations.append(f"{label}: 判定表的 {nfr} 不是本 plan spec.md 的 NFR，也不是被 MODIFY 的 NFR")
        for tid in refactors:
            if tid not in referenced:
                violations.append(f"{tid}: `重構` 任務須被 NFR 判定表至少一列以「列 {tid}」引用")


def _check_trailing(header: dict, phases: list[dict], violations: list[str]) -> None:
    # Dependencies & Execution Order (with its four subsections and Feature Dependencies table) and Parallel Example.
    lines = [line for _, line in header["trailing"]]
    deps_at = next((i for i, line in enumerate(lines) if line.strip() == _DEPS_HEAD), None)
    par_at = next((i for i, line in enumerate(lines) if _PARALLEL_HEAD.match(line)), None)
    if deps_at is None:
        violations.append(f"tasks.md: Acceptance Gates 之後須有「{_DEPS_HEAD}」")
    else:
        end = par_at if par_at is not None and par_at > deps_at else len(lines)
        section = lines[deps_at + 1:end]
        positions = []
        for sub in _DEPS_SUBSECTIONS:
            at = next((i for i, line in enumerate(section) if line.strip() == sub), None)
            if at is None:
                violations.append(f"Dependencies: 缺少「{sub}」")
            positions.append(at)
        present = [p for p in positions if p is not None]
        if present != sorted(present):
            violations.append("Dependencies: 小節順序須為 " + " → ".join(s[4:] for s in _DEPS_SUBSECTIONS))
        fd_at = positions[1]
        if fd_at is not None:
            following = [p for p in positions if p is not None and p > fd_at]
            body = section[fd_at + 1:min(following) if following else len(section)]
            _check_feature_deps(body, phases, violations)
    if par_at is None:
        violations.append("tasks.md: Dependencies & Execution Order 之後須有「## Parallel Example: <標題>」")
    else:
        if deps_at is not None and par_at < deps_at:
            violations.append("tasks.md: Parallel Example 須排在 Dependencies & Execution Order 之後")
        if not _PARALLEL_HEAD.match(lines[par_at]).group(1).strip():
            violations.append("Parallel Example: 標題不得為空")
        rest = lines[par_at + 1:]
        opening = next((i for i, line in enumerate(rest) if line.strip().startswith("```")), None)
        if opening is None or rest[opening].strip() != "```text":
            violations.append("Parallel Example: 須有 ```text 程式碼區塊")
        elif not any(line.strip() == "```" for line in rest[opening + 1:]):
            violations.append("Parallel Example: ```text 區塊未以 ``` 結束")
    for line in lines:
        if line.startswith("## ") and line.strip() != _DEPS_HEAD and not _PARALLEL_HEAD.match(line):
            violations.append(f"tasks.md: Acceptance Gates 之後只放 Dependencies & Execution Order 與 Parallel Example：{line.strip()}")


def _check_feature_deps(body: list[str], phases: list[dict], violations: list[str]) -> None:
    # One row per MODIFY, DELETE and ADD Phase with its feature files; dependencies are earlier phases or —.
    found, rows = _table_after(body, _FEATURE_DEPS_HEADER)
    if not found:
        violations.append("Dependencies: Feature Dependencies 須有表格，表頭為「| Phase | feature | 依賴 Phase | 依據 |」")
        return
    by_number = {p["number"]: p for p in phases}
    change = {n: p for n, p in by_number.items() if p["kind"] in _CHANGE_KINDS}
    targets = {n for n, p in by_number.items() if p["kind"] in ("foundational", "audit", *_CHANGE_KINDS)}
    seen: dict[int, int] = {}
    for cells in rows:
        if len(cells) != 4:
            violations.append(f"Dependencies: Feature Dependencies 每列須有 4 欄：| {' | '.join(cells)} |")
            continue
        number, feature, deps, basis = cells
        if not number.isdigit() or int(number) not in change:
            violations.append(f"Dependencies: Feature Dependencies 的 Phase 欄 {number} 不是 MODIFY、DELETE 或 ADD Phase")
            continue
        n = int(number)
        phase = change[n]
        seen[n] = seen.get(n, 0) + 1
        files = _PART.findall(feature)
        if phase["kind"] == "add" and files != [phase["feature"]]:
            violations.append(f"Dependencies: Phase {n} 的 feature 欄須為 `{phase['feature']}`，現為 {feature}")
        elif phase["kind"] != "add":
            if not files or not all(re.fullmatch(r"specs/truth/features/[^`]+\.feature", f) for f in files):
                violations.append(f"Dependencies: Phase {n} 的 feature 欄須為以「、」分隔的 `specs/truth/features/…feature`，現為 {feature}")
            elif phase["kind"] == "modify" and phase.get("scope") and set(files) != {_scope_file(s) for s in phase["scope"]}:
                violations.append(f"Dependencies: Phase {n} 的 feature 欄須為本 Phase 範疇的 feature 檔（"
                                  + "、".join(sorted({_scope_file(s) for s in phase['scope']})) + "）")
        dep_numbers = []
        if deps != "—":
            for dep in deps.split("、"):
                dep = dep.strip()
                if not dep.isdigit() or int(dep) not in targets:
                    violations.append(f"Dependencies: Phase {n} 的依賴 {dep} 不是 Truth Impact Audit、MODIFY、DELETE 或 ADD Phase；"
                                      "依賴欄寫 — 或以「、」分隔的 Phase 編號")
                elif int(dep) >= n:
                    violations.append(f"Dependencies: Phase {n} 依賴的 Phase {dep} 須排在它之前")
                else:
                    dep_numbers.append(int(dep))
        if phase["kind"] == "delete" and phase["replaced_by"] is not None and phase["replaced_by"] not in dep_numbers:
            violations.append(f"Dependencies: 被取代的 Phase {n} 須依賴取代它的 Phase {phase['replaced_by']}")
        if not basis:
            violations.append(f"Dependencies: Phase {n} 的依據不得為空")
    for n in change:
        if seen.get(n, 0) != 1:
            violations.append(f"Dependencies: Feature Dependencies 須對 Phase {n} 恰好一列，現有 {seen.get(n, 0)} 列")


def _find_root(start: Path) -> Path | None:
    for p in [start, *start.parents]:
        if (p / "specs" / "truth").is_dir():
            return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a tasks.md (v2) against its plan's truth-delta.md: header, phase kinds and order, task forms, markers, checkpoints, shared blocks, contracts, NFR table, dependencies and truth-delta coverage."
    )
    parser.add_argument("--tasks", required=True, help="Path to the tasks.md to check")
    parser.add_argument("--plan", required=True, help="Plan package directory holding truth-delta.md, spec.md and plan.md (specs/plans/NNN-name)")
    parser.add_argument("--structure-only", action="store_true",
                        help="Skip every check that needs real files (truth-delta coverage, spec.md stories and NFR ids, "
                             "existence of cited documents, parts and scope lines)")
    args = parser.parse_args()
    tasks_path = Path(args.tasks)
    plan_dir = Path(args.plan)
    if not tasks_path.is_file():
        sys.stderr.write(f"error: '{tasks_path}' is not a file; pass the path to the generated tasks.md\n")
        return 2
    priority: dict[int, int] | None = None
    nfr_ids: list[str] | None = None
    delta: dict[str, list[dict]] | None = None
    docs: _Docs | None = None
    root: Path | None = None
    prefix_m = re.match(r"^(\d{3})-", plan_dir.resolve().name)
    prefix = prefix_m.group(1) if prefix_m else None
    if not args.structure_only:
        if not plan_dir.is_dir():
            sys.stderr.write(f"error: '{plan_dir}' is not a directory; pass the specs/plans/<NNN>-<name> directory or add --structure-only\n")
            return 2
        root = _find_root(plan_dir.resolve())
        if root is None:
            sys.stderr.write(f"error: no specs/truth/ above '{plan_dir}'; pass a plan directory inside the repository\n")
            return 2
        delta_path, spec_path = plan_dir / "truth-delta.md", plan_dir / "spec.md"
        if not delta_path.is_file():
            sys.stderr.write(f"error: '{delta_path}' not found; create it with the truth-delta skill before /tasks\n")
            return 2
        if not spec_path.is_file():
            sys.stderr.write(f"error: '{spec_path}' not found; run /specify first\n")
            return 2
        delta = _delta_rows(delta_path.read_text(encoding="utf-8"))
        spec_text = spec_path.read_text(encoding="utf-8")
        priority = _parse_spec(spec_text)
        nfr_ids = list(dict.fromkeys(_NFR_BOLD.findall(spec_text)))
        nfr_ids += [r["location"] for r in delta["requirements"] if r["action"] == "MODIFY" and "/NFR-" in r["location"]]
        locations = {r["location"] for section in delta.values() for r in section}
        docs = _Docs(plan_dir.resolve(), root, locations)
    violations: list[str] = []
    tasks, phases, header = _parse_tasks(tasks_path.read_text(encoding="utf-8"), violations)
    if not tasks:
        sys.stderr.write(f"error: no task lines like '- [ ] T001 ...' found in '{tasks_path}'\n")
        return 2
    has_change_rows = None if delta is None else any(r["action"] in ("MODIFY", "DELETE") for s in delta.values() for r in s)
    plan_header = header["plan"] if header["plan"] and _PLAN_PATH.match(header["plan"]) else None
    _check_header(header, plan_dir, args.structure_only, violations)
    _check_phase_order(phases, priority, has_change_rows, violations)
    _check_tasks_in_phases(phases, plan_header, violations)
    _check_checkpoints(phases, violations)
    _check_blocks_and_contracts(phases, tasks, docs, delta, violations)
    _check_nfr_table(phases, nfr_ids, prefix, violations)
    _check_trailing(header, phases, violations)
    if docs is not None and delta is not None and root is not None:
        _check_scope_lines(phases, docs, violations)
        _check_coverage(phases, tasks, delta, root, violations)
    if not violations:
        sys.stdout.write("OK\n")
        return 0
    sys.stdout.write("\n".join(violations) + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
