---
name: data-plan
description: 要為 plan 中 `資料庫端點` 的資料表介面（新增、修改既有或刪除既有）設計資料表契約，在 `specs/truth/data/schema.dbml` 就地新增、修改或刪除 Table、欄位、TableGroup 與交易，並委派 truth-delta 判定影響與記錄 data 段時（含由 system-analysis 委派），必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取輸入
1. READ 讀取呼叫端傳入的 plan 目錄中的 spec.md（含既有需求異動）、plan.md、research.md（含各決策的 `**取代**` 欄位）、truth-delta.md 的 requirements 與 contracts 段、`specs/truth/techstack.md`，以及 `specs/truth/contracts/` 下 openapi.yaml 與 asyncapi.yaml 的全文；單獨使用時向使用者取得 plan 目錄。
2. READ 從 plan.md 的系統介面盤點取出端點類型為 `資料庫端點` 的全部介面，以及各介面的異動、主要介面與需求原文依據。
3. READ 讀取 `specs/truth/data/schema.dbml` 的全文；檔案不存在時視為首次建立。

## Phase 2 -- 設計資料表
1. READ 讀取 DBML 官方文件（https://dbml.dbdiagram.io/docs/），確認目前的語法。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file specs/truth/data/schema.dbml`，取得適用於 schema.dbml 的憲法檔清單。
3. THINK 依 `rules/資料表設計-規範.md` 與第 2 步取得的憲法檔（與 `rules/` 衝突時以憲法為準），依各資料表介面的異動設計資料表、欄位、索引與交易：新增的寫出完整定義，修改既有與刪除既有的以 truth 現況為基準，並依 truth-delta contracts 段的每一列與被 `**取代**` 的決策掃描連帶影響，整理成以語義單元為部位（如 `schema.dbml › Table <表>`、`schema.dbml › Table <表>.<欄位>`、`schema.dbml › TableGroup 資料庫共通介面`）的 ADD、MODIFY、DELETE 清單；有需要使用者決定的問題時，回傳給呼叫端轉問（單獨使用時直接詢問使用者），未獲回答前停止。
4. DELEGATE 清單有 MODIFY 或 DELETE 時交給 truth-delta 執行「判定影響」，傳入 plan 目錄與每一項的部位與改動內容，取得需先交給 clarify 的高影響項目、已確認項目與低風險項目。
5. DELEGATE 有高影響項目、連帶影響超出宣告範圍的項目，或需要修改契約的項目時，由 system-analysis 委派的情境下回傳給呼叫端（契約的修改由呼叫端重新委派 api-plan），單獨使用時直接交給 clarify 訪談使用者，取得拍板結果；未獲拍板前不修改這些項目，使用者不同意的項目移出清單。

## Phase 3 -- 寫入並驗證
1. WRITE 依定案的清單就地修改 `specs/truth/data/schema.dbml`，只改清單中的部位，不整份重寫；檔案不存在時才複製 `templates/schema.dbml` 並參照 `templates/schema.example.dbml` 改寫填位符號建立。
2. DELEGATE 在 scratchpad 目錄執行 `npx -p @dbml/cli dbml2sql --<specs/truth/techstack.md 指定的資料庫，如 mysql> specs/truth/data/schema.dbml`，從輸出的 `ERROR` 段取得語法錯誤清單（有錯時 exit code 仍為 0）。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/coverage_check.py --plan <plan.md> --dbml specs/truth/data/schema.dbml --openapi specs/truth/contracts/openapi.yaml [--asyncapi specs/truth/contracts/asyncapi.yaml] --requirements specs/truth/requirements.md`，取得新增或修改既有卻缺 Table、刪除既有卻仍有 Table 的介面，Note 缺對應需求或編號不帶前綴、不在現行需求中的 Table 與 TableGroup，TableGroup 成員與 Table 不一致之處，有交易卻未寫入 TableGroup 或已不存在卻仍被交易段引用的 operation，以及欄位 note 中不在 `Error.code` 的錯誤碼清單。
4. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file specs/truth/data/schema.dbml --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule。
5. WRITE 依第 2–4 步的結果修正 schema.dbml 並重跑，並逐條自檢第 4 步列出的 Rule，直到沒有錯誤。
6. DELEGATE 交給 truth-delta 執行「記錄」，段落為 data，依據檔傳入 spec.md、plan.md、research.md、truth-delta.md 的 contracts 段與 clarify 的拍板結果；回報「超出宣告範圍」的項目時，比照 Phase 2 第 5 步取得拍板，確認不納入的項目還原後從第 2 步重跑。
7. WRITE 向呼叫端回報修改的 schema.dbml 路徑、驗證結果、data 段 ADD、MODIFY、DELETE 各幾列、經 clarify 拍板的項目、需要回頭修改契約的項目、套用的憲法檔與被覆寫的內建 Rule、spec 未規定而自行決定的事項，並提醒 migration 由 /tasks 依 data 段產生。
