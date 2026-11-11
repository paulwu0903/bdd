---
name: implement
description: 在 /tasks 產出 tasks.md 之後，要依其 Phase 與任務標記（盤點、/bdd realign、red、green、refactor、移除等）與 Must Read / Optional / Why 契約逐任務實作、證明受影響的既有測試已對齊最新 truth、通過驗證，並在使用者同意後以 git commit 交付整個 plan 時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/implement.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/implement.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 確認輸入、環境與基準
1. READ 讀取使用者指定的 `specs/plans/<NNN>-<專案名>/tasks.md` 的檔首與 Phase 標題，以及使用者補充的程式碼根目錄與任務範圍；只有在 tasks.md 不存在時才交給 tasks skill 產出再繼續，已存在則直接使用；程式碼根目錄未指定時以 repository root 為準。
2. READ 讀取 `specs/truth/techstack.md` 的執行環境，確認本機具備所列的執行時版本與資料庫；缺少時自行安裝、啟動並建立測試資料庫，仍做不到則改採 research.md 已評估的替代方案並記入當責紀錄。
3. DELEGATE 對 `specs/truth/features/` 下的每個端點目錄，以 uv run 執行 gherkin-and-dsl skill 的 `verify_features.py`（位於 `.claude/skills/gherkin-and-dsl` 的 scripts 目錄）`--feature-dir <端點目錄> --dsl-root <端點目錄> --only-delta <plan 目錄>/truth-delta.md`，只對本 plan 在 truth-delta features 段改過的 feature 檔回報逐檔違規，跨檔檢查仍涵蓋整個端點；任一端有違規時不寫任何程式，向使用者列出違規，請其交由 /dsl-refine 修正後重跑。
4. DELEGATE 以各端點的測試一鍵指令執行整個 truth 套件並輸出機器可讀報告，再以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/map_baseline.py --plan <plan 目錄> --report <報告> [--report ...]`，取得每一個失敗對應到的 truth-delta 列，以及對應不到的失敗。
5. THINK 對應不到的失敗先重跑一次排除不穩定；屬於環境問題的自行修復後回到第 4 步；仍有對應不到的失敗時停止，不寫任何程式，向使用者列出失敗的 Example、使用的句型與最可能的來源，請其交由 /dsl-refine 補記或確認為既有問題；使用者確認為既有問題的記為「已知失敗」，與基準一併寫入執行紀錄。

## Phase 2 -- 取得下一批任務
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_batch.py --tasks <tasks.md 路徑> --spec <spec.md 路徑> [--range <任務範圍>]`，取得下一批可執行任務已併入所在 Phase 共用區塊的全文、所在 Phase，以及該批完成後是否到達 Phase 末尾與其 Checkpoint 與 Checkpoint 引用的使用者故事的 Independent Test。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <任務列的檔案路徑> ...`，為批次中每個任務取得其檔案路徑適用的憲法檔清單。

## Phase 3 -- 實作
1. DELEGATE 把批次中的任務依 tasks.md 順序一次一個交給執行子代理（第一個任務開子代理，之後以 SendMessage 交給同一個子代理）；每次傳入該任務全文與憲法檔，首次另傳入程式碼根目錄、plan 目錄、`rules/參照-規範.md`、`rules/完成判準-規範.md` 與 `rules/執行順序-規範.md`；帶 `/bdd <階段>` 標記（含 realign）的任務，子代理以該階段與任務列中的範疇呼叫 bdd skill，並告知呼叫者為 /implement 與 plan 目錄；`盤點` 任務依 `rules/盤點-規範.md` 並參照 `templates/impact-audit.md` 與 `templates/impact-audit.example.md` 寫出 plan 目錄的 `impact-audit.md`；`移除` 任務依 `rules/移除-規範.md` 執行；其餘任務依規範讀取契約、實作、自行驗證並回報；全程不向使用者提問，文件未規定或互相衝突之處由子代理依規範裁決並列入回報。

## Phase 4 -- 驗證與記錄
1. DELEGATE 在程式碼根目錄執行該批任務所屬工作區的型別檢查、lint 與測試一鍵指令，以 Phase 1 的基準與已知失敗為比較基礎自行確認通過；未通過即把錯誤輸出交回同一個子代理修正並重跑，修正滿 3 次仍失敗則另開一個乾淨子代理帶完整失敗紀錄重做 1 次，之後的任務改由這個新子代理接續，仍失敗即由協調者依專業判斷完成並記入當責紀錄；不跳過、不終止、不向使用者提問；例外：子代理回報 bdd skill 因上游缺口或他端未實作而停止，或 `盤點` 任務發現 tasks.md 沒涵蓋的影響時，不重試、不裁決，依第 4 步標記已通過的任務後終止 run，向使用者回報缺口清單與已完成的任務，請其交由 /dsl-refine 修正或重跑 /tasks 後再重跑 /implement。
2. DELEGATE 該批含 `移除` 任務時，以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/check_orphan_routes.py --openapi specs/truth/contracts/openapi.yaml --src <各端原始碼目錄> ...`，取得程式碼中有、truth 契約中沒有的路由與呼叫；有孤兒時依第 1 步的方式交回子代理移除或在回報中說明誤報理由後重跑。
3. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <該批新增或修改的檔案> ... --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；違規與自檢不符依第 1 步的方式交回子代理修正並重跑。
4. DELEGATE 確認批內每個任務都已交回回報，缺任務或缺項即交回該子代理補完；全數齊備後以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/mark_done.py --tasks <tasks.md 路徑> <任務編號 ...>`，把通過的任務標記為 [X]，script 因前置任務未完成而拒絕時先完成前置任務；進度與決策只寫入執行紀錄，批次之間不向使用者輸出摘要。
5. READ 確認本批已依序走完 Phase 2 第 1 步到本步的每一步，有遺漏即補做該步；該批到達 Phase 末尾時讀取該 Phase 的 Checkpoint 與 Independent Test，逐項實際執行確認，全部通過才回到 Phase 2 第 1 步；未通過視同該 Phase 最後一個序列任務失敗，依第 1 步處理；未到 Phase 末尾則直接回到 Phase 2 第 1 步。

## Phase 5 -- 完成回報
1. READ 讀取 tasks.md 確認全部任務已為 [X]，執行整個 truth 套件，以 uv run 執行 dsl-refine skill 的 `check_trace.py`（位於 `.claude/skills/dsl-refine` 的 scripts 目錄）`--plan <plan 目錄>` 檢查本 plan 前綴的檢查點覆蓋與整個 truth 的追溯 tag，並交給 truth-delta 以「檢查」動作確認紀錄與實際異動一致；向使用者回報完成的 Phase 與任務數、上述驗證結果、MODIFY 與 DELETE 的對齊證據摘要、當責紀錄、需上游修正的文件不一致與自行裁決的衝突、任務路徑之外新增或修改的檔案、套用的憲法檔與被覆寫的內建 Rule，以及文件未規定而自行決定的事項。

## Phase 6 -- 交付
1. WRITE 第 5 階段的驗證全部通過時，依 `rules/交付-規範.md` 列出將要 commit 的檔案範圍與 commit message 草稿，詢問使用者是否以 git commit 交付本 plan；任一驗證未通過時不詢問，回報未通過項目；未獲回答前停止。
2. DELEGATE 使用者同意時，交給 truth-delta 以「切換狀態」動作把 Status 改為已交付，再依已確認的範圍與訊息執行 git commit，回報 commit 的雜湊值；使用者不同意時維持實作中並回報。
