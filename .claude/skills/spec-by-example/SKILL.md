---
name: spec-by-example
description: 在 /clarify-over-specs 之後，要讓 PM 以 Gherkin 為 plan 的 spec.md 定義總驗收標準（Journey 型的系統流程，含既有需求異動中 PM 看得到的修改），產出或就地補齊 `specs/plans/<NNN>-<專案名>/features/acceptance/` 底下的 feature 檔與待澄清事項時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 讀取需求
1. READ 讀取使用者指定的 `specs/plans/<NNN>-<專案名>/spec.md` 的 User Stories、驗收情境、FR、NFR、Success Criteria、Edge Cases、既有需求異動與 Assumptions，`specs/truth/requirements.md` 中被 spec 以 plan 前綴引用或列入既有需求異動的條目，以及同目錄已有的 `features/acceptance/`；該目錄已有 feature 檔時為補齊模式。
2. THINK 依 `rules/主題與旅程-規範.md` 定出驗收主題、主題的 demo 順序與每個主題的 Journey，含既有需求異動中 MODIFY 的檢查點與不寫成 Journey 的 DELETE；補齊模式沿用既有的主題與 Journey 順序。

## Phase 2 -- 撰寫驗收 Gherkin
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file specs/plans/<NNN>-<專案名>/features/acceptance/<主題>.feature [--file …]`（每個主題一個 `--file`），取得適用於驗收 feature 檔的憲法檔清單；檔案尚未建立時只比對路徑。
2. READ 讀取第 1 步取得的每個憲法檔，本 Phase 後續各步撰寫時一併遵守，與 `rules/` 衝突時以憲法為準；清單為空則略過。
3. THINK 依 `rules/結構-規範.md` 為每個主題寫出 Feature 描述、一句 Rule 與照流程寫完的 Journey Example；只有多條 Journey 共用的步驟才抽成 Background，沒有共用就不寫。
4. THINK 依 `rules/句子-規範.md` 撰寫每個步驟的句子、參數、Data Table 與檢查點。
5. THINK 依 `rules/澄清標籤-規範.md` 在需求有疑問之處加上澄清標籤並寫明暫定答案。
6. WRITE 複製 `templates/acceptance.feature` 並參照 `templates/acceptance.example.feature` 改寫填位符號，每個主題寫入一個 `specs/plans/<NNN>-<專案名>/features/acceptance/<主題>.feature`；補齊模式就地修改既有檔，保留已澄清的標籤，新 Journey 追加在該主題末尾；不產 dsl.md，不分前端與後端。

## Phase 3 -- 回檢
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_acceptance.py --dir <features/acceptance 目錄>`，取得結構、數量、引號與澄清標籤的違規清單；有違規即修正後重跑。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <每個驗收 feature 檔路徑> [--file …] --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，逐條自檢列出的 Rule 並修正。

## Phase 4 -- 澄清
1. DELEGATE 交給 clarify skill，依 Phase 1 第 2 步定出的主題順序（demo 順序）逐檔、檔內依澄清標籤的出現順序逐題向使用者澄清，並以標籤中的暫定答案作為推薦選項。
2. WRITE 依使用者的回答修改對應的 Background（有的話）、Example 與檢查點數字，再把已解決的標籤改寫成 `# [CLARIFIED: <問題>？→「<定案答案>」]` 並留在原位（不刪除），再執行 Phase 3 全部步驟。
3. DELEGATE 回答補充或改變了 spec.md 的條目（含既有需求異動與現行需求）時，交給 clarify-over-specs 執行回寫模式，傳入 spec.md 路徑與每項修訂（修訂內容、使用者拍板日期、出處為 feature 檔與澄清標籤的問題），取得 spec.md 改動的區塊與 requirements 段的異動列數；回寫模式交回高影響或超出宣告範圍的項目時，向使用者確認後再委派，未獲回答前停止。
4. WRITE 向使用者回報產出路徑、主題數與 Journey 數、套用的憲法檔與被覆寫的內建 Rule、仍未解決的澄清事項（仍為待澄清標籤者）、既有需求異動中 MODIFY 的涵蓋處（主題與 Journey）、未寫成 Journey 的 DELETE、回寫 spec.md 的條目，以及未寫成 Journey 的規格需求（受每主題 Journey 上限擠掉的 FR 與 Edge Cases、量測型 NFR 與 Success Criteria，之後由 /dsl-refine 補成端點測試或列為純量測需求）。
