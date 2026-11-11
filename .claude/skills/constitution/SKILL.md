---
name: constitution
description: 要為本 repo 的 SDD 產出物新增、修改或刪除憲法規則（`.claude/constitution/`）時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/constitution.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/constitution.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 定位約束
1. READ 讀取使用者的需求與 `.claude/constitution/` 底下的現有檔案。
2. THINK 依 `rules/歸屬-規範.md` 把需求拆成一條條約束，判定每條是否收錄、約束哪個產出物，以及寫入 `shared/` 或 `skills/<skill>/<產出物>.md`。
3. DELEGATE 有無法從需求與現有檔案判定的項目時，交給 clarify，傳入這些項目作為指定提問面向、不詳記問答紀錄，取得拍板結果後回到第 2 步；全部判定完才進入 Phase 2。

## Phase 2 -- 對照內建規則
1. READ 讀取目標產出物所屬 skill 的 `rules/` 與 `templates/`。
2. THINK 依 `rules/條款-規範.md` 定出每條約束的 Rule 內容、等級與驗證方式，剔除已被內建規則涵蓋的部分，並記下會被憲法覆寫的內建 Rule。

## Phase 3 -- 寫入
1. WRITE `.claude/constitution/CONSTITUTION.md` 不存在時，複製 `templates/CONSTITUTION.md` 並參照 `templates/CONSTITUTION.example.md` 寫入。
2. WRITE 複製 `templates/產出物.md` 並參照 `templates/產出物.example.md` 改寫填位符號，寫入或更新目標檔；Rule 區塊依 skill-form-rule 的 RuleFile 格式規範與 RuleLevel 定義撰寫。
3. WRITE 新增 `shared/` 檔時，在每個須遵守它的產出物檔加上 `- 引用：`。
4. WRITE 驗證方式為 script 的 Rule，依 `rules/驗證程式-規範.md` 撰寫 `.claude/constitution/checks/<名稱>.py`。

## Phase 4 -- 回檢與影響
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/constitution_lint.py --root .claude/constitution`，取得檔首、Applies To 是否指向現行結構（`specs/plans/`、`specs/truth/` 或 `<工作區>/**`）、引用路徑、驗證路徑與 Rule 格式的違規清單；有違規即修正後重跑。
2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/affected.py --root .claude/constitution --repo <repository root>`，對 Applies To 涵蓋的 truth 與未交付 plan 的既有產出物執行全部 script 驗證，取得依 owner skill 分組的不合規清單與被跳過的凍結 plan（truth-delta.md 的 Status 為已交付，或沒有 truth-delta.md 的舊制 plan），不修改任何產出物；最後向使用者回報異動的檔案、被覆寫的內建 Rule、需逐條自檢的 Rule、依 owner skill 分組的不合規清單與跳過的 plan，並說明 truth 的不合規須由該 owner skill 在 plan branch 上修正並經 truth-delta 記錄。
