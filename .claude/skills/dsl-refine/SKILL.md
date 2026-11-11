---
name: dsl-refine
description: 在 /system-analysis 產出 plan.md 並更新 truth 的契約與資料表之後，要以 plan 的 features/acceptance/ 驗收 Gherkin 為嚴格依據、補上 spec.md 中 acceptance 沒涵蓋的需求，並依既有需求異動在 `specs/truth/features/<端點>/<模組>/` 就地新增、修改或刪除端點 feature 檔、Example 與 dsl.md 句型（含把既有 Example 對齊新需求）時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 確認輸入與驗收標準
1. READ 讀取使用者指定的 plan 目錄 `specs/plans/<NNN>-<專案名>/` 下 `features/acceptance/` 的全部 feature 檔、plan.md 的「系統介面的盤點」、spec.md 的「既有需求異動」，以及 truth-delta.md 的 requirements、contracts、data、features 四段；缺少 acceptance、plan.md 或 truth-delta.md 時，請使用者先執行 /spec-by-example、/system-analysis 或 /specify，未補齊前停止。
2. DELEGATE acceptance 仍有 `[NEEDS CLARIFICATION]` 標籤時，交給 clarify skill，依主題檔名順序、檔內標籤出現順序逐題向使用者澄清，以標籤中的暫定答案為推薦選項；標籤超過 5 個時分多個 clarify session；沒有標籤則略過第 2 至 4 步。
3. WRITE 依使用者的回答修改 acceptance 對應的步驟與數字，再依 spec-by-example skill 的 `澄清標籤-規範.md`（位於 `.claude/skills/spec-by-example` 的 rules 目錄）Rule 6 把已解決的標籤改寫成已澄清標籤並留在原位。
4. DELEGATE 以 uv run 執行 spec-by-example skill 的 `check_acceptance.py`（位於 `.claude/skills/spec-by-example` 的 scripts 目錄）`--dir <acceptance 目錄>`，有違規即修正後重跑。

## Phase 2 -- 切出檢查點、補充規格並分配職責
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/list_checkpoints.py --dir <acceptance 目錄>`，取得每個檢查點帶 plan 前綴的追溯鍵（`@ac:<NNN>/<主題>:<J>-<C>`）、前置步驟、受測的 When 段與 Then 段。
2. READ 讀取 plan 的 spec.md 的 FR、NFR、Success Criteria、Edge Cases、Assumptions 與既有需求異動，依 `rules/規格補充-規範.md` 找出 acceptance 檢查點沒涵蓋的需求（含 MODIFY 的新內容），並分成可在端點觀察與純量測兩類。
3. THINK 依 `rules/職責分配-規範.md` 把每個檢查點與第 2 步可在端點觀察的需求拆成各端點的職責段，並定出涉及的 `specs/truth/features/<端點>/` 目錄；出現 gherkin-and-dsl skill 尚未定義的端點類型時向使用者詢問，未獲回答前停止。
4. THINK 依 `rules/端點Example推導-規範.md` 為每個端點的每段職責推導端點 Example：判定原子 Example 或 `@journey`、把前置狀態折疊成 Given、寫出 When 與該端的 Then 範圍、要抓的錯誤實作與屬於他端的不必查。

## Phase 3 -- 盤點既有 truth 並判定影響
1. READ 依 `rules/輸入取用-規範.md` 讀取 Phase 2 分配到的上游段落，以及涉及端點在 `specs/truth/features/<端點>/` 下全部 dsl.md 與 feature 檔的規定範圍；`specs/truth/techstack.md` 找不到該端的 BDD 框架時向使用者詢問，未獲回答前停止。
2. THINK 由既有需求異動的 MODIFY、DELETE 與 truth-delta contracts、data 段的 MODIFY、DELETE，寫出改變的需求編號，以及舊值在 truth 中實際出現的各種寫法（數值加單位、拒絕原因文字、`預設為 <值>`），作為影響搜尋的字面值；沒有 MODIFY、DELETE 則略過第 2 至 6 步。
3. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/find_impact.py --plan <plan 目錄> [--id <NNN/FR-nnn> ...] --term <字面值> [--term ...]`，取得整個 truth 端點中以 `@spec` tag、字面值與句型使用處三種信號找到的候選 Example 與 dsl.md 列，部位為 truth-delta features 段的格式。
4. THINK 依 `rules/異動判定-規範.md` 把每個候選判為需修正、刪除或不受影響，找出本 plan 檢查點已被既有 Example 驗到而只需改寫的項目與連帶影響，列出預計的 MODIFY、DELETE 清單（部位與改動內容）。
5. DELEGATE 交給 truth-delta 執行「判定影響」，傳入 plan 目錄與第 4 步的 MODIFY、DELETE 清單，取得需先交給 clarify 的高影響項目、已確認項目與低風險項目。
6. DELEGATE 有高影響項目，或有超出既有需求異動與本次 acceptance 範圍的連帶影響時，交給 clarify skill 逐項附上選項與權衡比較向使用者確認；未拍板前不修改這些項目，使用者不同意的項目移出本次修改；沒有則略過。

## Phase 4 -- 撰寫端點 feature 與 dsl.md
1. READ 讀取 gherkin-and-dsl skill 的撰寫標準（位於 `.claude/skills/gherkin-and-dsl` 的 rules 與 templates 目錄：分檔、句型、Then 嚴格度、DSL 撰寫、結構規範，以及 dsl 與 feature 的骨架與範例），撰寫時逐條遵守。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <本次要寫入的 truth feature 檔或 dsl.md 路徑> ...`，取得適用於這些檔案的憲法檔清單；檔案尚未建立時只比對路徑。
3. READ 讀取第 2 步取得的每個憲法檔，本 Phase 後續各步撰寫時一併遵守，與 `rules/` 衝突時以憲法為準；清單為空則略過。
4. WRITE 依 Phase 2 的推導與 Phase 3 的判定，就地寫入 `specs/truth/features/<端點>/<模組>/` 的 feature 檔與 dsl.md：ADD 的 Example 寫進對應模組，需修正的就地改值與換 tag，刪除的連同只被它使用的句型一起移除；需要的新句型先定義進註冊它的模組 dsl.md 再寫進 feature；更新被寫入的 feature 檔頭來源註解，加入本 plan 目錄。
5. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <第 4 步新增或修改的檔案> ... --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，逐條自檢列出的 Rule 並修正。

## Phase 5 -- 稽核、把關、記錄並回報
1. THINK 依 `rules/覆蓋稽核-規範.md` 逐檢查點、逐條本 plan 需求與既有需求異動、逐端點雙向比對 acceptance、spec 與端點產出，有缺漏或不一致直接修正 feature 與 dsl.md。
2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_trace.py --plan <plan 目錄>`，取得本 plan 未被任何端點覆蓋的檢查點、整個 truth 中沒有前綴或指向不存在檢查點或需求的追溯 tag，以及本 plan 的 ADD 與 MODIFY 需求中沒有任何 `@spec` Example 的編號；前兩者有則修正後重跑。
3. DELEGATE 交給 gherkin-and-dsl skill 把關每個涉及的端點目錄，只回報清單為本 plan 在 Phase 4 新增或修改的 feature 檔，取得違規清單；有違規即修正 feature 或 dsl.md 後再交給它把關，直到沒有違規。
4. DELEGATE 交給 truth-delta 執行「記錄」，段落為 features，依據檔傳入 spec.md、acceptance 目錄與 clarify 拍板結果，並傳入本次發現、不在本次解決的上游衝突寫入待和解；回報「超出宣告範圍」的項目時向使用者確認，未獲回答前停止。
5. WRITE 在對話中回報寫入的檔案路徑、各端點的句型數與 Rule／Example 數、檢查點對端點的覆蓋表、本 plan 每條 FR 與 NFR 的去向（含純量測需求）、既有需求異動每一列的落點、features 段 ADD、MODIFY、DELETE 各幾列、寫入待和解的上游衝突、上游缺口、只存在於契約而未寫的項目，以及套用的憲法檔與被覆寫的內建 Rule。
