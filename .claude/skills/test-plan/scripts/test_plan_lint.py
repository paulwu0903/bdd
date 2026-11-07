# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List structural, identifier and coverage violations of a test-plan.md written from the test-plan skill's template.

Usage:
    uv run scripts/test_plan_lint.py --plan <test-plan.md> --spec <spec.md> --system-plan <plan.md>
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


NFR_TYPE = "NFR 量測"
JOURNEY_TYPE = "旅程（預期不先紅）"
CASE_TYPES = {"TDD Slice", "防回歸（預期不先紅）", JOURNEY_TYPE, NFR_TYPE}
FIELDS_BEFORE_MEASURE = [
    "案例類型", "觀察 seam", "涉及系統介面", "測試名稱", "對應需求", "唯一測試意圖", "測試檔", "受測部位", "受測操作",
]
FIELDS_AFTER_MEASURE = ["前置條件", "建立方式", "要抓的錯誤實作", "主要 oracle", "必須維持不變", "本案例不驗證"]
MEASURE_FIELD = "量測條件"
COMPARATORS = (
    "不等於", "等於", "不包含", "包含", "屬於", "數量為", "符合", "可見", "停用", "可用", "至少", "至多",
)
FIXTURE_HEADER = "| Fixture | 前置狀態 | 建立步驟 | 就緒條件 | Helper |"
CHANGE_HEADER = "| 日期 | 案例 | 變更 | 原因 | 依據 |"
GAP_STATUSES = {"未涵蓋", "部分涵蓋"}
STORY_HEAD = re.compile(r"^## User Story (\d+) - .+$")
CROSS_STORY = "## 跨故事旅程"
GLOBAL_NFR = "## 全域 NFR"
CARD_HEAD = re.compile(r"^### SL-(\d{3}) - .+$")
SEAM_HEAD = re.compile(r"^### (\S+) seam$")
FIXTURE_ROW = re.compile(r"^\| ([A-Za-z0-9]+)-FX-([A-Z0-9-]+) \|")
FIXTURE_REF = re.compile(r"\b[A-Za-z0-9]+-FX-[A-Z0-9-]+\b")
FIELD_LINE = re.compile(r"^- \*\*(.+?)\*\*: ?(.*)$")
SPEC_ID = re.compile(r"\b(?:FR|NFR|SC)-\d{3}\b")
SCENARIO_REF = re.compile(r"\bUS(\d+)-(\d+)\b")


def split_sections(lines: list[str]) -> list[tuple[int, str, list[tuple[int, str]]]]:
    """Group numbered lines under their '## ' heading."""
    groups: list[tuple[int, str, list[tuple[int, str]]]] = []
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            groups.append((n, line, []))
        elif groups:
            groups[-1][2].append((n, line))
    return groups


def check_order(lines: list[str], sections, out: list[str]) -> None:
    # Expected order: Fixtures, User Story sections, optional cross-story and global NFR, gaps, changes.
    if not lines or not re.match(r"^# 測試計畫：.+$", lines[0]):
        out.append("line 1: first line must be '# 測試計畫：<feature name>'")
    rank = {"## Fixtures": 0, CROSS_STORY: 2, GLOBAL_NFR: 3, "## 未涵蓋項目": 4, "## 變更紀錄": 5}
    seen: dict[str, int] = {}
    last_rank, last_story = -1, 0
    for n, heading, _ in sections:
        m = STORY_HEAD.match(heading)
        r = 1 if m else rank.get(heading)
        if r is None:
            out.append(f"line {n}: unexpected section '{heading}'")
            continue
        if not m:
            seen[heading] = seen.get(heading, 0) + 1
            if seen[heading] > 1:
                out.append(f"line {n}: section '{heading}' appears more than once")
        if r < last_rank:
            out.append(f"line {n}: section '{heading}' is out of order "
                       "(Fixtures, User Story…, 跨故事旅程, 全域 NFR, 未涵蓋項目, 變更紀錄)")
        if m:
            story = int(m.group(1))
            if story <= last_story:
                out.append(f"line {n}: User Story sections must follow the spec order without repeats")
            last_story = story
        last_rank = max(last_rank, r)
    for required in ("## Fixtures", "## 未涵蓋項目", "## 變更紀錄"):
        if required not in seen:
            out.append(f"missing section '{required}'")
    if not any(STORY_HEAD.match(h) for _, h, _ in sections):
        out.append("plan needs at least one '## User Story N - <title>' section")


def parse_fixtures(section, out: list[str]) -> dict[str, str]:
    """Return {fixture id: seam} and check per-seam tables and naming."""
    fixtures: dict[str, str] = {}
    if section is None:
        return fixtures
    seam, has_header = None, False
    for n, line in section[2]:
        m = SEAM_HEAD.match(line)
        if m:
            if seam is not None and not has_header:
                out.append(f"'### {seam} seam' needs the table header '{FIXTURE_HEADER}'")
            seam, has_header = m.group(1), False
            continue
        if line.startswith("### "):
            out.append(f"line {n}: Fixtures subsections must read '### <seam> seam'")
            continue
        if line == FIXTURE_HEADER:
            has_header = True
        f = FIXTURE_ROW.match(line)
        if f:
            fid = f"{f.group(1)}-FX-{f.group(2)}"
            if seam is None:
                out.append(f"line {n}: fixture {fid} must sit under a '### <seam> seam' subsection")
            elif f.group(1) != seam.upper():
                out.append(f"line {n}: fixture {fid} under '{seam} seam' must be named '{seam.upper()}-FX-<STATE>'")
            if fid in fixtures:
                out.append(f"line {n}: fixture {fid} is defined twice")
            fixtures[fid] = seam or ""
    if seam is not None and not has_header:
        out.append(f"'### {seam} seam' needs the table header '{FIXTURE_HEADER}'")
    if seam is None:
        out.append(f"line {section[0]}: '## Fixtures' needs at least one '### <seam> seam' table")
    return fixtures


def parse_cards(section, out: list[str]) -> list[dict]:
    """Return the cards ({num, line, fields, values, oracles, body}) of one case section."""
    cards: list[dict] = []
    current, field = None, None
    for n, line in section[2]:
        m = CARD_HEAD.match(line)
        if m:
            current = {"num": int(m.group(1)), "id": f"SL-{m.group(1)}", "line": n, "section": section[1],
                       "fields": [], "values": {}, "oracles": [], "body": []}
            cards.append(current)
            field = None
            continue
        if line.startswith("### ") or line.startswith("#### "):
            out.append(f"line {n}: card headings must read '### SL-NNN - <title>'")
            current = None
            continue
        if current is None:
            continue
        current["body"].append((n, line))
        f = FIELD_LINE.match(line)
        if f:
            field = f.group(1)
            current["fields"].append(field)
            current["values"][field] = f.group(2)
        elif line.startswith("  - ") and field == "主要 oracle":
            current["oracles"].append((n, line[4:]))
    if not cards:
        out.append(f"line {section[0]}: '{section[1]}' has no '### SL-NNN - <title>' card")
    return cards


def check_card(c: dict, seams: set[str], interfaces: set[str], case_ids: set[str], out: list[str]) -> None:
    where = f"line {c['line']} ({c['id']})"
    v = c["values"]
    ctype = v.get("案例類型")
    is_nfr = ctype == NFR_TYPE
    expected = FIELDS_BEFORE_MEASURE + ([MEASURE_FIELD] if is_nfr else []) + FIELDS_AFTER_MEASURE
    if c["fields"] != expected:
        if not is_nfr and MEASURE_FIELD in c["fields"]:
            out.append(f"{where}: {MEASURE_FIELD} is only allowed on '{NFR_TYPE}' cards")
        out.append(f"{where}: fields must be exactly {', '.join(expected)} in that order")
    if ctype is not None and ctype not in CASE_TYPES:
        out.append(f"{where}: 案例類型 must be one of {', '.join(sorted(CASE_TYPES))}")
    seam = v.get("觀察 seam", "").strip()
    if seam and seam not in seams:
        out.append(f"{where}: 觀察 seam '{seam}' has no '### {seam} seam' table in Fixtures")
    named = re.findall(r"`([^`]+)`", v.get("涉及系統介面", ""))
    if "涉及系統介面" in v and not named:
        out.append(f"{where}: 涉及系統介面 must list backticked interface names from plan.md")
    for name in named:
        if name not in interfaces:
            out.append(f"{where}: 涉及系統介面 '{name}' is not in plan.md '### 系統介面的盤點'")
    name = v.get("測試名稱", "")
    if not re.match(rf"^`(test_sl_{c['num']:03d}_\w+|{c['id']} .+)`$", name):
        out.append(f"{where}: 測試名稱 must carry the case id (`test_sl_{c['num']:03d}_...` or `{c['id']} ...`)")
    for field in expected:
        if field != "主要 oracle" and field in v and not v[field].strip():
            out.append(f"{where}: {field} is empty")
    if not c["oracles"]:
        out.append(f"{where}: 主要 oracle needs at least one item")
    for n, oracle in c["oracles"]:
        observer, sep, claim = oracle.partition("：")
        if not sep or not observer.strip():
            out.append(f"line {n} ({c['id']}): oracle must start with '<observer>…：' before the claim")
        elif not any(word in claim for word in COMPARATORS):
            out.append(f"line {n} ({c['id']}): oracle claim after '：' uses no allowed comparator ({'、'.join(COMPARATORS)})")
        if "或" in oracle:
            out.append(f"line {n} ({c['id']}): oracle must be deterministic; '或' is not allowed")
        # NFR cards carry their start and end points in 量測條件 instead of each oracle.
        if not is_nfr and re.search(r"\d+(?:\.\d+)? 秒內", oracle) and not re.search(r"（自.+起算）", oracle):
            out.append(f"line {n} ({c['id']}): time threshold needs a start point '（自…起算）'")
    for n, line in c["body"]:
        for other in re.findall(r"\bSL-\d{3}\b", line):
            if other in case_ids and other != c["id"]:
                out.append(f"line {n} ({c['id']}): card must not reference another card ({other})")


def parse_spec(spec_lines: list[str]):
    """Collect FR/NFR (with the user stories they belong to), SC ids, global ids and scenario counts per user story."""
    owner: dict[str, set[int] | None] = {}
    global_ids: set[str] = set()
    scenarios: dict[int, int] = {}
    story = None
    for line in spec_lines:
        m = re.match(r"^### User Story (\d+) - ", line)
        if m:
            story = int(m.group(1))
            scenarios[story] = 0
            continue
        if line.startswith("### Edge Cases") or line.startswith("## "):
            story = None
        if story is not None and re.match(r"^\d+\. \*\*Given\*\*", line):
            scenarios[story] += 1
        m = re.match(r"^- \*\*((?:FR|NFR|SC)-\d{3})\*\*(?:（適用：([^）]+)）)?", line)
        if m:
            applies = {int(x) for x in re.findall(r"US(\d+)", m.group(2) or "")}
            owner[m.group(1)] = {story} if story is not None else (applies or None)
            if story is None:
                global_ids.add(m.group(1))
    return owner, global_ids, scenarios


def check_placement(c: dict, global_ids: set[str], out: list[str]) -> None:
    # Journey and NFR cards must sit in the section that matches the scope of what they cite.
    where = f"line {c['line']} ({c['id']})"
    ctype = c["values"].get("案例類型")
    source = c["values"].get("對應需求", "")
    stories = {int(us) for us, _ in SCENARIO_REF.findall(source)}
    nfrs = [sid for sid in SPEC_ID.findall(source) if sid.startswith("NFR-")]
    m = STORY_HEAD.match(c["section"])
    if c["section"] == CROSS_STORY:
        if ctype != JOURNEY_TYPE:
            out.append(f"{where}: '{CROSS_STORY}' may only hold '{JOURNEY_TYPE}' cards")
        elif len(stories) < 2:
            out.append(f"{where}: a cross-story journey must cite scenarios of at least two user stories")
    elif c["section"] == GLOBAL_NFR:
        if ctype != NFR_TYPE:
            out.append(f"{where}: '{GLOBAL_NFR}' may only hold '{NFR_TYPE}' cards")
        elif not any(sid in global_ids for sid in nfrs):
            out.append(f"{where}: cards in '{GLOBAL_NFR}' must cite a global NFR")
    elif m:
        story = int(m.group(1))
        if ctype == JOURNEY_TYPE and stories - {story}:
            out.append(f"{where}: a journey citing other user stories belongs in '{CROSS_STORY}'")
        if ctype == NFR_TYPE and nfrs and all(sid in global_ids for sid in nfrs):
            out.append(f"{where}: an NFR card citing only global NFRs belongs in '{GLOBAL_NFR}'")


def check_coverage(stories_in_plan: set[int], cards, gaps, owner, scenarios, out: list[str]) -> None:
    by_card: set[str] = set()
    for c in cards:
        source = c["values"].get("對應需求", "")
        for sid in SPEC_ID.findall(source):
            if sid not in owner:
                out.append(f"line {c['line']} ({c['id']}): 對應需求 cites {sid}, which is not in the spec")
            by_card.add(sid)
        for us, num in SCENARIO_REF.findall(source):
            if int(num) > scenarios.get(int(us), 0):
                out.append(f"line {c['line']} ({c['id']}): 對應需求 cites US{us}-{num}, which is not in the spec")
            by_card.add(f"US{us}-{num}")
    by_gap: set[str] = set()
    if gaps is not None:
        for n, line in gaps[2]:
            if not line.strip():
                continue
            m = re.match(r"^- \*\*(.+?)\*\*（(.+?)）：.+$", line)
            if not m or m.group(2) not in GAP_STATUSES:
                out.append(f"line {n}: 未涵蓋項目 must read '- **<spec item>**（未涵蓋|部分涵蓋）：<reason>'")
                continue
            if m.group(2) == "未涵蓋" and not m.group(1).startswith("SC-"):
                out.append(f"line {n}: only SC items needing a human may be '未涵蓋'; {m.group(1)} needs a card")
            by_gap.add(m.group(1))
    for story in sorted(stories_in_plan):
        if story not in scenarios:
            out.append(f"'## User Story {story}' is not a user story in the spec")
    for sid, stories in sorted(owner.items()):
        if sid.startswith("SC-"):
            if sid not in by_card and sid not in by_gap:
                out.append(f"{sid} is neither cited by any card nor listed in 未涵蓋項目")
            continue
        relevant = stories is None or bool(stories & stories_in_plan)
        if relevant and sid not in by_card:
            out.append(f"{sid} is not cited by any card; every in-scope FR and NFR needs a card")
    for us in sorted(stories_in_plan):
        for num in range(1, scenarios.get(us, 0) + 1):
            if f"US{us}-{num}" not in by_card:
                out.append(f"US{us}-{num} is not cited by any card")


def parse_interfaces(system_lines: list[str]) -> set[str] | None:
    """Return backticked interface names listed under '### 系統介面的盤點', or None if the heading is absent."""
    names: set[str] = set()
    inside = False
    for line in system_lines:
        if re.match(r"^#{1,3} ", line):
            inside = line.strip() == "### 系統介面的盤點"
            continue
        if inside:
            m = re.match(r"^\d+\. `([^`]+)`", line)
            if m:
                names.add(m.group(1))
    found = any(line.strip() == "### 系統介面的盤點" for line in system_lines)
    return names if found else None


def main() -> int:
    parser = argparse.ArgumentParser(description="List structural, identifier and coverage violations of a test-plan.md.")
    parser.add_argument("--plan", required=True, help="Path to the test-plan.md to check")
    parser.add_argument("--spec", required=True, help="Path to the spec.md the plan is derived from")
    parser.add_argument("--system-plan", required=True, help="Path to the plan.md holding '### 系統介面的盤點'")
    args = parser.parse_args()
    paths = ((Path(args.plan), "--plan"), (Path(args.spec), "--spec"), (Path(args.system_plan), "--system-plan"))
    for path, flag in paths:
        if not path.is_file():
            sys.stderr.write(f"error: '{path}' is not a file; pass {flag} <feature dir>/{path.name or '...'}\n")
            return 2
    lines = paths[0][0].read_text(encoding="utf-8").splitlines()
    spec_lines = paths[1][0].read_text(encoding="utf-8").splitlines()
    interfaces = parse_interfaces(paths[2][0].read_text(encoding="utf-8").splitlines())
    if interfaces is None:
        sys.stderr.write(f"error: '{args.system_plan}' has no '### 系統介面的盤點'; run /system-analysis first or pass the right plan.md\n")
        return 2
    out: list[str] = []
    for n, line in enumerate(lines, 1):
        if "{{" in line or "}}" in line:
            out.append(f"line {n}: unfilled placeholder remains")
    sections = split_sections(lines)
    check_order(lines, sections, out)
    by_name = {h: s for s in sections for h in [s[1]]}
    fixtures = parse_fixtures(by_name.get("## Fixtures"), out)
    case_sections = [s for s in sections if STORY_HEAD.match(s[1]) or s[1] in (CROSS_STORY, GLOBAL_NFR)]
    cards = [c for s in case_sections for c in parse_cards(s, out)]
    nums = [c["num"] for c in cards]
    if nums != list(range(1, len(nums) + 1)):
        out.append("SL- case ids must run 001, 002, ... across the whole file without gaps, duplicates or reordering")
    case_ids = {c["id"] for c in cards}
    seams = set(fixtures.values())
    owner, global_ids, scenarios = parse_spec(spec_lines)
    for c in cards:
        check_card(c, seams, interfaces, case_ids, out)
        check_placement(c, global_ids, out)
    for n, line in enumerate(lines, 1):
        for fx in FIXTURE_REF.findall(line):
            if fx not in fixtures:
                out.append(f"line {n}: fixture {fx} is not defined in any Fixtures table")
    stories_in_plan = {int(STORY_HEAD.match(s[1]).group(1)) for s in case_sections if STORY_HEAD.match(s[1])}
    check_coverage(stories_in_plan, cards, by_name.get("## 未涵蓋項目"), owner, scenarios, out)
    changes = by_name.get("## 變更紀錄")
    if changes is not None and CHANGE_HEADER not in [line for _, line in changes[2]]:
        out.append(f"line {changes[0]}: '## 變更紀錄' needs the table header '{CHANGE_HEADER}'")
    if out:
        sys.stdout.write("\n".join(out) + "\n")
        return 1
    sys.stdout.write(f"OK: no violations ({len(cards)} cases)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
