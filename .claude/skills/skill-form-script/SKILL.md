---
name: skill-form-script
description: 撰寫 skill 之 scripts/ 底下 Python script 檔時，必須用此 skill。
---

# SOP

## Phase 1 -- 確認目標
1. READ 讀取目標 skill 的 SKILL.md 與既有 scripts/，確認要新增、修改或重寫的 script 名稱、輸入與輸出。

## Phase 2 -- 整理腳本
1. THINK 整理出 script 的最小職責、CLI 參數與第三方相依。
2. READ 讀取 `rules/ScriptFile-格式規範.md` 與 `rules/Dependency-宣告規範.md`，依規範定出檔頭、相依區塊、守衛與錯誤處理的寫法。

## Phase 3 -- 撰寫並回檢
1. WRITE 複製 `templates/script.py` 並參照 `templates/script.example.py` 改寫填位符號，寫入目標 skill 的 `scripts/<name>.py`。
2. DELEGATE 以 uv run 執行剛寫入的 `scripts/<name>.py --help` 做煙霧測試，確認相依可解析且 CLI 可啟動。
3. READ 回頭檢查結果是否符合規範；若不符合，立即修正。
