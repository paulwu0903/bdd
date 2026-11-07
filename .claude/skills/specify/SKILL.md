---
name: specify
description: 要把使用者以自然語言描述的功能需求轉成一份 spec.md 功能規格時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/specify.md, templates/spec-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/specify.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 釐清需求
1. THINK 逐句拆出功能描述中的每個要求，並依 `rules/釐清-規範.md` 判定哪些歧義要問使用者、哪些由 AI 推定。
2. THINK 將要問的歧義逐題附上選項與權衡比較，向使用者提問；未獲回答前停止，不寫 spec；沒有要問的歧義則直接進入 Phase 2。

## Phase 2 -- 推導需求
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file specs/<專案名的 kebab-case 英文名稱>/spec.md`，取得適用於 spec.md 的憲法檔清單；檔案尚未建立時只比對路徑。
2. READ 讀取第 1 步取得的每個憲法檔，本 Phase 後續各步推導時一併遵守，與 `rules/` 衝突時以憲法為準；清單為空則略過。
3. THINK 依 `rules/UserStory-規範.md` 將功能切成可獨立測試、依價值排序的 User Story，並寫出每個 User Story 的驗收情境。
4. THINK 依 `rules/EdgeCase-規範.md` 逐類掃描邊界與異常情境，寫出 Edge Cases。
5. THINK 依 `rules/需求歸屬-規範.md` 為每個 User Story 推導 FR 與 NFR（含 Edge Cases 帶出的約束），並決定每條需求歸屬於 User Story、Global Requirements 或 System Constraints；需求內容依 `rules/寫作視角-規範.md` 撰寫。
6. THINK 為第 5 步推導出的每條「絕不」「不提供」類 FR / NFR，回補其所屬或適用之 User Story 的反向驗收情境。
7. THINK 依 `rules/KeyEntity-規範.md` 整理 Key Entities，並依 `rules/SuccessCriteria-規範.md` 定出 Success Criteria。

## Phase 3 -- 寫入並回檢
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/create_feature.py --short-name <專案名的 kebab-case 英文名稱>`，於 `specs/` 下建立 `<NNN>-<專案名>` 功能目錄並取得其路徑。
2. WRITE 複製 `templates/spec.md` 並參照 `templates/spec.example.md` 改寫填位符號，寫入功能目錄的 `spec.md`；Feature Branch 填功能目錄名，Input 逐字保留使用者原文。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/spec_lint.py --spec <spec.md 路徑>`，取得結構違規清單；有違規即修正後重跑。
4. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，逐條自檢列出的 Rule 並修正，最後向使用者回報套用的憲法檔與被覆寫的內建 Rule。
