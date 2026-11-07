---
name: ui-plan
description: 要為 `前端端點` 的前端介面規劃畫面規格與可操作的視覺雛形，產出 frontend.md 與 prototype/*.html 時（含由 system-analysis 委派），必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取輸入
1. READ 讀取呼叫端傳入的 spec.md、plan.md、research.md、techstack.md 與上游的 openapi.yaml、asyncapi.yaml；單獨使用時向使用者取得 spec.md 與上游契約的路徑，以 spec.md 同目錄的 `analysis/` 為產出目錄。
2. READ 從 plan.md 的系統介面盤點取出端點類型為 `前端端點` 的全部介面，以及各介面的主要介面與需求原文依據。

## Phase 2 -- 決定視覺風格
1. THINK 詢問使用者對視覺風格的偏好（由 system-analysis 委派時回傳給呼叫端轉問）；使用者沒意見時，以 ASCII 示意圖提出 2–3 種風格讓使用者選，不先實作；未獲回答前停止。

## Phase 3 -- 設計畫面
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <產出目錄>/frontend.md --file <產出目錄>/prototype/index.html`，取得適用於 frontend.md 與 prototype 的憲法檔清單。
2. THINK 依 `rules/畫面規格-規範.md` 與第 1 步取得的 frontend.md 憲法檔（與 `rules/` 衝突時以憲法為準），為每個前端介面設計畫面與版面、互動與呼叫、錯誤時的畫面反應、即時事件、四態與網址參數。

## Phase 4 -- 寫入
1. WRITE 複製 `templates/frontend.md` 並參照 `templates/frontend.example.md` 改寫填位符號，寫入產出目錄的 `frontend.md`。
2. WRITE 依 `rules/雛形-規範.md` 與 Phase 3 第 1 步取得的 prototype 憲法檔（與 `rules/` 衝突時以憲法為準），以 `templates/prototype/page.html` 為每頁的骨架，參照 `templates/prototype/example/index.html`、`templates/prototype/example/checkout.html`、`templates/prototype/example/complete.html` 與共用的 `templates/prototype/example/assets/style.css`、`templates/prototype/example/assets/app.js`，寫入產出目錄的 `prototype/` 與 `prototype/assets/`。

## Phase 5 -- 驗證
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/coverage_check.py --plan <plan.md> --frontend <frontend.md> --prototype <prototype 目錄> [--openapi <openapi.yaml>] [--asyncapi <asyncapi.yaml>]`，取得缺段落的前端介面、缺少的雛形檔與契約中不存在的 operationId、事件清單。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <frontend.md> --file <prototype 下每個 .html> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule。
3. WRITE 依第 1–2 步的結果修正產出並重跑，並逐條自檢第 2 步列出的 Rule，直到沒有錯誤，最後向呼叫端回報產出路徑、驗證結果、套用的憲法檔與被覆寫的內建 Rule，以及 spec 未規定而自行決定的事項。
