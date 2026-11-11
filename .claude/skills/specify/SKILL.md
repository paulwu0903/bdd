---
name: specify
description: 要把使用者以自然語言描述的功能需求（含新增、修改或刪除 `specs/truth/requirements.md` 中既有需求）轉成新 plan package 的 spec.md，並同步 truth 的現行需求時，必須使用此 skill；每次執行一定開一個新的 plan package 與 git branch。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/specify.md, templates/spec-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/specify.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取現行需求
1. READ 讀取 `specs/truth/requirements.md` 全文，以及與功能描述相關的 `specs/truth/features/<端點>/<模組>/` 下各 feature 檔的 Feature、Rule 標題；requirements.md 不存在時視為沒有現行需求。

## Phase 2 -- 釐清需求
1. THINK 逐句拆出功能描述中的每個要求，並依 `rules/釐清-規範.md` 判定哪些歧義要問使用者、哪些由 AI 推定。
2. THINK 依 `rules/既有需求異動-規範.md` 逐一比對每個要求與現行需求，判定為新增、修改既有或刪除既有，並為每條修改、刪除寫出既有編號、新內容與理由。
3. DELEGATE 有修改或刪除時交給 truth-delta 執行「判定影響」，傳入第 2 步的清單，取得高影響與低風險清單。
4. THINK 將要問的歧義與高影響的修改、刪除逐題附上選項與權衡比較，向使用者提問；未獲回答前停止，不寫 spec；使用者不同意的修改、刪除改回新增或移出本次範圍；沒有要問的項目則直接進入 Phase 3。

## Phase 3 -- 推導需求
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file specs/plans/<NNN>-<專案名的 kebab-case 英文名稱>/spec.md`（NNN 為 `specs/plans/` 中最大編號加一），取得適用於 spec.md 的憲法檔清單；檔案尚未建立時只比對路徑。
2. READ 讀取第 1 步取得的每個憲法檔，本 Phase 後續各步推導時一併遵守，與 `rules/` 衝突時以憲法為準；清單為空則略過。
3. THINK 依 `rules/UserStory-規範.md` 將功能切成可獨立測試、依價值排序的 User Story，並寫出每個 User Story 的驗收情境。
4. THINK 依 `rules/EdgeCase-規範.md` 逐類掃描邊界與異常情境，寫出 Edge Cases。
5. THINK 依 `rules/需求歸屬-規範.md` 為每個 User Story 推導 FR 與 NFR（含 Edge Cases 帶出的約束），並決定每條需求歸屬於 User Story、Global Requirements 或 System Constraints；需求內容依 `rules/寫作視角-規範.md` 撰寫。
6. THINK 為第 5 步推導出的每條「絕不」「不提供」類 FR / NFR，回補其所屬或適用之 User Story 的反向驗收情境。
7. THINK 依 `rules/KeyEntity-規範.md` 整理 Key Entities，並依 `rules/SuccessCriteria-規範.md` 定出 Success Criteria。

## Phase 4 -- 開立 plan package
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/git_state.py`，取得是否為 git repo、未 commit 的改動清單，以及目前 branch 上 truth-delta.md 的 Status 不是「已交付」的 plan。
2. THINK 依第 1 步的結果逐項詢問使用者：不是 git repo 時問是否執行 `git init` 並建立第一個 commit；有未 commit 的改動時問「先 commit、帶著改動開 branch、取消」；有未交付的 plan 時提醒並問是否繼續；未獲回答前停止，依回答執行，使用者取消則結束，不建立任何檔案。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/create_feature.py --short-name <專案名的 kebab-case 英文名稱>`，於 `specs/plans/` 下建立新的 `<NNN>-<專案名>` plan 目錄並切換到同名的新 git branch，取得目錄路徑與 branch 名稱。
4. DELEGATE 交給 truth-delta 執行「建立」，傳入 plan 目錄與 branch 名稱，取得 truth-delta.md 的路徑與 Base。

## Phase 5 -- 寫入、同步並回檢
1. WRITE 複製 `templates/spec.md` 並參照 `templates/spec.example.md` 改寫填位符號，寫入 plan 目錄的 `spec.md`；Feature Branch 填 branch 名稱，Input 逐字保留使用者原文，既有需求異動填入 Phase 2 判定並經確認的修改與刪除。
2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/spec_lint.py --spec <spec.md 路徑>`，取得結構與既有需求異動的違規清單；有違規即修正後重跑。
3. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，逐條自檢列出的 Rule 並修正。
4. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/sync_requirements.py --spec <spec.md 路徑>`，把 spec 的新需求加上 plan 前綴寫入 `specs/truth/requirements.md`，並依既有需求異動就地改寫或移除既有條目。
5. DELEGATE 交給 truth-delta 執行「記錄」，段落為 requirements，依據檔傳入 spec.md；回報「超出宣告範圍」的項目時向使用者確認，未獲回答前停止。
6. WRITE 向使用者回報 plan 目錄、branch、套用的憲法檔與被覆寫的內建 Rule、requirements 段 ADD、MODIFY、DELETE 各幾列，以及下一步為 /clarify-over-specs。
