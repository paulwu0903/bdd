---
name: technical-research
description: 在 /spec-by-example 之後，要為 plan 的 spec.md（含既有需求異動）定案實作所需的技術決策，產出只含本次增量的 `specs/plans/<NNN>-<專案名>/research.md`，並就地更新 `specs/truth/techstack.md` 時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 列出研究題目
1. READ 讀取使用者指定的 `specs/plans/<NNN>-<專案名>/spec.md`（未指定則詢問使用者）的 FR、NFR、Success Criteria、Edge Cases、Assumptions 與既有需求異動，同目錄 truth-delta.md 的 requirements 段，`specs/truth/techstack.md` 全文（不存在時視為沒有現行技術堆疊），以及 `specs/truth/` 中引用、且與本次需求或既有需求異動相關的 `research NNN/Rn` 所在的既有 R 節。
2. THINK 依 `rules/研究題目-規範.md` 逐條掃描 spec 的需求與既有需求異動，列出本次實作前必須定案的技術決策作為研究題目（含因既有需求異動而必須重新決定的既有決策），並為每題列出候選方案。

## Phase 2 -- 查證候選方案
1. READ 依 `rules/查證-規範.md` 向官方來源讀取每個候選方案的最新版本、相依需求、瀏覽器支援、授權（含遞移依賴）與最後發佈日，記下每項事實的來源 URL。

## Phase 3 -- 釐清
1. THINK 依 `rules/釐清-規範.md` 判定要向使用者提問的決策與查證後發現 spec 需修訂之處，逐題附上選項與權衡比較提問；未獲回答前停止，不寫 research.md；沒有要問的則直接進入 Phase 4。
2. DELEGATE 使用者同意修訂 spec 時，交給 clarify-over-specs 執行回寫模式，傳入 spec.md 路徑與每項修訂（修訂內容、使用者拍板日期、出處為對應的研究題目），取得 spec.md 改動的條目與 requirements 段的異動列數；回寫模式交回高影響或超出宣告範圍的項目時，向使用者確認後再委派，未獲回答前停止。
3. WRITE 有修訂時依 `rules/spec修訂-規範.md` 比對 acceptance feature 檔，向使用者回報受修訂影響的情境。

## Phase 4 -- 寫入並回檢 research.md
1. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 同目錄>/research.md --file specs/truth/techstack.md`，取得適用於 research.md 與 techstack.md 的憲法檔清單。
2. THINK 依 `rules/決策條目-規範.md` 與第 1 步取得的 research.md 憲法檔（與 `rules/` 衝突時以憲法為準），為本次每個研究題目寫出 Decision、Rationale、補充欄（含取代既有決策的 `**取代**`）與 Alternatives considered；撰寫時發現需要使用者決定的問題，回到 Phase 3 第 1 步提問。
3. THINK 依 `rules/依賴授權-規範.md` 整理本次新增或變更版本的 runtime 依賴授權表。
4. WRITE 複製 `templates/research.md` 並參照 `templates/research.example.md` 改寫填位符號，寫入 spec.md 同目錄的 `research.md`，只含本次的題目；Sources 列出查證時用到的每個 URL。
5. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/research_lint.py --research <research.md 路徑>`，取得結構違規清單；有違規即修正後重跑。
6. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <research.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，並逐條自檢列出的 Rule 並修正。

## Phase 5 -- 更新技術堆疊 truth
1. THINK 依 `rules/技術堆疊-規範.md` 與 Phase 4 第 1 步取得的 techstack.md 憲法檔（與 `rules/` 衝突時以憲法為準），比對本次 research.md 各 R 節的 Decision 與 `specs/truth/techstack.md`，列出要新增、修改、刪除的執行環境與套件列（分成 Runtime 與 Dev），以及 Source 要追加的連結。
2. DELEGATE 第 1 步有修改或刪除既有列時，交給 truth-delta 執行「判定影響」，傳入這些列的動作、部位與改動內容，取得高影響、已確認與低風險清單。
3. DELEGATE 有高影響項目時交給 clarify，逐題附上選項與權衡向使用者提問，取得拍板結果；使用者不同意的項目移出本次範圍，回到 Phase 4 第 2 步修正對應的 R 節。
4. WRITE `specs/truth/techstack.md` 不存在時，複製 `templates/techstack.md` 並參照 `templates/techstack.example.md` 改寫填位符號建立；存在時就地套用第 1 步經確認的增改刪並追加 Source 連結，其餘列原樣保留。
5. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/techstack_lint.py --techstack specs/truth/techstack.md --plan <plan 目錄>`，取得結構違規，以及相對 plan Base 有變動的列與本次 research.md 不一致之處；有違規即修正後重跑。
6. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file specs/truth/techstack.md --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，逐條自檢列出的 Rule 並修正。
7. DELEGATE 交給 truth-delta 執行「記錄」，段落為 techstack，依據檔傳入 research.md 與第 3 步的拍板結果；techstack 沒有異動時同樣執行，記錄零列；回報「超出宣告範圍」的項目時向使用者確認，未獲回答前停止。
8. WRITE 向使用者回報 research.md 路徑、本次開的題目與 `**取代**` 的既有決策、techstack 段 ADD、MODIFY、DELETE 各幾列、套用的憲法檔與被覆寫的內建 Rule，以及下一步為 /system-analysis。
