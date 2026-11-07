---
name: artifact-to-skill-engineering
description: 要以一份 artifact 範例（可能是別人的 artifact 或規格格式）為起點，客製化後從零建立一個能穩定產出同類 artifact 的新 skill 時，必須使用此 skill。
---

# SOP

## Phase 1 -- 決定參考範例
1. READ 讀取使用者以檔案路徑或貼上內容提供的 artifact 範例，並確認目標 skill 名稱。

## Phase 2 -- 互動客製化範例
1. WRITE 依使用者的客製化需求直接修改範例並寫入目標 skill 的 `templates/<名字>.example.<格式>`，每輪修改後提出仍需調整之處與建議並詢問使用者；未獲使用者確認範例內容已滿意前，持續此步，不進入 Phase 3。

## Phase 3 -- 反向抽取模板
1. DELEGATE 交給 skill-form-template，以定稿範例在目標 skill 的 `templates/` 寫入骨架 `<名字>.<格式>` 與範例 `<名字>.example.<格式>`。

## Phase 4 -- 後設推理流程與規則
1. THINK 以 Phase 3 的骨架與範例為目標，後設出「給定 input prompt 即可穩定產出該 artifact」所需的推理流程與規則草案，並在對話中向使用者提出；未獲明確確認前停止。
2. DELEGATE 交給 skill-engineering，以已確認的草案與 Phase 3 的模板作為新建來源，編排目標 skill 的 SOP、rules，必要時加上 scripts。

## Phase 5 -- 試跑驗證
1. DELEGATE 以子代理用依 `templates/` 範例推得的輸入執行目標 skill，比對產出與範例，確認每條規則都被確實執行；落差根因在目標 skill 時回到 Phase 4 修正後重跑，根因在其他既有 skill 時停止並向使用者回報，不修改既有 skill。
