---
name: bdd-set
description: 要根據一份需求先產生 Gherkin、經使用者 review 通過後，再對每個測試情境逐一以測試驅動開發實作到全部通過時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 確認需求與專案
1. READ 讀取使用者提供的需求，以及專案內既有的 .feature、step definition 與相關領域程式碼。
2. DELEGATE 需求有缺漏、矛盾或多種解讀時交給 clarify 訪談使用者，取得拍板後的需求；需求清楚則略過。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/detect_bdd_stack.py --project <專案根目錄>`，取得 cucumber-js 的 feature 與 step 目錄，以及 lint、產 snippet、跑單一情境、跑全套與列出未使用 step 的指令。
4. WRITE 偵測不到 cucumber-js 時，向使用者確認是否安裝，確認後依 cucumber-js 官方最新文件安裝並設定 TypeScript，再重跑上一步。

## Phase 2 -- 產生 Gherkin 並取得 review
1. THINK 依 `rules/Gherkin-撰寫規範.md` 把需求拆成業務規則，並為每條規則挑出能揭露邊界的具體例子；單一 feature 超過 15 個情境時，先提議拆成多個 feature，由使用者決定這次先做哪一個。
2. WRITE 複製 `templates/feature.feature` 並參照 `templates/feature.example.feature` 改寫填位符號，寫入專案的 feature 目錄，Feature 加上 @wip。
3. DELEGATE 執行 Phase 1 取得的 lint 指令，有違規即修正後重跑；專案沒有 lint 則略過。
4. WRITE 在對話中列出每條規則與其情境的對照請使用者 review，依意見修改後重新提出；未獲明確通過前停止，不寫任何 step 或產品碼。

## Phase 3 -- 逐情境 TDD（依 feature 中的順序，每個情境重複本 Phase，情境之間不停下）
1. DELEGATE 以跑單一情境的指令執行當前情境，取得 undefined 步驟的 snippet。
2. WRITE 依 `rules/Step-實作規範.md` 把 snippet 寫進依領域分檔的 step 檔與其下的 driver，再執行當前情境取得紅燈。
3. THINK 依 `rules/Failure-分類規範.md` 判定紅燈類別；測試端問題修正後回到本步，產品尚未實作或行為不符則進入下一步，Then 的預期與需求衝突則停止並向使用者提出，取得同意前不改 .feature。
4. WRITE 在內層先寫一個失敗的單元測試，再寫最少的產品碼讓它通過，重複到當前情境綠燈。
5. WRITE 重跑本 feature 已通過的情境確認仍綠，再依已讀的實作規範重構 step 與 driver，保持全綠後進入下一個情境。

## Phase 4 -- 收尾
1. WRITE 移除 @wip，以隨機順序執行全套測試，並刪除未被任何情境使用的 step definition。
2. WRITE 向使用者回報每個情境的結果、新增或修改的 step、driver、產品碼與單元測試。
