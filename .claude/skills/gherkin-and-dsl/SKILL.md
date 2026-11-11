---
name: gherkin-and-dsl
description: 要撰寫或檢查 `specs/truth/features/<端點>/<模組>/` 下端點（如前端、後端）的 Gherkin feature 檔與 dsl.md 是否合乎可落地到 step definition 的標準（含模組歸屬、句型只定義一次與追溯 tag 的 plan 前綴）時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 讀取受檢產出
1. READ 讀取使用者或呼叫者指定的一到多個端點目錄 `specs/truth/features/<端點>/` 底下各模組資料夾的全部 feature 檔與 dsl.md，以及呼叫者指定的只回報檔案清單（feature 檔路徑，或 plan 的 truth-delta.md）；確認每個目錄的端點類型（前端或後端），只依這些檔案檢查，不讀取其他規格文件；有只回報清單時，語意違規只回報清單內的 feature 檔與本次新增或修改的 dsl.md 列。

## Phase 2 -- 檢查撰寫標準
1. THINK 依 `rules/分檔-規範.md` 檢查各端點 feature 檔的切分、檔名與模組歸屬，以及句型與附錄所在的 dsl.md。
2. THINK 依 `rules/句型-規範.md` 檢查每個步驟的句子、參數與引號。
3. THINK 依 `rules/Then嚴格度-規範.md` 與 `rules/DSL撰寫-規範.md` 檢查 dsl.md 每一列的參數、預設參數與 StepDef 實作語意。
4. THINK 依 `rules/結構-規範.md` 檢查每個 feature 檔的層級、Rule 名稱、追溯 tag、Example 名稱、Data Table、預設值註解、Background 與 Scenario Outline。
5. THINK 對照 `templates/dsl.md` 與 `templates/dsl.example.md` 檢查每份 dsl.md 的段落、欄位與各關鍵字實作語意的固定小標。
6. THINK 對照 `templates/feature.md` 與 `templates/feature.example.md` 檢查每個 feature 檔的排版、來源註解與縮排。

## Phase 3 -- 機械檢查並回報
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/verify_features.py --feature-dir <端點目錄> --dsl-root <端點目錄> [--only <feature 檔> ...] [--only-delta <truth-delta.md>]`，每個端點目錄各執行一次，呼叫者有指定只回報清單時才帶 `--only` 或 `--only-delta`，取得機械檢查的違規清單與句型數、Rule／Example 數。
2. WRITE 在對話中依端點回報 Phase 2 的語意違規與 Phase 3 第 1 步的機械違規，每項列出檔案與行號或句型、違反的 Rule 或檢查碼，以及一句修正方向，並附各端點的句型數與 Rule／Example 數；不修改任何檔案。
