---
name: ui-plan
description: 要為 plan 中 `前端端點` 的前端介面（新增、修改既有或刪除既有），依 truth 契約、truth features 與現行前端程式規劃畫面規格與可操作的視覺雛形，產出 plan 目錄 `ui/` 下的 frontend.md 與 prototype/*.html 時（含由 system-analysis 委派），必須使用此 skill；本 skill 只產出 plan 文件，不修改 `specs/truth/`。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取輸入
1. READ 讀取呼叫端傳入的 plan 目錄中的 spec.md（含既有需求異動）、plan.md、research.md、truth-delta.md 的 requirements 與 contracts 段、`specs/truth/techstack.md`，以及 `specs/truth/contracts/` 下的 openapi.yaml 與 asyncapi.yaml；產出目錄為 `<plan 目錄>/ui/`；單獨使用時向使用者取得 plan 目錄。
2. READ 從 plan.md 的系統介面盤點取出端點類型為 `前端端點` 的全部介面，以及各介面的異動、主要介面（含修改既有、刪除既有介面標出的現行程式與 features 模組）與需求原文依據。
3. READ 讀取 repository 現行前端程式的樣式 token、元件與頁面，以及第 2 步標出的程式檔與 `specs/truth/features/frontend/<模組>/` 的 feature 檔；沒有前端程式時視為首次建立。

## Phase 2 -- 決定視覺風格
1. THINK 已有前端程式且 spec.md 沒有要求改變視覺風格時，沿用 Phase 1 第 3 步讀到的樣式 token，不詢問使用者；否則詢問使用者對視覺風格的偏好（由 system-analysis 委派時回傳給呼叫端轉問），使用者沒意見時，以 ASCII 示意圖提出 2–3 種風格讓使用者選，不先實作；未獲回答前停止。

## Phase 3 -- 設計畫面
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <產出目錄>/frontend.md --file <產出目錄>/prototype/index.html`，取得適用於 frontend.md 與 prototype 的憲法檔清單。
2. THINK 依 `rules/畫面規格-規範.md` 與第 1 步取得的 frontend.md 憲法檔（與 `rules/` 衝突時以憲法為準），為新增的前端介面設計畫面與版面、互動與呼叫、錯誤時的畫面反應、即時事件、四態與網址參數；為修改既有、刪除既有的前端介面，以現行程式與 truth features 為基準寫出每個受影響畫面的現況與本次；truth-delta contracts 段中 ADD、MODIFY 的 operation 或 message 不影響畫面時，列入不影響畫面的契約異動並寫出理由。

## Phase 4 -- 寫入
1. WRITE 複製 `templates/frontend.md` 並參照 `templates/frontend.example.md` 改寫填位符號，寫入產出目錄的 `frontend.md`。
2. WRITE 依 `rules/雛形-規範.md` 與 Phase 3 第 1 步取得的 prototype 憲法檔（與 `rules/` 衝突時以憲法為準），以 `templates/prototype/page.html` 為每頁的骨架，參照 `templates/prototype/example/index.html`、`templates/prototype/example/checkout.html`、`templates/prototype/example/complete.html` 與共用的 `templates/prototype/example/assets/style.css`、`templates/prototype/example/assets/app.js`，寫入產出目錄的 `prototype/` 與 `prototype/assets/`。

## Phase 5 -- 驗證
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/coverage_check.py --plan <plan.md> --frontend <產出目錄>/frontend.md --prototype <產出目錄>/prototype [--openapi specs/truth/contracts/openapi.yaml] [--asyncapi specs/truth/contracts/asyncapi.yaml] --delta <plan 目錄>/truth-delta.md`，取得缺段落的前端介面、未列入「本次異動的既有畫面」的修改既有與刪除既有介面、缺少的雛形檔、契約中不存在的 operationId 與事件、本次新增或修改卻未被畫面引用的契約，以及已刪除卻仍被引用的契約。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <frontend.md> --file <prototype 下每個 .html> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule。
3. WRITE 依第 1–2 步的結果修正產出並重跑，並逐條自檢第 2 步列出的 Rule，直到沒有錯誤，最後向呼叫端回報產出路徑、驗證結果、套用的憲法檔與被覆寫的內建 Rule、沿用既有風格或使用者選定的風格，以及 spec 未規定而自行決定的事項。
