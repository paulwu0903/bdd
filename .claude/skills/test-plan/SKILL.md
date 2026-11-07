---
name: test-plan
description: 在 /system-analysis 產出 plan.md 與 analysis/ 之後、/tasks 之前，要依 spec.md 與上游產出為各 User Story 規劃切片測試案例並產出 test-plan.md 時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 讀取上游
1. READ 讀取使用者指定的 `specs/<NNN>-<專案名>/spec.md` 的 User Stories、驗收情境、FR、NFR、SC 與 Edge Cases，以及使用者對測試的要求原文。
2. READ 確認 spec.md 同目錄有 `research.md`、`techstack.md`、`plan.md` 與 `analysis/`；缺少時請使用者先執行對應的上游 skill，未補齊前停止。
3. READ 讀取 plan.md 的系統介面盤點與 Source Code 樹、`analysis/` 底下全部產出，以及 research.md 與 techstack.md 中的測試層級、測試工具與執行環境決策；repo 已有測試時一併讀取其測試目錄與 helper。

## Phase 2 -- 定出觀察 seam
1. THINK 依 `rules/觀察seam-規範.md` 從上游定出本功能用到的觀察 seam 及各自的測試層級與工具。
2. THINK 依 `rules/釐清-規範.md` 判定上游未決定、需問使用者的測試決策，逐題附上選項與權衡提問；未獲回答前停止，沒有要問的決策則直接進入 Phase 3。

## Phase 3 -- 推導案例
1. THINK 依 `rules/Fixture-規範.md` 為每個觀察 seam 定出共用的前置狀態與 helper。
2. THINK 依 `rules/TestCase-規範.md` 逐一掃描每個 User Story 範圍內的驗收情境、FR、NFR 與 Edge Cases，推導切片卡並依依賴排序，跨故事旅程與全域 NFR 各自成段。
3. THINK 依 `rules/Oracle-規範.md` 寫出每張卡的主要 oracle、必須維持不變與要抓的錯誤實作。
4. THINK 依 `rules/Coverage-規範.md` 核對範圍內 spec 項目的涵蓋情形，未涵蓋者列入未涵蓋項目。

## Phase 4 -- 寫入並回檢
1. WRITE 複製 `templates/test-plan.md` 並參照 `templates/test-plan.example.md` 改寫填位符號，寫入 spec.md 同目錄的 `test-plan.md`。
2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/test_plan_lint.py --plan <test-plan.md 路徑> --spec <spec.md 路徑> --system-plan <plan.md 路徑>`，取得結構、識別碼與涵蓋的違規清單；有違規即修正後重跑，最後向使用者回報案例數、案例類型分布、未涵蓋項目、由 AI 推定的測試決策與需上游修正的缺漏。
