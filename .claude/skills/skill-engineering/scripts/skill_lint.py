# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check one skill directory against the SOP / rules / templates / scripts format and pointing rules.

Usage:
    uv run scripts/skill_lint.py --skill <skill-dir>
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


VERBS = ("READ", "WRITE", "THINK", "DELEGATE")
LEVELS = ("MUST", "SHOULD", "MAY")
COMPAT_LINE = "compatibility: Requires Python >=3.11 and uv"
PART_DIRS = ("rules", "templates", "scripts")
# A part path as it appears in SKILL.md, with or without the ${CLAUDE_SKILL_DIR}/ prefix.
_PART_REF = re.compile(r"(?:\$\{CLAUDE_SKILL_DIR\}/)?((?:rules|templates|scripts)/[^\s`'\"()，。；：、]+)")
_PHASE = re.compile(r"^## Phase (\d+) -- \S.*$")
_STEP = re.compile(r"^(\d+)\. (\S+)(?:\s|$)")
_RULE_H1 = re.compile(r"^# Rule (\d+) - .+ \[(\w+)\]$")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")


class Report:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.lines: list[str] = []

    def add(self, file: Path, line: int, rule: str, msg: str) -> None:
        rel = file.relative_to(self.root) if file.is_relative_to(self.root) else file
        self.lines.append(f"{rel}:{line} {rule} {msg}")


def _split_frontmatter(text: str) -> tuple[list[str], list[str], int]:
    # Return (frontmatter lines, body lines, body start line number as 1-indexed).
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], lines[i + 1 :], i + 2
    return [], lines, 1


def check_sop(skill_md: Path, body: list[str], offset: int, rep: Report) -> None:
    h1_idx = [i for i, l in enumerate(body) if l.startswith("# ")]
    sop_idx = [i for i in h1_idx if l_strip(body[i]) == "# SOP"]
    if len(sop_idx) != 1:
        rep.add(skill_md, offset, "sop-format", "SKILL.md 必須恰有一個一級標題 `# SOP`")
        return
    start = sop_idx[0]
    end = next((i for i in h1_idx if i > start), len(body))
    expected_phase = 1
    expected_step = 0
    in_phase = False
    for i in range(start + 1, end):
        line = body[i]
        ln = offset + i
        if not line.strip():
            continue
        m = _PHASE.match(line)
        if line.startswith("#"):
            if not m:
                rep.add(skill_md, ln, "sop-format", "Phase 標題格式須為 `## Phase N -- 標題`")
                continue
            n = int(m.group(1))
            if n != expected_phase:
                rep.add(skill_md, ln, "sop-format", f"Phase 編號應為 {expected_phase}，實際為 {n}")
            expected_phase = n + 1
            expected_step = 1
            in_phase = True
            continue
        s = _STEP.match(line)
        if not s:
            rep.add(skill_md, ln, "sop-format", "Phase 下只能是阿拉伯數字編號的步驟")
            continue
        n, verb = int(s.group(1)), s.group(2)
        if not in_phase:
            rep.add(skill_md, ln, "sop-format", "步驟出現在任何 Phase 之前")
        elif n != expected_step:
            rep.add(skill_md, ln, "sop-format", f"步驟編號應為 {expected_step}，實際為 {n}")
        expected_step = n + 1
        if verb not in VERBS:
            rep.add(skill_md, ln, "sop-verb", f"動詞 `{verb}` 不在字彙表 {'/'.join(VERBS)} 內")
        if verb == "DELEGATE" and "scripts/" in line and ("rules/" in line or "templates/" in line):
            rep.add(skill_md, ln, "delegate-no-parts", "委派 script 的 DELEGATE 步驟不得點名 rules/ 或 templates/")


def l_strip(s: str) -> str:
    return s.strip()


def check_pointing(skill_md: Path, body: list[str], offset: int, rep: Report) -> None:
    counts: dict[str, list[int]] = {}
    for i, line in enumerate(body):
        for m in _PART_REF.finditer(line):
            if "<" in m.group(1):
                continue  # Placeholder such as scripts/<name>.py describes a path, it is not one.
            counts.setdefault(m.group(1), []).append(offset + i)
    for ref, lines in counts.items():
        if not (rep.root / ref).is_file():
            rep.add(skill_md, lines[0], "missing-part", f"點名的 `{ref}` 不存在")
        if len(lines) > 1:
            rep.add(skill_md, lines[1], "pointed-twice", f"`{ref}` 被點名 {len(lines)} 次，應恰好一次")
    for d in PART_DIRS:
        folder = rep.root / d
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if f.is_dir() or f.name.startswith("."):
                continue
            if f"{d}/{f.name}" not in counts:
                rep.add(f, 1, "orphan-part", "此部件未被 SKILL.md 任何步驟點名")


def check_templates(rep: Report) -> None:
    folder = rep.root / "templates"
    if not folder.is_dir():
        return
    names = {f.name for f in folder.iterdir() if f.is_file()}
    for name in sorted(names):
        f = folder / name
        if ".example." in name:
            stem, _, ext = name.partition(".example.")
            if f"{stem}.{ext}" not in names:
                rep.add(f, 1, "template-pair", f"範例缺少對應骨架 `{stem}.{ext}`")
            text = f.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), 1):
                if "{{" in line:
                    rep.add(f, i, "example-placeholder", "範例不得殘留 `{{...}}` 填位符號")
        else:
            stem, _, ext = name.rpartition(".")
            if f"{stem}.example.{ext}" not in names:
                rep.add(f, 1, "template-pair", f"骨架缺少對應範例 `{stem}.example.{ext}`")


def check_compatibility(skill_md: Path, frontmatter: list[str], rep: Report) -> None:
    scripts = rep.root / "scripts"
    has_scripts = scripts.is_dir() and any(p.suffix == ".py" for p in scripts.iterdir())
    has_compat = any(l.strip() == COMPAT_LINE for l in frontmatter)
    if has_scripts and not has_compat:
        rep.add(skill_md, 1, "compatibility", f"有 scripts/ 但 frontmatter 缺 `{COMPAT_LINE}`")
    if has_compat and not has_scripts:
        rep.add(skill_md, 1, "compatibility", "frontmatter 有 compatibility 但 scripts/ 內沒有 script")


def check_rules(rep: Report) -> None:
    folder = rep.root / "rules"
    if not folder.is_dir():
        return
    for f in sorted(folder.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        expected = 1
        rule_line = 0
        state = ""  # "", "rule", "good", "bad"
        fence = ""  # Backtick run that opened the current fenced block, if any.
        for i, line in enumerate(lines, 1):
            m_fence = _FENCE.match(line)
            if fence:
                if m_fence and m_fence.group(1)[0] == fence[0] and len(m_fence.group(1)) >= len(fence) and not m_fence.group(2).strip():
                    fence = ""
                continue
            if m_fence:
                fence = m_fence.group(1)
                continue
            if line.startswith("# "):
                if state == "rule":
                    rep.add(f, rule_line, "rule-examples", "Rule 缺少 `## Good Example` 與 `## Bad Example`")
                elif state == "good":
                    rep.add(f, rule_line, "rule-examples", "Rule 缺少 `## Bad Example`")
                m = _RULE_H1.match(line)
                if not m:
                    rep.add(f, i, "rule-format", "標題須為 `# Rule N - 名稱 [等級]`")
                    state, rule_line = "rule", i
                    continue
                n, level = int(m.group(1)), m.group(2)
                if n != expected:
                    rep.add(f, i, "rule-format", f"Rule 編號應為 {expected}，實際為 {n}")
                expected = n + 1
                if level not in LEVELS:
                    rep.add(f, i, "rule-level", f"等級 `{level}` 不在 {'/'.join(LEVELS)} 內")
                state, rule_line = "rule", i
            elif line.startswith("## "):
                if line.strip() == "## Good Example":
                    if state != "rule":
                        rep.add(f, i, "rule-examples", "`## Good Example` 必須緊接在 Rule 之後且只出現一次")
                    state = "good"
                elif line.strip() == "## Bad Example":
                    if state != "good":
                        rep.add(f, i, "rule-examples", "`## Bad Example` 必須在 `## Good Example` 之後且只出現一次")
                    state = "bad"
                else:
                    rep.add(f, i, "rule-format", "Rule 內只允許 `## Good Example` 與 `## Bad Example` 兩個二級標題")
        if state == "rule":
            rep.add(f, rule_line, "rule-examples", "Rule 缺少 `## Good Example` 與 `## Bad Example`")
        elif state == "good":
            rep.add(f, rule_line, "rule-examples", "Rule 缺少 `## Bad Example`")
        if expected == 1:
            rep.add(f, 1, "rule-format", "RuleFile 內沒有任何 Rule")


def check_scripts(rep: Report) -> None:
    folder = rep.root / "scripts"
    if not folder.is_dir():
        return
    for f in sorted(folder.glob("*.py")):
        src = f.read_text(encoding="utf-8")
        block = next((m for m in re.finditer(_PEP723, src) if m.group("type") == "script"), None)
        if block is None:
            rep.add(f, 1, "pep723", "缺少 `# /// script` 區塊")
            continue
        content = "".join(
            line[2:] if line.startswith("# ") else line[1:]
            for line in block.group("content").splitlines(keepends=True)
        )
        try:
            meta = tomllib.loads(content)
        except tomllib.TOMLDecodeError as e:
            rep.add(f, 1, "pep723", f"區塊不是合法 TOML：{e}")
            continue
        if meta.get("requires-python") != ">=3.11":
            rep.add(f, 1, "pep723", '區塊須含 `requires-python = ">=3.11"`')
        if "dependencies" not in meta:
            rep.add(f, 1, "pep723", "區塊須含 `dependencies` 欄位（無相依時寫 `[]`）")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check one skill directory against the SOP / rules / templates / scripts format and pointing rules.")
    parser.add_argument("--skill", required=True, help="Path to the skill directory containing SKILL.md")
    args = parser.parse_args()
    root = Path(args.skill).resolve()
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        sys.stderr.write(f"error: '{skill_md}' does not exist; pass --skill <dir> pointing at a directory that contains SKILL.md\n")
        return 2
    rep = Report(root)
    frontmatter, body, offset = _split_frontmatter(skill_md.read_text(encoding="utf-8"))
    check_sop(skill_md, body, offset, rep)
    check_pointing(skill_md, body, offset, rep)
    check_templates(rep)
    check_compatibility(skill_md, frontmatter, rep)
    check_rules(rep)
    check_scripts(rep)
    for line in rep.lines:
        sys.stdout.write(line + "\n")
    return 1 if rep.lines else 0


if __name__ == "__main__":
    sys.exit(main())
