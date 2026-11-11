---
name: truth-delta
description: truth owner skill（specify、clarify-over-specs、technical-research、api-plan、data-plan、dsl-refine）要修改既有 `specs/truth/` 前判定 MODIFY／DELETE 的影響、改完 truth 後把異動記入 plan package 的 truth-delta.md，或 specify、tasks、implement、system-analysis 要建立、檢查 truth-delta.md 及切換其 Status 時，必須使用此 skill；truth owner 每次改完 truth 都必須委派本 skill 記錄。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 確認動作
1. READ 讀取呼叫者傳入的動作（建立、判定影響、記錄、檢查、切換狀態）與 plan package 路徑，以及動作所需的參數：建立需 branch 名稱；判定影響需預計的 MODIFY、DELETE 清單（含部位與改動內容）；記錄需段落（requirements、techstack、contracts、data、features 之一）與本次修改的依據檔路徑；檢查可指定段落；切換狀態需目標 Status。
2. THINK 依動作決定路線：建立只走 Phase 2；判定影響只走 Phase 3；記錄走 Phase 4 全部步驟；檢查只走 Phase 4 第 1 步；切換狀態只走 Phase 5。

## Phase 2 -- 建立
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/init_delta.py --plan <plan 目錄> --branch <branch 名稱>`，建立 truth-delta.md：Base 為目前 HEAD 的 commit、Status 為規劃中、五個異動段落都沒有列，並把上一個已交付 plan 的待和解段落中標為「延後」的項目接續到本 plan；檔案已存在時不覆寫，回報既有的 Base 與 Status。
2. WRITE 向呼叫者回報 truth-delta.md 的路徑、Base 與接續的待和解項目數。

## Phase 3 -- 判定影響
1. THINK 依 `rules/影響判定-規範.md` 逐項判定呼叫者預計的 MODIFY、DELETE 為高影響或低風險；已在 spec.md「既有需求異動」中由使用者確認的項目標為「已確認」。
2. WRITE 向呼叫者回報三份清單：需先交給 clarify 的高影響項目、已確認項目、可直接修改的低風險項目；呼叫者取得 clarify 的拍板結果後才修改高影響項目。

## Phase 4 -- 記錄與檢查
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_delta.py --plan <plan 目錄> [--section <段落> ...]`，以語義單元比對 truth-delta.md 與「Base 到工作目錄」之間 `specs/truth/` 的實際異動，取得：未記錄的異動（含動作、標準部位與改前改後內容）、動作或部位與實際不符的列、已記錄卻沒有異動的列、同一部位重複的列，以及摘要或原因留空的列；動作為檢查時把結果直接交回呼叫者，不執行後續步驟。
2. THINK 依 `rules/摘要-規範.md`，為每個未記錄的異動與摘要留空的列寫出摘要。
3. THINK 依 `rules/原因-規範.md`，從呼叫者傳入的依據檔與 clarify 拍板結果，為每個未記錄的異動與原因留空的列找出原因；找不到依據的異動列為「超出宣告範圍」，交回呼叫者向使用者確認，不自行寫入。
4. WRITE 依 `templates/truth-delta.md` 的段落格式並參照 `templates/truth-delta.example.md` 更新該段落：未記錄的語義單元追加在段落末尾；已存在的就地更新動作、摘要與原因；刪除已無異動的列。
5. WRITE 依 `rules/待和解-規範.md`，把本次發現、但不在本次範圍內解決的定義衝突寫入待和解段落，並把本次已解決的既有項目標為「已處理」。
6. THINK 回到第 1 步重跑，直到沒有違規，或只剩交回呼叫者的「超出宣告範圍」項目。
7. WRITE 向呼叫者回報該段落 ADD、MODIFY、DELETE 各幾列、「超出宣告範圍」項目，以及新增的待和解項目。

## Phase 5 -- 切換狀態
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/set_status.py --plan <plan 目錄> --status <實作中|已交付>`，依「規劃中 → 實作中 → 已交付」的順序更新 Status，不允許倒退或跳過；改為已交付時，異動段落不能有摘要或原因留空的列，待和解的每一項都必須已標為「已處理」或「延後」。
