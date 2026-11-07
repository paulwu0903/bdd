# Truth Delta: 004-full-amount-gift

**Plan**: `specs/plans/004-full-amount-gift`
**Branch**: `004-full-amount-gift`
**Base**: `3f2a9c1d8e7b6a5f4e3d2c1b0a9f8e7d6c5b4a39`
**Status**: 實作中

## /specify — truth/requirements.md

| 動作 | 部位 | 摘要 | 原因 |
|---|---|---|---|
| ADD | `004/FR-001` | 結帳時訂單金額達門檻即自動加贈一份贈品 | spec.md 使用者故事 1 |
| ADD | `004/FR-002` | 贈品庫存不足時照常結帳，只是不加贈並告知會員 | spec.md 使用者故事 1 |
| MODIFY | `002/FR-006` | 訂單明細只列商品 → 訂單明細同時列出商品與贈品 | spec.md 既有需求異動 #1 |
| DELETE | `003/FR-009` | 會員不再能在結帳後自行取消贈品 | spec.md 既有需求異動 #2 |

## /technical-research — truth/techstack.md

| 動作 | 部位 | 摘要 | 原因 |
|---|---|---|---|
| ADD | `Runtime Dependencies / decimal.js` | 以十進位計算門檻金額，避免浮點誤差 | research 004/R3 |
| MODIFY | `Runtime Dependencies / zod` | 4.5.0 → 4.6.7，支援以 refine 驗證贈品規則 | research 004/R2 |

## /api-plan — truth/contracts/

| 動作 | 部位 | 摘要 | 原因 |
|---|---|---|---|
| ADD | `openapi.yaml › operationId applyGift` | 結帳時依訂單金額自動加贈符合門檻的贈品 | 004/FR-001 |
| MODIFY | `openapi.yaml › components.schemas.Order` | 回應只有 items → 回應新增 gifts 陣列 | spec.md 既有需求異動 #1 |
| MODIFY | `openapi.yaml › components.schemas.Error` | 錯誤碼新增 GIFT_OUT_OF_STOCK | 004/FR-002 |
| DELETE | `openapi.yaml › operationId cancelGift` | 會員不再能自行取消贈品 | clarify 2026-11-06：移除取消贈品 |
| ADD | `openapi.yaml › tags.贈品 API 介面` | 新增贈品相關 API 的分組 | plan.md 系統介面盤點 › 贈品 API 介面 |

## /data-plan — truth/data/

| 動作 | 部位 | 摘要 | 原因 |
|---|---|---|---|
| ADD | `schema.dbml › Table gift_grants` | 記錄每筆訂單實際發放的贈品 | 004/FR-001 |
| ADD | `schema.dbml › Table gift_grants.granted_at` | 記錄贈品發放時間，供客服查詢 | 004/FR-001、research 004/R4 |
| DELETE | `schema.dbml › Table order_gifts.cancelled_at` | 不再記錄贈品取消時間 | 連帶：openapi.yaml › operationId cancelGift |

## /dsl-refine — truth/features/

| 動作 | 部位 | 摘要 | 原因 |
|---|---|---|---|
| ADD | `backend/贈品/滿額加贈.feature` | 驗證達門檻加贈、未達不加贈與庫存不足照常結帳 | acceptance @ac:004/滿額贈品:1-1、004/FR-002 |
| MODIFY | `backend/訂單/訂單明細.feature › Rule: 訂單明細必須列出購買內容 › Example: 阿明查看剛完成的訂單` | 明細只驗商品 → 同時驗商品與贈品 | spec.md 既有需求異動 #1 |
| DELETE | `backend/贈品/取消贈品.feature` | 移除會員自行取消贈品的驗證 | clarify 2026-11-06：移除取消贈品 |
| ADD | `backend/贈品/dsl.md › Given › 贈品 {贈品名稱} 庫存剩 {數量} 份` | 準備贈品庫存的前置句型 | 連帶：backend/贈品/滿額加贈.feature |
| MODIFY | `backend/平臺共用/dsl.md › Given › {會員} 的購物車有以下商品：` | 由訂單模組搬到平臺共用，句型與語意不變 | 連帶：backend/贈品/滿額加贈.feature |

## 待和解

| # | 部位 | 衝突內容 | 建議 owner | 狀態 | 處理紀錄 |
|---|---|---|---|---|---|
| 1 | `backend/訂單/dsl.md › Then › 訂單 {訂單編號} 的金額為 {金額} 元` | 句型說明寫「含運費」，實作的斷言不含運費 | /dsl-refine | 待處理 | |
| 2 | `schema.dbml › Table orders.discount_total` | 欄位說明寫「折扣後金額」，openapi 的 Order.discountTotal 寫「折扣金額」 | /data-plan | 延後 | 等 006 折扣重構時一併釐清 |
