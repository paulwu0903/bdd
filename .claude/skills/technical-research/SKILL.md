---
name: technical-research
description: 在 /specify 產出 spec.md 之後，要為該功能定案實作所需的技術決策，並產出 research.md 與彙整技術堆疊的 techstack.md 時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 列出研究題目
1. READ 讀取使用者指定的 `specs/<NNN>-<專案名>/spec.md`；未指定則詢問使用者。
2. THINK 依 `rules/研究題目-規範.md` 逐條掃描 spec 的 FR、NFR、Success Criteria、Edge Cases 與 Assumptions，列出實作前必須定案的技術決策作為研究題目，並為每題列出候選方案。

## Phase 2 -- 查證候選方案
1. READ 依 `rules/查證-規範.md` 向官方來源讀取每個候選方案的最新版本、相依需求、瀏覽器支援、授權（含遞移依賴）與最後發佈日，記下每項事實的來源 URL。

## Phase 3 -- 釐清
1. THINK 依 `rules/釐清-規範.md` 判定要向使用者提問的決策與查證後發現 spec 需修訂之處，逐題附上選項與權衡比較提問；未獲回答前停止，不寫 research.md；沒有要問的則直接進入 Phase 4。
2. WRITE 使用者同意修訂 spec 時，修改 spec.md 的對應條目，修改後以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 路徑> --check`，有違規即修正後重跑，並逐條自檢列出的 Rule 並修正；最後依 `rules/spec修訂-規範.md` 比對 acceptance feature 檔，向使用者回報受修訂影響的情境。

## Phase 4 -- 寫入並回檢
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 同目錄>/research.md --file <spec.md 同目錄>/techstack.md`，取得適用於 research.md 與 techstack.md 的憲法檔清單。
2. THINK 依 `rules/決策條目-規範.md` 與第 1 步取得的 research.md 憲法檔（與 `rules/` 衝突時以憲法為準），為每個研究題目寫出 Decision、Rationale、補充欄與 Alternatives considered；撰寫時發現需要使用者決定的問題，回到 Phase 3 第 1 步提問。
3. THINK 依 `rules/依賴授權-規範.md` 整理依賴授權表。
4. WRITE 複製 `templates/research.md` 並參照 `templates/research.example.md` 改寫填位符號，寫入 spec.md 同目錄的 `research.md`；Sources 列出查證時用到的每個 URL。
5. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/research_lint.py --research <research.md 路徑>`，取得結構違規清單；有違規即修正後重跑。
6. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <research.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，並逐條自檢列出的 Rule 並修正。

## Phase 5 -- 彙整技術堆疊
1. THINK 依 `rules/技術堆疊-規範.md` 與 Phase 4 第 1 步取得的 techstack.md 憲法檔（與 `rules/` 衝突時以憲法為準），從 research.md 各 R 節的 Decision 萃取執行環境與所有套件，分成 Runtime 與 Dev。
2. WRITE 複製 `templates/techstack.md` 並參照 `templates/techstack.example.md` 改寫填位符號，寫入 spec.md 同目錄的 `techstack.md`。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/techstack_lint.py --techstack <techstack.md 路徑> --research <research.md 路徑>`，取得結構與一致性違規清單；有違規即修正後重跑。
4. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <techstack.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，逐條自檢列出的 Rule 並修正，最後向使用者回報本次套用的憲法檔與被覆寫的內建 Rule。
