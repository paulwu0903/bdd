# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Inventory a skill chain: steps, part references, delegated skills, orphan and missing files.

Usage:
    uv run scripts/analyze_skill_references.py --skill <skill-dir> [--skill <skill-dir> ...] [--root <skills-root> ...]
"""
import argparse
import re
import sys
import tomllib
from collections import deque
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


PART_DIRS = ("rules", "templates", "scripts")
_PART_REF = re.compile(r"(?:\$\{CLAUDE_SKILL_DIR\}/)?((?:rules|templates|scripts)/[^\s`'\"()，。；：、]+)")
_PHASE = re.compile(r"^## Phase (\d+) -- (.*)$")
_STEP = re.compile(r"^(\d+)\. (\S+)\s*(.*)$")


def _split_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    lines = text.splitlines()
    meta: dict[str, str] = {}
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for l in lines[1:i]:
                    key, sep, val = l.partition(":")
                    if sep:
                        meta[key.strip()] = val.strip()
                return meta, lines[i + 1 :]
    return meta, lines


def _discover_skills(roots: list[Path]) -> dict[str, Path]:
    # Map every skill directory name under the given roots to its path; first root wins on duplicates.
    found: dict[str, Path] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / "SKILL.md").is_file() and d.name not in found:
                found[d.name] = d
    return found


def _analyze(skill_dir: Path, known: dict[str, Path]) -> dict:
    meta, body = _split_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    name_pattern = re.compile(
        r"(?<![A-Za-z0-9_-])(" + "|".join(re.escape(n) for n in sorted(known, key=len, reverse=True)) + r")(?![A-Za-z0-9_-])"
    ) if known else None
    steps: list[dict] = []
    phase = 0
    for line in body:
        m = _PHASE.match(line)
        if m:
            phase = int(m.group(1))
            continue
        s = _STEP.match(line)
        if not s or phase == 0:
            continue
        parts = [p for p in _PART_REF.findall(line) if "<" not in p]
        delegated = sorted({n for n in name_pattern.findall(line) if n != skill_dir.name}) if name_pattern else []
        steps.append({
            "label": f"Phase {phase} 第 {s.group(1)} 步",
            "verb": s.group(2),
            "parts": parts,
            "skills": delegated,
        })
    referenced: dict[str, list[str]] = {}
    for st in steps:
        for p in st["parts"]:
            referenced.setdefault(p, []).append(st["label"])
    present: list[str] = []
    for d in PART_DIRS:
        folder = skill_dir / d
        if folder.is_dir():
            present += [f"{d}/{f.name}" for f in sorted(folder.iterdir()) if f.is_file() and not f.name.startswith(".")]
    return {
        "name": skill_dir.name,
        "path": skill_dir,
        "meta": meta,
        "steps": steps,
        "referenced": referenced,
        "orphans": [p for p in present if p not in referenced],
        "missing": [p for p in referenced if p not in present],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory a skill chain: steps, part references, delegated skills, orphan and missing files.")
    parser.add_argument("--skill", action="append", required=True, help="Skill directory to start from; repeat to add more entry points")
    parser.add_argument("--root", action="append", default=[], help="Extra directory whose subdirectories are skills; the parents of --skill and ~/.claude/skills are always searched")
    args = parser.parse_args()
    entries = [Path(s).resolve() for s in args.skill]
    for e in entries:
        if not (e / "SKILL.md").is_file():
            sys.stderr.write(f"error: '{e}' has no SKILL.md; pass --skill <dir> pointing at a skill directory\n")
            return 2
    roots = [e.parent for e in entries] + [Path(r).resolve() for r in args.root] + [Path.home() / ".claude" / "skills"]
    known = _discover_skills(roots)
    for e in entries:
        known.setdefault(e.name, e)

    analyzed: dict[str, dict] = {}
    unresolved: set[str] = set()
    edges: list[tuple[str, str, str]] = []
    queue = deque(entries)
    while queue:
        d = queue.popleft()
        if d.name in analyzed:
            continue
        info = _analyze(d, known)
        analyzed[d.name] = info
        for st in info["steps"]:
            for s in st["skills"]:
                edges.append((d.name, st["label"], s))
                if s in known:
                    queue.append(known[s])
                else:
                    unresolved.add(s)

    out: list[str] = ["# Skill 鏈盤點", "", "## 鏈", "", "| 來源 skill | 步驟 | 委派 skill | 目錄 |", "|---|---|---|---|"]
    for src, label, dst in edges:
        out.append(f"| {src} | {label} | {dst} | {known[dst] if dst in known else '（未解析）'} |")
    if not edges:
        out.append("| （無委派） | | | |")
    for info in analyzed.values():
        out += ["", f"## {info['name']}（{info['path']}）", ""]
        for key in ("description", "compatibility"):
            if key in info["meta"]:
                out.append(f"- {key}: {info['meta'][key]}")
        out += ["", "### 步驟", "", "| 步驟 | 動詞 | 點名部件 | 委派 skill |", "|---|---|---|---|"]
        for st in info["steps"]:
            out.append(f"| {st['label']} | {st['verb']} | {', '.join(st['parts']) or '—'} | {', '.join(st['skills']) or '—'} |")
        if not info["steps"]:
            out.append("| （無 Phase / 步驟，非模組化 skill，需直接讀 SKILL.md 全文） | | | |")
        out += ["", "### 部件", "", "| 檔案 | 被點名於 |", "|---|---|"]
        for p, labels in info["referenced"].items():
            if p not in info["missing"]:
                out.append(f"| {p} | {', '.join(labels)} |")
        for p in info["orphans"]:
            out.append(f"| {p} | （孤兒，未被點名） |")
        if info["missing"]:
            out += ["", "### 缺失部件", ""]
            for p in info["missing"]:
                out.append(f"- {p} ← {', '.join(info['referenced'][p])}")
    if unresolved:
        out += ["", "## 未解析的 skill 名稱", ""] + [f"- {s}" for s in sorted(unresolved)]
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
