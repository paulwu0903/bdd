---
name: bdd
description: 在 /dsl-refine 修改 `specs/truth/features/` 的端點 feature 檔與 dsl.md 之後，要在單一端點的一或多個 feature 檔或其中明確區塊（Rule、Example）的範疇內，執行 BDD 的紅燈（/bdd red）、綠燈（/bdd green）、重構（/bdd refactor），或為被修改的 truth 改寫既有測試碼的對齊（/bdd realign）階段時（由使用者直接呼叫，或由 /implement 傳入階段、範疇與 plan 目錄），必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 確認範疇與輸入
1. READ 讀取呼叫者指定的階段（red、green、refactor 或 realign）、plan 目錄（`specs/plans/<NNN>-<專案名>/`）與範疇：`specs/truth/features/<端點>/` 單一端點目錄，或同一端點的一或多個 feature 檔、以 `檔案:行號` 指向的 Rule 或 Example；未指定階段或範疇、或範疇跨多個端點時，請使用者改為單一端點的範疇，未指定前停止；呼叫者為 /implement 時本 skill 全程不向使用者提問，各步原本要詢問使用者之處一律改為停止並回報給呼叫者。
2. DELEGATE 以 uv run 執行 gherkin-and-dsl skill 的 `verify_features.py`（位於 `.claude/skills/gherkin-and-dsl` 的 scripts 目錄）`--feature-dir <端點目錄> --dsl-root <端點目錄> --only-delta <plan 目錄>/truth-delta.md`，只對本 plan 在 truth-delta features 段改過的 feature 檔回報逐檔違規，跨檔檢查仍涵蓋整個端點；缺 dsl.md 或有任何違規時停止，列出違規並交還 /dsl-refine 處理。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/list_slices.py --feature-dir <端點目錄> --dsl-root <端點目錄> --scope <範疇> [--scope <範疇> ...]`，取得範疇內依 feature 順序排列的 slice（Example 或 Scenario Outline 的檔案、行號、Rule、標題、追溯 tag）與每個 slice 用到的 dsl.md 句型。
4. READ 讀取 `specs/truth/techstack.md` 與 plan 目錄的 plan.md，取得該端點的 BDD 框架與程式碼根目錄。
5. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/detect_bdd_stack.py --project <該端程式碼根目錄> --features <端點目錄>`，取得框架（cucumber-js 或 playwright-bdd）、step 目錄、設定是否涵蓋端點目錄，以及產 snippet、dry-run、依 slice 標題執行（跑單一 slice 或跑範疇）、跑全套與列出未使用 step 的指令；偵測不到框架時向使用者確認是否依 techstack.md 安裝，確認後依該框架官方最新文件安裝再重跑本步；設定未涵蓋端點目錄時把它加進設定的 feature 路徑（保留既有路徑，依 script 的 notes 一併調整相關設定）再重跑本步；之後執行 dry-run 確認沒有 ambiguous 步驟，有則停止，列出 ambiguous 的步驟與各自所屬的 feature 與 dsl.md 並交還 /dsl-refine。
6. READ 讀取 slice 用到的 dsl.md 句型列與附錄共通規則、該端既有的 step definition、World 或 fixture、driver 與相關領域程式碼，並讀取各階段共用的規範：`rules/上游缺口-規範.md`（遇到缺口時停止並交還上游的判準）、`rules/Failure-分類規範.md`（red 與 green 判定紅燈類別）、`rules/Step-實作規範.md`（red 撰寫與 refactor 整理 step）；階段為 red 進入 Phase 2，green 進入 Phase 3，refactor 進入 Phase 4，realign 進入 Phase 5。

## Phase 2 -- 紅燈（red）
1. DELEGATE 以產 snippet 的指令對範疇執行，取得尚未定義的步驟與其 snippet。
2. WRITE 依已讀的 Step 實作規範為每個尚未定義的步驟，照 dsl.md 該句型的實作語意寫出 step definition 與其下的 driver 或 fixture，不寫任何產品碼。
3. DELEGATE 以跑範疇的指令執行全部 slice，依已讀的失敗分類與 `rules/紅燈-規範.md` 判定每個 slice 的結果；測試端問題修正後重跑本步，直到每個 slice 都是合格紅燈或已確認的綠燈；遇到已讀的上游缺口判準所定義的缺口時停止並交還 /dsl-refine。
4. WRITE 向使用者回報每個 slice 的紅燈類別與失敗訊息、已綠的 slice 與其確認依據，以及新增或修改的 step、driver 與 fixture。

## Phase 3 -- 綠燈（green）
1. DELEGATE 以跑範疇的指令執行全部 slice；還有未定義的步驟時停止，請使用者先執行 /bdd red；否則依 feature 順序取第一個紅燈 slice，依已讀的失敗分類確認紅燈落在本端產品，測試端問題先修正，紅燈為他端未實作時停止並回報缺的端點與操作、建議先對該端點執行 /bdd，遇到已讀的上游缺口判準所定義的缺口時停止並交還 /dsl-refine。
2. WRITE 依 `rules/綠燈-規範.md` 寫出剛好讓當前 slice 通過的最少產品碼，重跑當前 slice，重複到綠燈。
3. DELEGATE 以跑範疇的指令確認已綠的 slice 都仍通過；有退步即回第 2 步修正產品碼；範疇內還有紅燈 slice 則回第 1 步，slice 之間不停下，全部綠燈後進入下一步。
4. WRITE 向使用者回報每個 slice 的結果，以及新增或修改的產品碼。

## Phase 4 -- 重構（refactor）
1. DELEGATE 以跑範疇的指令執行，確認範疇全綠；有紅燈時停止，請使用者先執行 /bdd green。
2. WRITE 依 `rules/重構-規範.md` 與已讀的 Step 實作規範整理範疇內 slice 涉及的 step、driver、fixture，以及本範疇 green 動到的產品碼，每次改動後重跑範疇保持全綠；需要改 feature 或 dsl.md 才能整理時，依已讀的上游缺口判準列入回報並交還 /dsl-refine，不自行修改。
3. DELEGATE 以列出未使用 step 的指令找出未被該端任何 feature 使用的 step definition 並刪除，再以跑全套的指令確認該端全綠，範疇外尚未實作的 slice（未定義步驟或產品未實作）視為待定、不算失敗；範疇外既有功能的 Example 因本範疇規格刻意改變而失敗時，依已讀的上游缺口判準停止並交還上游，不刪改舊 feature、不從設定移除舊路徑。
4. WRITE 向使用者回報重構的項目、刪除的 step，以及全套的結果。

## Phase 5 -- 對齊（realign）
1. READ 讀取 plan 目錄的 truth-delta.md 中與範疇相關的列、impact-audit.md 的對應項目，以及 `git diff <Base>` 中範疇 Example 與其句型的改前、改後內容。
2. WRITE 依 `rules/對齊-規範.md` 與已讀的 Step 實作規範，改寫範疇所用句型的 step definition 及其下的 driver、helper、fixture、parameter type，使其逐項符合最新的句型語意與 Example 預期，不寫任何產品碼。
3. DELEGATE 以跑範疇的指令執行全部 slice，依已讀的失敗分類判定結果；測試端問題修正後重跑本步，直到每個 slice 都是合格紅燈或已確認的綠燈；遇到已讀的上游缺口判準所定義的缺口時停止並交還 /dsl-refine。
4. DELEGATE 對每個 slice 依已讀的對齊規範，把被修改的預期值暫時改回改前的值重跑，確認會變紅後還原，取得 Then 檢查的是新值的證據。
5. WRITE 向呼叫者回報每個 slice 的結果與證據，以及改寫的 step、driver、helper、fixture 與各自對應的 truth-delta 列。
