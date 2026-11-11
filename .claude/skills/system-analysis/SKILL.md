---
name: system-analysis
description: 在 plan package（`specs/plans/<NNN>-<名稱>/`）已有 spec.md、research.md、truth-delta.md，且 /technical-research 已更新 `specs/truth/techstack.md` 之後，要盤點需求涉及的端點與系統介面（含新增的介面，以及被修改、刪除的既有介面）、規劃 wave 順序並產出 plan.md，再依 wave 委派 owner skill 就地修改 truth 的契約與資料表、產出 plan 的 ui/，並檢查 truth-delta 的 contracts 與 data 段時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取需求與現況
1. READ 讀取使用者指定的 `specs/plans/<NNN>-<名稱>/spec.md`，取出 Input 使用者原文、全部 FR／NFR 條目，以及「既有需求異動」表的每一列（動作、既有編號、新內容）。
2. READ 確認 plan 目錄有 `truth-delta.md` 與 `research.md`，且 `specs/truth/techstack.md` 存在；缺 truth-delta.md 時請使用者先執行 /specify，缺 research.md 或 truth 的 techstack.md 時請使用者先執行 /technical-research，未補齊前停止。
3. READ 讀取 plan 目錄的 `research.md`（含各決策的 `**取代**` 欄位）、`truth-delta.md` 的 requirements 與 techstack 段，以及 `specs/truth/techstack.md`，取出已定案的架構、狀態存放位置、儲存決策與本次的需求、技術異動。
4. READ 讀取 `specs/truth/contracts/` 各檔的 tags 與 operationId、`specs/truth/data/schema.dbml` 的 Table 與 TableGroup、`specs/truth/features/<端點>/` 的模組目錄，以及 repository 中各端點的程式目錄樹；檔案或目錄不存在時視為首次建立。
5. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/trace_refs.py --truth specs/truth --id <編號> [--id <編號> ...]`，編號取自既有需求異動與 truth-delta requirements 段中 MODIFY、DELETE 的需求編號，以及 research.md `**取代**` 指向的決策編號（寫成 `research NNN/Rn`），取得 truth 中引用它們的 operationId 與所屬 tag、Table 或 TableGroup、feature 檔與 Example；沒有可追的編號時略過。

## Phase 2 -- 盤點端點與介面
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <plan 目錄>/plan.md`，取得適用於 plan.md 的憲法檔清單。
2. READ 讀取第 1 步取得的每個憲法檔，本 Phase 至 Phase 4 撰寫 plan.md 內容時一併遵守，與 `rules/` 衝突時以憲法為準；清單為空則略過。
3. THINK 從 spec.md 與 Phase 1 第 5 步的命中盤點本次需求涉及的端點類型（前端、後端、資料庫、檔案儲存，視需求還有硬體、手機、雲端、第三方等），每個端點視為一個獨立系統。
4. THINK 依 `rules/介面盤點-規範.md` 與 Phase 1 第 3、4、5 步的結果，將每個端點拆成系統介面，涵蓋新增的介面與受影響的既有介面，寫出每個介面的端點類型、異動、主要介面與需求原文依據；只存在記憶體或其他端點的狀態，不拆成資料表介面。

## Phase 3 -- 安排分析流程
1. THINK 依 `rules/分析流程-規範.md` 將端點依依賴分成多個 wave，寫出每個 wave 的平行分析端點與安排理由。
2. READ 讀取 `.claude/skills/` 底下每個 skill 的 SKILL.md，取得其 description 宣告負責的端點類型與產出或修改的檔案。
3. THINK 為每個端點選出 description 宣告負責該端點類型的 skill 作為委派 skill；某端點找不到或有多個候選時，向使用者詢問，未獲回答前停止。

## Phase 4 -- 規劃專案結構
1. THINK 依 `rules/專案結構-規範.md`，以 Phase 2 的端點與介面、Phase 3 各委派 skill 產出或修改的檔案，以及 Phase 1 第 4 步讀到的程式目錄樹，寫出分成 plan package 與 truth 兩段的 Documentation 樹、只列本次新增、修改、刪除檔案的 Source Code 樹，以及 Structure Decision。

## Phase 5 -- 寫入
1. WRITE 複製 `templates/plan.md` 並參照 `templates/plan.example.md` 改寫填位符號，寫入 plan 目錄的 `plan.md`。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <plan.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，並逐條自檢列出的 Rule 並修正。

## Phase 6 -- 執行分析
1. DELEGATE 依 plan.md 的 wave 順序，為同一 wave 的每個端點各開一個子代理平行執行其委派 skill，傳入 plan 目錄、spec.md、plan.md、research.md、truth-delta.md 與 `specs/truth/` 的路徑、負責的端點類型與落點（api-plan → `specs/truth/contracts/`，data-plan → `specs/truth/data/`，ui-plan → `<plan 目錄>/ui/`），並收回各子代理回報的產出或修改路徑；子代理回傳需要使用者回答的問題時，轉問使用者並把答案交回同一個子代理繼續，其餘子代理照常執行；後一個 wave 回報需要修改前一個 wave 的 truth 時，重新委派該 owner 修改，再重跑依賴它的端點；一個 wave 的子代理全部完成才進入下一個 wave，除此之外不停下等待使用者確認。
2. DELEGATE 子代理回報高影響的修改、刪除，或超出宣告範圍的連帶影響時，交給 clarify 訪談使用者，傳入該子代理的清單與 spec.md 既有需求異動，取得拍板結果後交回同一個子代理繼續；未獲拍板前該子代理不修改這些項目。

## Phase 7 -- 回檢
1. READ 讀取全部產出並比對 plan.md 的系統介面盤點，確認每個端點都有產出、新增與修改既有的介面都在其端點的產出中被分析、刪除既有的介面已從 truth 移除；有遺漏的端點重新委派一次，仍有遺漏則連同產出清單向使用者回報。
2. DELEGATE 交給 truth-delta 執行「檢查」，段落為 contracts 與 data，取得未記錄、記錯與摘要或原因留空的列；有違規時交回該段的 owner（contracts → api-plan，data → data-plan）補記後重跑，直到沒有違規。
3. WRITE 向使用者回報 plan.md 路徑、各端點的產出或修改路徑、contracts 與 data 段 ADD、MODIFY、DELETE 各幾列、經 clarify 拍板的項目、plan.md 與各子代理回報的套用憲法檔與被覆寫的內建 Rule，以及下一步為 /dsl-refine。
