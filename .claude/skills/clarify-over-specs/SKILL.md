---
name: clarify-over-specs
description: 在 /specify 產出 spec.md 之後、進入 /technical-research 之前，要對該 spec.md 做結構化需求澄清並把使用者拍板的答案回寫 spec.md 時，必須使用此 skill。
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/clarify.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/clarify.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 盤點覆蓋
1. READ 讀取使用者指定的 `specs/<NNN>-<專案名>/spec.md`；未指定路徑則詢問使用者，檔案不存在則請使用者先執行 /specify，不自行建立。
2. THINK 依 `rules/覆蓋掃描與排序-規範.md` 對 spec.md 逐類標記 Clear / Partial / Missing 作為內部 coverage map，剔除不該問的缺口，將純技術選型標為 Deferred，並以 Impact × Uncertainty 排出候選缺口清單；全部 Clear 則直接進入 Phase 4。

## Phase 2 -- 委派訪談
1. DELEGATE 交給 clarify，傳入排序後的候選缺口（每個缺口附 taxonomy 類別）作為指定提問面向、剩餘題數預算（整個 session 累計上限 5 題）與兩項指示：每題 Context 第一行標註 `**Taxonomy**：<類別>`；回傳每題的拍板結果與使用者補充。

## Phase 3 -- 回寫與驗證
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 路徑>`，取得適用於 spec.md 的憲法檔清單。
2. WRITE 依 `rules/回寫路由-規範.md` 與第 1 步取得的憲法檔（與 `rules/` 衝突時以憲法為準），把本輪每個拍板結果寫入 spec.md 對應區塊，並在 `## Assumptions` 以「使用者於 YYYY-MM-DD 釐清選擇 X」留痕；每輪寫完立即存檔。
3. DELEGATE 以 uv run 執行 specify skill 的 `spec_lint.py`（位於 `.claude/skills/specify` 的 scripts 目錄）`--spec <spec.md 路徑>`，取得結構違規清單；有違規即修正後重跑。
4. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，並逐條自檢列出的 Rule 並修正。
5. THINK 依本輪答案更新 coverage map；仍有 Partial / Missing 的高影響類別、累計題數未達 5 題且使用者未表示結束，則回到 Phase 2，否則進入 Phase 4。

## Phase 4 -- 完成報告
1. WRITE 複製 `templates/completion-report.md` 並參照 `templates/completion-report.example.md` 改寫填位符號，直接在對話輸出；不寫入檔案；報告後另列套用的憲法檔與被覆寫的內建 Rule。
