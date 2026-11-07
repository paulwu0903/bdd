---
name: tdd
description: 在 /implement 執行 tasks.md 中標有 `/tdd 紅燈`、`/tdd 綠燈` 或 `/tdd 重構` 的任務時，必須使用此 skill。
---

# SOP

## Phase 1 -- 讀取任務
1. READ 讀取呼叫者傳入的 TDD 步驟與任務全文，以及任務 Must Read 指定的 test-plan.md 案例卡與 Fixture。
2. READ 讀取專案的 `GLOSSARY.md`（若存在）與將修改區域的 ADR，取得測試名稱與介面要沿用的領域詞彙，以及必須遵守的既有決策；步驟為紅燈時進入 Phase 2，綠燈時進入 Phase 3，重構時進入 Phase 4。

## Phase 2 -- 紅燈
1. WRITE 依 `rules/Test-規範.md`，以案例卡的建立方式、受測操作與 oracle 為該卡寫一個測試。
2. DELEGATE 執行該卡的測試，依 `rules/案例類型-規範.md` 確認結果符合案例類型，完成後結束。

## Phase 3 -- 綠燈
1. WRITE 依 `rules/Boundary-設計規範.md` 寫出剛好讓該卡測試通過的最少實作，不預寫後續案例卡的行為，也不加推測性功能。
2. DELEGATE 執行專案的測試指令與該卡的測試，依 `rules/案例類型-綠燈規範.md` 確認全部測試通過，完成後結束。

## Phase 4 -- 重構
1. READ 讀取專案中記載寫碼標準的文件（`CODING_STANDARDS.md` 或 `CONTRIBUTING.md` 存在時必讀），取得優先於 code smell 的 repo 標準。
2. WRITE 依 `rules/Refactor-規範.md` 在全部測試通過的狀態下整理任務列出的檔案，使其結構良好。
3. DELEGATE 執行專案的測試指令，確認全部測試仍通過。
