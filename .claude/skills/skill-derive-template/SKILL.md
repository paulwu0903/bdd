---
name: skill-derive-template
description: 給定一個已撰寫 SOP 的 SKILL，使用者想針對某個步驟，把該步驟對產出檔案格式的要求抽成 template 時，必須呼叫此 skill。
---

# SOP

## Phase 1 -- 確認展開目標
1. READ 讀取目標 skill 的 SKILL.md 與既有 templates/，鎖定使用者指定的步驟，確認該步是否已有對應樣板。

## Phase 2 -- 萃取並寫入樣板
1. THINK 依 `rules/Template-萃取規範.md` 從該步驟的描述與使用者的補充拆出骨架的固定結構與填位符號。
2. DELEGATE 交給 skill-form-template，將骨架與範例寫入目標 skill 的 templates/。

## Phase 3 -- 接回流程
1. DELEGATE 交給 skill-form-sop，依 `rules/Step-接回規範.md` 改寫該步驟描述。
2. READ 回頭比對展開前後，確認骨架與範例兩個路徑都只在該步被點名一次，其他步驟未受影響。
