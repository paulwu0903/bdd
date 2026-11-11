---
name: api-plan
description: 要為 plan 中 `後端端點` 的系統介面（新增、修改既有或刪除既有）設計 HTTP API 與即時事件契約，在 `specs/truth/contracts/` 就地新增、修改或刪除 openapi.yaml 與有即時事件時的 asyncapi.yaml，並委派 truth-delta 判定影響與記錄 contracts 段時（含由 system-analysis 委派），必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取輸入
1. READ 讀取呼叫端傳入的 plan 目錄中的 spec.md（含既有需求異動）、plan.md、research.md（含各決策的 `**取代**` 欄位）、truth-delta.md 的 requirements 與 techstack 段，以及 `specs/truth/techstack.md`；單獨使用時向使用者取得 plan 目錄。
2. READ 從 plan.md 的系統介面盤點取出端點類型為 `後端端點` 的全部介面，以及各介面的異動、主要介面與需求原文依據。
3. READ 讀取 `specs/truth/contracts/` 下 openapi.yaml 與 asyncapi.yaml 的全文；檔案不存在時視為首次建立。

## Phase 2 -- 設計契約
1. READ 首次建立時讀取 OpenAPI（spec.openapis.org）與 AsyncAPI（asyncapi/spec 的 GitHub release）的官方來源，確認最新版本；既有檔沿用原本的 `openapi`、`asyncapi` 版本，只有 research.md 有升級決策時才修改，`info.version` 一律不改。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file specs/truth/contracts/openapi.yaml --file specs/truth/contracts/asyncapi.yaml`，取得適用於 openapi.yaml 與 asyncapi.yaml 的憲法檔清單。
3. THINK 依 `rules/契約設計-規範.md` 與第 2 步取得的憲法檔（與 `rules/` 衝突時以憲法為準），依各後端介面的異動設計 HTTP API 或即時事件：新增的寫出完整 schema、業務規則、交易與錯誤碼，修改既有與刪除既有的以 truth 現況為基準，並掃描連帶影響，整理成以語義單元為部位（如 `openapi.yaml › operationId <id>`、`openapi.yaml › components.schemas.<名稱>`、`openapi.yaml › tags.<介面>`）的 ADD、MODIFY、DELETE 清單；有需要使用者決定的問題時，回傳給呼叫端轉問（單獨使用時直接詢問使用者），未獲回答前停止。
4. DELEGATE 清單有 MODIFY 或 DELETE 時交給 truth-delta 執行「判定影響」，傳入 plan 目錄與每一項的部位與改動內容，取得需先交給 clarify 的高影響項目、已確認項目與低風險項目。
5. DELEGATE 有高影響項目或連帶影響超出宣告範圍的項目時，由 system-analysis 委派的情境下回傳給呼叫端交給 clarify，單獨使用時直接交給 clarify 訪談使用者，取得拍板結果；未獲拍板前不修改這些項目，使用者不同意的項目移出清單。

## Phase 3 -- 寫入並驗證
1. WRITE 依定案的清單就地修改 `specs/truth/contracts/openapi.yaml`（有即時事件時含 `asyncapi.yaml`），只改清單中的部位，不整份重寫；檔案不存在時才複製 `templates/openapi.yaml` 並參照 `templates/openapi.example.yaml` 改寫填位符號建立，需要即時事件而 asyncapi.yaml 不存在時，同樣以 `templates/asyncapi.yaml` 與 `templates/asyncapi.example.yaml` 建立。
2. DELEGATE 在 scratchpad 目錄執行 `npx @redocly/cli lint --extends=minimal <openapi.yaml>`，有 asyncapi.yaml 時再執行 `npx @asyncapi/cli validate <asyncapi.yaml>`，取得語法錯誤清單。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/coverage_check.py --plan <plan.md> --openapi specs/truth/contracts/openapi.yaml [--asyncapi specs/truth/contracts/asyncapi.yaml] --requirements specs/truth/requirements.md`，取得新增或修改既有卻缺 tag、刪除既有卻仍有 tag 或 operation 的介面，對應需求缺漏、不帶前綴或不在現行需求中的 API，缺錯誤碼說明的錯誤回應，沒有被引用的 components，以及 `Error.code` 與各回應錯誤碼不一致的清單。
4. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file specs/truth/contracts/openapi.yaml [--file specs/truth/contracts/asyncapi.yaml] --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule。
5. WRITE 依第 2–4 步的結果修正 truth 契約並重跑，並逐條自檢第 4 步列出的 Rule，直到沒有錯誤。
6. DELEGATE 交給 truth-delta 執行「記錄」，段落為 contracts，依據檔傳入 spec.md、plan.md、research.md 與 clarify 的拍板結果；回報「超出宣告範圍」的項目時，比照 Phase 2 第 5 步取得拍板，確認不納入的項目還原後從第 2 步重跑。
7. WRITE 向呼叫端回報修改的 truth 契約路徑、驗證結果、contracts 段 ADD、MODIFY、DELETE 各幾列、經 clarify 拍板的項目、套用的憲法檔與被覆寫的內建 Rule，以及 spec 未規定而自行決定的事項。
