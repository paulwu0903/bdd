---
name: spec-by-example
description: 在 /specify 產出 spec.md 之後，要讓 PM 以 Gherkin 定義總驗收標準（Journey 型的系統流程），並產出 features/acceptance/ 底下的 feature 檔與待澄清事項時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 讀取需求
1. READ 讀取使用者指定的 `specs/<NNN>-<專案名>/spec.md` 的 User Stories、驗收情境、FR、NFR、Success Criteria、Edge Cases 與 Assumptions。
2. THINK 依 `rules/主題與旅程-規範.md` 定出驗收主題、主題的 demo 順序與每個主題的 Journey。

## Phase 2 -- 撰寫驗收 Gherkin
1. THINK 依 `rules/結構-規範.md` 為每個主題寫出 Feature 描述、一句 Rule 與照流程寫完的 Journey Example；只有多條 Journey 共用的步驟才抽成 Background，沒有共用就不寫。
2. THINK 依 `rules/句子-規範.md` 撰寫每個步驟的句子、參數、Data Table 與檢查點。
3. THINK 依 `rules/澄清標籤-規範.md` 在需求有疑問之處加上澄清標籤並寫明暫定答案。
4. WRITE 複製 `templates/acceptance.feature` 並參照 `templates/acceptance.example.feature` 改寫填位符號，每個主題寫入一個 `specs/<NNN>-<專案名>/features/acceptance/<主題>.feature`；不產 dsl.md，不分前端與後端。

## Phase 3 -- 回檢
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_acceptance.py --dir <features/acceptance 目錄>`，取得結構、數量、引號與澄清標籤的違規清單；有違規即修正後重跑。

## Phase 4 -- 澄清
1. DELEGATE 交給 clarify skill，依 Phase 1 第 2 步定出的主題順序（demo 順序）逐檔、檔內依澄清標籤的出現順序逐題向使用者澄清，並以標籤中的暫定答案作為推薦選項。
2. WRITE 依使用者的回答修改對應的 Background（有的話）、Example 與檢查點數字，再把已解決的標籤改寫成 `# [CLARIFIED: <問題>？→「<定案答案>」]` 並留在原位（不刪除），再執行 Phase 3 第 1 步。
3. READ 向使用者回報產出路徑、主題數與 Journey 數、仍未解決的澄清事項（仍為待澄清標籤者），以及未寫成 Journey 的規格需求（受每主題 Journey 上限擠掉的 FR 與 Edge Cases、量測型 NFR 與 Success Criteria，之後由 /dsl-refine 補成端點測試或列為純量測需求）。
