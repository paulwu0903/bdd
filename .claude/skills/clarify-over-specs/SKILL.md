---
name: clarify-over-specs
description: 在 /specify 產出 spec.md 之後、進入 /spec-by-example 之前，要對該 spec.md 做結構化需求澄清（含與 `specs/truth/requirements.md` 現行需求的一致性），把使用者拍板的答案回寫 spec.md 並同步 truth 的現行需求時，必須使用此 skill；/spec-by-example、/technical-research 要把使用者已拍板的需求修訂寫回 spec.md 時，也必須以回寫模式委派此 skill。
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/clarify.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/clarify.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 確認模式與讀取
1. READ 讀取使用者或呼叫者指定的 `specs/plans/<NNN>-<專案名>/spec.md`、`specs/truth/requirements.md` 全文與同目錄 truth-delta.md 的 requirements 段；未指定路徑則詢問使用者，spec.md 不存在則請使用者先執行 /specify，不自行建立；由 /spec-by-example 或 /technical-research 傳入已拍板的修訂（每項含修訂內容、使用者拍板日期與出處）時為回寫模式，一併讀取這些修訂。
2. THINK 回寫模式略過 Phase 2 與 Phase 3，以呼叫者傳入的修訂作為本輪拍板結果，直接進入 Phase 4；否則為一般模式，進入 Phase 2。

## Phase 2 -- 盤點覆蓋
1. THINK 依 `rules/覆蓋掃描與排序-規範.md` 對 spec.md 與現行需求逐類標記 Clear / Partial / Missing 作為內部 coverage map，剔除不該問的缺口，將純技術選型標為 Deferred，並以 Impact × Uncertainty 排出候選缺口清單；全部 Clear 則直接進入 Phase 5。

## Phase 3 -- 委派訪談
1. DELEGATE 交給 clarify，傳入排序後的候選缺口（每個缺口附 taxonomy 類別）作為指定提問面向、剩餘題數預算（整個 session 累計上限 5 題）與兩項指示：每題 Context 第一行標註 `**Taxonomy**：<類別>`；回傳每題的拍板結果與使用者補充。

## Phase 4 -- 回寫與同步
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 路徑>`，取得適用於 spec.md 的憲法檔清單。
2. THINK 依 `rules/回寫路由-規範.md` 與第 1 步取得的憲法檔（與 `rules/` 衝突時以憲法為準），為本輪每個拍板結果擬定 spec.md 的落點、改寫內容與 Assumptions 留痕；修改或刪除現行需求者擬為 `## 既有需求異動` 的新列或改寫既有列。
3. DELEGATE 第 2 步擬有新增或改寫的既有需求異動列時，交給 truth-delta 執行「判定影響」，傳入這些列的動作、既有編號與新內容，取得高影響、已確認與低風險清單；本輪已由使用者拍板的列確認欄寫「使用者於 YYYY-MM-DD 確認」；未經使用者拍板的高影響列不寫入，一般模式併入下一輪題目，回寫模式交回呼叫者向使用者確認。
4. WRITE 把第 2 步擬定、且未被第 3 步攔下的內容寫入 spec.md，存檔前依第 2 步的規範逐項自檢並修正；每輪寫完立即存檔。
5. DELEGATE 以 uv run 執行 specify skill 的 `spec_lint.py`（位於 `.claude/skills/specify` 的 scripts 目錄）`--spec <spec.md 路徑>`，取得結構與既有需求異動的違規清單；有違規即修正後重跑。
6. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，並逐條自檢列出的 Rule 並修正。
7. DELEGATE 以 uv run 執行 specify skill 的 `sync_requirements.py`（位於 `.claude/skills/specify` 的 scripts 目錄）`--spec <spec.md 路徑>`，把 spec 的需求與既有需求異動同步到 `specs/truth/requirements.md`。
8. DELEGATE 交給 truth-delta 執行「記錄」，段落為 requirements，依據檔傳入 spec.md 與本輪拍板結果；回報「超出宣告範圍」的項目時，一般模式向使用者確認，回寫模式交回呼叫者，未獲回答前停止。
9. THINK 回寫模式直接進入 Phase 5；一般模式依本輪答案更新 coverage map，仍有 Partial / Missing 的高影響類別、累計題數未達 5 題且使用者未表示結束，則回到 Phase 3，否則進入 Phase 5。

## Phase 5 -- 完成報告
1. WRITE 一般模式複製 `templates/completion-report.md` 並參照 `templates/completion-report.example.md` 改寫填位符號，直接在對話輸出，不寫入檔案，報告後另列套用的憲法檔與被覆寫的內建 Rule；回寫模式不輸出完整報告，改向呼叫者回報 spec.md 改動的區塊、既有需求異動的增減、requirements 段 ADD、MODIFY、DELETE 各幾列，以及交回的高影響與超出宣告範圍項目。
