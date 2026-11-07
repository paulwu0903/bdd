---
name: skill-derive-rule
description: 給訂一個已經撰寫的的 SOP 的 SKILL，使用者想要針對某個步驟，去展開該步驟需要遵守的規則，那此時就必須呼叫此 skill。
---

# SOP

## Phase 1 -- 確認展開目標
1. READ 讀取目標 skill 的 SKILL.md 與既有 rules/，鎖定使用者指定的步驟，確認該步是否已有對應規則檔。

## Phase 2 -- 萃取並寫入規則
1. THINK 依 `rules/Rule-萃取規範.md` 從該步驟的描述與使用者的補充拆出候選 Rule。
2. DELEGATE 交給 skill-form-rule，將候選 Rule 寫入目標 skill 的規則檔；已有規則檔則續編號追加。

## Phase 3 -- 接回流程
1. DELEGATE 交給 skill-form-sop，依 `rules/Step-接回規範.md` 改寫該步驟描述。
2. READ 回頭比對展開前後，確認規則檔只在該步被點名一次，其他步驟未受影響。
