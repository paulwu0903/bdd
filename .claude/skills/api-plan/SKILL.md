---
name: api-plan
description: 要為 `後端端點` 的系統介面設計 HTTP API 與即時事件契約，產出 openapi.yaml，以及有即時事件時的 asyncapi.yaml 時（含由 system-analysis 委派），必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取輸入
1. READ 讀取呼叫端傳入的 spec.md、plan.md、research.md、techstack.md 與上游產出；單獨使用時向使用者取得 spec.md 路徑，以其同目錄的檔案為輸入、同目錄的 `analysis/` 為產出目錄。
2. READ 從 plan.md 的系統介面盤點取出端點類型為 `後端端點` 的全部介面，以及各介面的主要介面與需求原文依據。

## Phase 2 -- 設計契約
1. READ 讀取 OpenAPI（spec.openapis.org）與 AsyncAPI（asyncapi/spec 的 GitHub release）的官方來源，確認最新版本。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <產出目錄>/openapi.yaml --file <產出目錄>/asyncapi.yaml`，取得適用於 openapi.yaml 與 asyncapi.yaml 的憲法檔清單。
3. THINK 依 `rules/契約設計-規範.md` 與第 2 步取得的憲法檔（與 `rules/` 衝突時以憲法為準），為每個後端介面設計 HTTP API 或即時事件，寫出完整 schema、業務規則、交易與錯誤碼；有需要使用者決定的問題時，回傳給呼叫端轉問（單獨使用時直接詢問使用者），未獲回答前停止。

## Phase 3 -- 寫入並驗證
1. WRITE 複製 `templates/openapi.yaml` 並參照 `templates/openapi.example.yaml` 改寫填位符號，寫入產出目錄的 `openapi.yaml`；有即時事件時，同樣以 `templates/asyncapi.yaml` 與 `templates/asyncapi.example.yaml` 寫入 `asyncapi.yaml`。
2. DELEGATE 在 scratchpad 目錄執行 `npx @redocly/cli lint --extends=minimal <openapi.yaml>`，有 asyncapi.yaml 時再執行 `npx @asyncapi/cli validate <asyncapi.yaml>`，取得語法錯誤清單。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/coverage_check.py --plan <plan.md> --openapi <openapi.yaml> [--asyncapi <asyncapi.yaml>]`，取得缺 tag 的後端介面、缺「對應需求」的 API 與缺錯誤碼說明的錯誤回應清單。
4. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <openapi.yaml> [--file <asyncapi.yaml>] --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule。
5. WRITE 依第 2–4 步的結果修正產出並重跑，並逐條自檢第 4 步列出的 Rule，直到沒有錯誤，最後向呼叫端回報產出路徑、驗證結果、套用的憲法檔與被覆寫的內建 Rule，以及 spec 未規定而自行決定的事項。
