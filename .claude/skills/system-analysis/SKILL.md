---
name: system-analysis
description: 在 /specify 與 /technical-research 產出 spec.md、research.md、techstack.md 之後，要盤點需求涉及的端點與系統介面、規劃 wave 順序並產出 plan.md，再依 wave 把每個端點委派給負責的 planner skill 執行系統分析時，必須使用此 skill。
license: MIT
metadata:
  derived-from: github/spec-kit v1.2.2 templates/commands/plan.md, templates/plan-template.md (MIT, Copyright GitHub, Inc.)
  derived-from-url: https://github.com/github/spec-kit/blob/v1.2.2/templates/commands/plan.md
  attribution: see NOTICE.md
---

# SOP

## Phase 1 -- 讀取需求
1. READ 讀取使用者指定的 `specs/<NNN>-<專案名>/spec.md`，取出 Input 使用者原文與全部 FR / NFR 條目。
2. READ 確認 spec.md 同目錄有 `research.md` 與 `techstack.md`；缺少時請使用者先執行 technical-research，未補齊前停止。

## Phase 2 -- 盤點端點與介面
1. READ 讀取 spec.md 同目錄的 `research.md` 與 `techstack.md`，取出已定案的架構、狀態存放位置與儲存決策。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <spec.md 同目錄>/plan.md`，取得適用於 plan.md 的憲法檔清單。
3. READ 讀取第 2 步取得的每個憲法檔，本 Phase 至 Phase 4 撰寫 plan.md 內容時一併遵守，與 `rules/` 衝突時以憲法為準；清單為空則略過。
4. THINK 從 spec.md 盤點本次需求涉及的端點類型（前端、後端、資料庫、檔案儲存，視需求還有硬體、手機、雲端、第三方等），每個端點視為一個獨立系統。
5. THINK 依 `rules/介面盤點-規範.md` 與第 1 步的決策將每個端點拆成系統介面，寫出每個介面的端點類型、主要介面與需求原文依據；只存在記憶體或其他端點的狀態，不拆成資料表介面。

## Phase 3 -- 安排分析流程
1. THINK 依 `rules/分析流程-規範.md` 將端點依依賴分成多個 wave，寫出每個 wave 的平行分析端點與安排理由。
2. READ 讀取 `.claude/skills/` 底下每個 skill 的 SKILL.md，取得其 description 宣告負責的端點類型與產出檔。
3. THINK 為每個端點選出 description 宣告負責該端點類型的 skill 作為委派 skill；某端點找不到或有多個候選時，向使用者詢問，未獲回答前停止。

## Phase 4 -- 規劃專案結構
1. THINK 依 `rules/專案結構-規範.md`，以 Phase 2 的端點與介面、Phase 3 各委派 skill 的產出檔，自行定義 Documentation 目錄、repository root 下列出每個資料夾內檔案與職責說明的 Source Code 樹，以及 Structure Decision。

## Phase 5 -- 寫入
1. WRITE 複製 `templates/plan.md` 並參照 `templates/plan.example.md` 改寫填位符號，寫入 spec.md 同目錄的 `plan.md`。
2. DELEGATE 以 uv run 執行 constitution skill 的 `affected.py`（位於 `.claude/skills/constitution` 的 scripts 目錄）`--root .claude/constitution --repo <repository root> --file <plan.md 路徑> --check`，取得憲法 script 驗證的違規與需逐條自檢的 Rule；有違規即修正後重跑，並逐條自檢列出的 Rule 並修正。

## Phase 6 -- 執行分析
1. DELEGATE 依 plan.md 的 wave 順序，為同一 wave 的每個端點各開一個子代理平行執行其委派 skill，傳入 spec.md、plan.md、research.md、techstack.md 的路徑、負責的端點類型、產出目錄 `specs/<NNN>-<專案名>/analysis/` 與先前 wave 的全部產出路徑，並收回各子代理回報的產出路徑；子代理回傳需要使用者回答的問題時，轉問使用者並把答案交回同一個子代理繼續，其餘子代理照常執行；一個 wave 的子代理全部完成才進入下一個 wave，除此之外不停下等待使用者確認。

## Phase 7 -- 回檢
1. READ 讀取全部產出並比對 plan.md 的系統介面盤點，確認每個端點都有產出、每個系統介面都在其端點的產出中被分析；有遺漏的端點重新委派一次，仍有遺漏則連同產出清單向使用者回報；回報時一併列出 plan.md 與各子代理回報的套用憲法檔與被覆寫的內建 Rule。
