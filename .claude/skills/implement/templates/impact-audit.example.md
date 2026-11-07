# Impact Audit: 004-full-amount-gift

**Baseline**: 2026-11-20 14:05，`npm run bdd -w backend -- --format json:reports/baseline.json`、`npm run bdd -w frontend`（Playwright JSON 報告）

## backend

### `backend/訂單/dsl.md › Then › 訂單 {訂單編號} 的明細為：`（MODIFY）

| 受影響項目 | 類型 | 位置 | 基準狀態 | 處理任務 |
|---|---|---|---|---|
| 阿明查看剛完成的訂單 | feature | `specs/truth/features/backend/訂單/訂單明細.feature:21` | 紅 | T010 |
| 退貨後查看訂單 | feature | `specs/truth/features/backend/訂單/退貨.feature:44` | 紅 | T010 |
| 訂單 {訂單編號} 的明細為： | step | `backend/tests/bdd/modules/訂單/斷言.ts:63` | — | T010 |
| assertOrderLines | helper | `backend/tests/bdd/shared/asserts.ts:118` | — | T010 |
| toOrderView | 產品 | `backend/src/services/order-service.ts:201` | — | T011 |

### `backend/贈品/取消贈品.feature`（DELETE）

| 受影響項目 | 類型 | 位置 | 基準狀態 | 處理任務 |
|---|---|---|---|---|
| {會員} 取消贈品 {贈品名稱} | step | `backend/tests/bdd/modules/贈品/操作.ts:41` | 未定義 | T015 |
| POST /gifts/:id/cancel | 產品 | `backend/src/routes/gift.ts:58` | — | T015 |
| cancelGrant | 產品 | `backend/src/services/gift-service.ts:132` | — | T015 |
| findGrant | 產品 | `backend/src/services/gift-service.ts:120` | — | 不需處理：滿額加贈仍使用 |

## frontend

### `backend/贈品/取消贈品.feature`（DELETE）

| 受影響項目 | 類型 | 位置 | 基準狀態 | 處理任務 |
|---|---|---|---|---|
| GiftCancelButton | 產品 | `frontend/src/components/GiftCancelButton.tsx:1` | — | T014 |
| cancelGift | 產品 | `frontend/src/api/client.ts:88` | — | T014 |

## tasks.md 未涵蓋的影響

| 受影響項目 | 類型 | 位置 | 對應的 truth-delta 列 | 說明 |
|---|---|---|---|---|
