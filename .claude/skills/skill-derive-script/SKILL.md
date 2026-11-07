---
name: skill-derive-script
description: 給定一個已撰寫 SOP 的 SKILL，使用者想針對某個步驟，把該步驟的職責委派給 Python script 自動執行時，必須呼叫此 skill。
---

# SOP

## Phase 1 -- 確認展開目標
1. READ 讀取目標 skill 的 SKILL.md 與既有 scripts/，鎖定使用者指定的步驟，確認該步是否已有對應 script。

## Phase 2 -- 萃取並寫入腳本
1. THINK 依 `rules/Script-萃取規範.md` 從該步驟的描述與使用者的補充拆出 script 的職責、輸入、輸出，並標記該步原有約束的去向。
2. DELEGATE 交給 skill-form-script，將 script 寫入目標 skill 的 scripts/。

## Phase 3 -- 接回流程
1. DELEGATE 交給 skill-form-sop，依 `rules/Step-接回規範.md` 改寫該步驟描述，承接約束的步驟一併改寫。
2. WRITE 在目標 skill 的 frontmatter 補上 `compatibility: Requires Python >=3.11 and uv`；已有則不改。
3. READ 回頭比對展開前後，確認 script 路徑只在該步被點名一次，除承接約束的步驟外其他步驟未受影響。
