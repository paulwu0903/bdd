---
name: dsl-refine
description: 在 /system-analysis 產出 plan.md 與 analysis/ 之後，要以 features/acceptance/ 的驗收 Gherkin 為嚴格依據、並補上 spec.md 中 acceptance 沒涵蓋的需求，推導或原地精修各端點（如前端、後端）可落地的 feature 檔與 dsl.md 時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 確認驗收標準
1. READ 讀取使用者指定的 `specs/<NNN>-<專案名>/features/acceptance/` 全部 feature 檔與同目錄 plan.md 的「系統介面的盤點」；缺少 acceptance 或 plan.md 時，請使用者先執行 /spec-by-example 或 /system-analysis，未補齊前停止。
2. DELEGATE acceptance 仍有 `[NEEDS CLARIFICATION]` 標籤時，交給 clarify skill，依主題檔名順序、檔內標籤出現順序逐題向使用者澄清，以標籤中的暫定答案為推薦選項；標籤超過 5 個時分多個 clarify session；沒有標籤則略過第 2 至 4 步。
3. WRITE 依使用者的回答修改 acceptance 對應的步驟與數字，再依 spec-by-example skill 的 `澄清標籤-規範.md`（位於 `.claude/skills/spec-by-example` 的 rules 目錄）Rule 6 把已解決的標籤改寫成已澄清標籤並留在原位。
4. DELEGATE 以 uv run 執行 spec-by-example skill 的 `check_acceptance.py`（位於 `.claude/skills/spec-by-example` 的 scripts 目錄）`--dir <acceptance 目錄>`，有違規即修正後重跑。

## Phase 2 -- 切出檢查點、補充規格並分配職責
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/list_checkpoints.py --dir <acceptance 目錄>`，取得每個檢查點的追溯鍵、前置步驟、受測的 When 段與 Then 段。
2. READ 讀取同目錄 spec.md 的 FR、NFR、Success Criteria、Edge Cases 與 Assumptions，依 `rules/規格補充-規範.md` 找出 acceptance 檢查點沒涵蓋的需求，並分成可在端點觀察與純量測兩類。
3. THINK 依 `rules/職責分配-規範.md` 把每個檢查點與第 2 步可在端點觀察的需求拆成各端點的職責段，並定出要產出的端點目錄；出現 gherkin-and-dsl skill 尚未定義的端點類型時向使用者詢問，未獲回答前停止。
4. THINK 依 `rules/端點Example推導-規範.md` 為每個端點的每段職責推導端點 Example：判定原子 Example 或 `@journey`、把前置狀態折疊成 Given、寫出 When 與該端的 Then 範圍、要抓的錯誤實作與屬於他端的不必查。

## Phase 3 -- 撰寫端點 feature 與 dsl.md
1. READ 依 `rules/輸入取用-規範.md` 讀取 Phase 2 分配到的上游段落，以及各端點目錄既有的 feature 檔與 dsl.md；techstack.md 找不到該端的 BDD 框架時向使用者詢問，未獲回答前停止。
2. READ 讀取 gherkin-and-dsl skill 的撰寫標準（位於 `.claude/skills/gherkin-and-dsl` 的 rules 與 templates 目錄：分檔、句型、Then 嚴格度、DSL 撰寫、結構規範，以及 dsl 與 feature 的骨架與範例），撰寫時逐條遵守。
3. THINK 端點目錄已有 feature 檔與 dsl.md 時，依 `rules/原地精修-規範.md` 把既有的每個 Example 與 dsl.md 列分成有效、需修正、缺漏、追不回四類。
4. WRITE 依第 2 步的標準寫入或原地更新每個端點的 `specs/<NNN>-<專案名>/features/<端點>/dsl.md` 與各 feature 檔：需要的句型先定義進 dsl.md 再寫進 feature；有效內容保留原寫法；追不回的內容不刪除。

## Phase 4 -- 稽核、把關並回報
1. THINK 依 `rules/覆蓋稽核-規範.md` 逐檢查點、逐條 spec 需求、逐端點雙向比對 acceptance、spec 與端點產出，有缺漏或不一致直接修正 feature 與 dsl.md。
2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_trace.py --acceptance-dir <acceptance 目錄> --features-dir <features 目錄> --spec <spec.md>`，取得未被任何端點覆蓋的檢查點、指向不存在檢查點或 spec 編號的追溯 tag，以及沒有任何 `@spec` Example 的 FR 與 NFR 編號；前兩者有則修正後重跑。
3. DELEGATE 交給 gherkin-and-dsl skill 把關每個端點目錄，取得違規清單；有違規即修正 feature 或 dsl.md 後再交給它把關，直到全部端點無違規。
4. WRITE 在對話中回報產出路徑、各端點的句型數與 Rule／Example 數、檢查點對端點的覆蓋表、spec 每條 FR 與 NFR 的去向（含純量測需求）、acceptance 與上游的衝突及應修正的上游檔、上游缺口、只存在於契約而未寫的項目，以及追不回的內容清單；追不回的內容待使用者確認後才刪除。
