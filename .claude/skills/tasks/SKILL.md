---
name: tasks
description: 在 truth owner skill 依 plan 的 truth-delta.md 修改 `specs/truth/` 之後，要把本次的 truth 異動拆成 Truth Impact Audit、MODIFY（/bdd realign、green、refactor）、DELETE（移除）、ADD（/bdd red、green、refactor），以及環境、基礎、NFR 與驗證任務，並產出 tasks.md 時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/tasks.md, templates/tasks-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/tasks.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取異動與切 Phase
1. DELEGATE 交給 truth-delta，以「檢查」動作確認 `specs/plans/<NNN>-<專案名>/truth-delta.md` 與實際異動一致；有違規時停止，請使用者交由對應的 truth owner skill 補記。
2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/list_changes.py --plan <plan 目錄>`，取得：truth-delta 各段落的列；features 段每一列對應的 feature 檔、Example 行號、追溯 tag 與依據；被 MODIFY 或 DELETE 的句型目前被哪些 Example 使用、由哪些 step 檔註冊、這些 step 檔引用了哪些 helper 與 fixture；被 DELETE 的 operation 在產品碼中出現的檔案；以及 spec.md 的故事優先序與「既有需求異動」條目。回報 dsl.md 缺漏或步驟對不到句型時停止，請使用者交由 /dsl-refine 修正。
3. READ 讀取 plan 的 spec.md（使用者故事與既有需求異動）與 `features/acceptance/`，依 `rules/Phase結構-規範.md` 判定是否需要 Truth Impact Audit Phase、每個異動的 Phase 分組與歸屬，以及 Phase 順序。

## Phase 2 -- 切任務
1. READ 讀取 plan 的 `plan.md` 的系統介面盤點與 Source Code 樹，依 `rules/BDD任務-規範.md` 切出各 Phase 的任務：Audit 的 `盤點`、MODIFY 的 `/bdd realign`、`/bdd green`、`/bdd refactor`、DELETE 的 `移除`、ADD 的 `/bdd red`、`/bdd green`、`/bdd refactor`，以及 Acceptance Gates 的驗證任務；MODIFY 與 DELETE 的路徑取自 Phase 1 第 2 步的靜態影響清單。
2. THINK 依第 1 步讀取的同一份規範，從 truth-delta 的 techstack 段定出 Setup 的套件任務，從 data 段定出 migration 任務與它們的位置。
3. THINK 依 `rules/NFR重構-規範.md` 逐條判定本 plan spec.md 的 NFR 與被 MODIFY 的 NFR 由哪個 feature 驗證或是否需要任務，寫出判定表與必要的 `重構` 任務。
4. THINK 依 `rules/Dependencies-規範.md` 定出各 Phase 依賴的 Phase、平行機會與 Parallel Example。

## Phase 3 -- 寫入 tasks.md
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <plan 目錄>/tasks.md`，取得適用於 tasks.md 的憲法檔清單。
2. READ 讀取 plan 的 `research.md`、`ui/`，以及 `specs/truth/techstack.md`、`specs/truth/contracts/`、`specs/truth/data/` 中本次異動涉及的部位，依 `rules/任務列-規範.md`、`rules/契約-規範.md` 與第 1 步取得的憲法檔（與 `rules/` 衝突時以憲法為準）寫出各 Phase 的共用區塊、任務列與契約。
3. WRITE 複製 `templates/tasks.md` 並參照 `templates/tasks.example.md` 改寫填位符號，寫入 plan 目錄的 `tasks.md`。

## Phase 4 -- 回檢
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_tasks.py --tasks <tasks.md 路徑> --plan <plan 目錄>`，取得格式、識別碼、truth-delta 覆蓋、Audit Phase 有無、各類 Phase 的任務形態、Phase 順序、共用區塊、NFR 判定表與 Dependencies 的違規清單；有違規即修正後重跑。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <tasks.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，並逐條自檢列出的 Rule 並修正。
3. DELEGATE 交給 truth-delta，以「切換狀態」動作把 Status 改為實作中；完成後向使用者回報產出路徑、套用的憲法檔與被覆寫的內建 Rule、執行中發現需上游修正的文件不一致、靠判斷歸屬的異動所判定的故事或既有需求異動與依據，以及 NFR 判定表中判為不需任務、只能人工量測的 NFR。
