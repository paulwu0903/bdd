---
name: data-plan
description: 要為 `資料庫端點` 的資料表介面設計資料表契約，產出 schema.dbml 時（含由 system-analysis 委派），必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取輸入
1. READ 讀取呼叫端傳入的 spec.md、plan.md、research.md、techstack.md 與上游產出，上游的 openapi.yaml 與 asyncapi.yaml 必讀；單獨使用時向使用者取得 spec.md 路徑與上游 openapi.yaml、asyncapi.yaml 的路徑，以 spec.md 同目錄的檔案為輸入、同目錄的 `analysis/` 為產出目錄。
2. READ 從 plan.md 的系統介面盤點取出端點類型為 `資料庫端點` 的全部介面，以及各介面的主要介面與需求原文依據。

## Phase 2 -- 設計資料表
1. READ 讀取 DBML 官方文件（https://dbml.dbdiagram.io/docs/），確認目前的語法。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <產出目錄>/schema.dbml`，取得適用於 schema.dbml 的憲法檔清單。
3. THINK 依 `rules/資料表設計-規範.md` 與第 2 步取得的憲法檔（與 `rules/` 衝突時以憲法為準），為每個資料表介面設計資料表、欄位、索引與交易；有需要使用者決定的問題時，回傳給呼叫端轉問（單獨使用時直接詢問使用者），未獲回答前停止。

## Phase 3 -- 寫入並驗證
1. WRITE 複製 `templates/schema.dbml` 並參照 `templates/schema.example.dbml` 改寫填位符號，寫入產出目錄的 `schema.dbml`。
2. DELEGATE 在 scratchpad 目錄執行 `npx -p @dbml/cli dbml2sql --<techstack 指定的資料庫，如 mysql> <schema.dbml>`，從輸出的 `ERROR` 段取得語法錯誤清單（有錯時 exit code 仍為 0）。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/coverage_check.py --plan <plan.md> --dbml <schema.dbml> --openapi <openapi.yaml>`，取得缺 Table 的資料表介面、缺「對應需求」的 Note 與交易未寫入 TableGroup 的 operation 清單。
4. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <schema.dbml> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule。
5. WRITE 依第 2–4 步的結果修正產出並重跑，並逐條自檢第 4 步列出的 Rule，直到沒有錯誤，最後向呼叫端回報產出路徑、驗證結果、套用的憲法檔與被覆寫的內建 Rule，以及 spec 未規定而自行決定的事項。
