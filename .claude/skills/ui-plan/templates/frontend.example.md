# 前端畫面規格：結帳與優惠券

## 範疇

- 端點類型：`前端端點`
- 本次涵蓋的前端介面：
    - `前端共通介面`
    - `購物車頁面介面`
    - `結帳頁面介面`
    - `訂單完成頁面介面`
- 不在範疇：商品頁的「加入購物車」（`addCartItem`）由商品頁功能負責，本次不變更
- 上游契約：
    - HTTP API：`specs/truth/contracts/openapi.yaml`
    - 即時事件：`specs/truth/contracts/asyncapi.yaml`
- 不影響畫面的契約異動：`addCartItem`（回應多帶 `coupon`，只由商品頁呼叫，商品頁不顯示折扣，呈現不變）
- 雛形入口：`prototype/index.html`

## 視覺風格

- 風格：沿用現行 `frontend/src/styles/tokens.css` 的方塊像素風格，畫面像遊戲裡的物品欄與工作台（spec 沒有要求改變風格，未詢問使用者）
- 色彩：

| Token | 色碼 | 用途 |
|---|---|---|
| `--grass` | `#5DA130` | 主要按鈕、成功狀態 |
| `--dirt` | `#8B5A2B` | 頁首與頁尾底色 |
| `--stone` | `#7F7F7F` | 卡片外框、停用狀態 |
| `--slot` | `#C6C6C6` | 物品格底色 |
| `--ink` | `#1E1E1E` | 文字、2px 粗外框 |
| `--redstone` | `#C0392B` | 錯誤、售完 |
| `--gold` | `#F2C230` | 折扣、價格變動提示 |

- 字型：標題用像素字體 `"Press Start 2P"`，中文與內文用 `"Noto Sans TC"`，數字用等寬字；字型檔自代管於 `public/fonts/`（雛形以 Google Fonts 預覽）
- 元件：
    - 所有框線 2px 實線、無圓角
    - 按鈕有立體陰影（右下深、左上淺），按下時陰影反轉
    - 商品圖以 16×16 像素圖示放大呈現

## 本次異動的既有畫面

| 畫面 | 對應介面 | 程式位置 | 現況 | 本次 | 依據 |
|---|---|---|---|---|---|
| 購物車頁 | `購物車頁面介面` | `frontend/src/pages/CartPage.tsx` | 右欄只有商品小計與「繼續購物」 | 右欄改為訂單摘要（商品小計、折扣、運費、應付總額）與「前往結帳」 | FR-008 |
| 購物車頁 | `購物車頁面介面` | `frontend/src/pages/CartPage.tsx`、`frontend/src/components/CouponField.tsx`（新增） | 沒有優惠碼 | 商品列表下方加入優惠碼輸入、套用與移除 | FR-006、FR-007 |
| 購物車頁 | `購物車頁面介面` | `frontend/src/components/CartItemRow.tsx` | 數量加減只更新該列小計 | 數量加減後依回應的 `coupon.status` 更新折扣列，未達門檻時顯示「未達門檻」 | FR-007 |
| 購物車頁 | `購物車頁面介面` | `frontend/src/pages/CartPage.tsx` | 進入頁面時呼叫一次 `getCart`，之後不更新 | 進入頁面時連線購物車通知，商品售完或改價時即時標記 | FR-012、FR-013 |

## 前端共通介面

- 匿名 session：首次造訪由後端發 cookie `sid`，前端不自行保存識別碼
- 錯誤呈現：一律顯示 `Error.message`，不顯示錯誤碼；`SESSION_MISSING` 時重新整理頁面以取得新 session
- 即時事件連線：進入購物車頁或結帳頁時連線 `cartNotifications`，離開頁面時關閉；斷線後以 1、2、4、8 秒退避重連，重連成功後呼叫 `getCart` 取回最新狀態
- 四態：每個頁面都要有載入、空、錯誤、正常四種狀態
- 響應式：寬 768px 以下改為單欄，訂單摘要移到列表下方並固定在底部
- 無障礙：按鈕一律用 `<button>`，輸入欄有 `<label>`，數量變動與即時提示以 `aria-live="polite"` 朗讀

## 畫面

### 購物車頁

- 對應介面：`購物車頁面介面`
- 雛形：`prototype/index.html`（依現行 `CartPage.tsx` 的版面與 `tokens.css` 重做，再加上本次的修改）
- 對應需求：FR-006、FR-007、FR-008、FR-012、FR-013；既有行為依 `001/FR-002`、`001/FR-004`、`001/FR-005`
- 四態：載入（`?state=loading`）、空（`?state=empty`，顯示空購物車與繼續購物）、錯誤（`?state=error`，顯示連線中斷與重試）、正常
- 版面：
    - 頁首：店名、購物車件數
    - 左欄：商品列表（每列有圖示、名稱、單價、數量加減、小計、移除）
    - 左欄下方：優惠碼輸入與套用
    - 右欄：訂單摘要（商品小計、折扣、運費、應付總額、前往結帳）
- 互動與呼叫：

| 操作 | 呼叫 | 成功時 | 失敗時 |
|---|---|---|---|
| 進入頁面 | `getCart` | 顯示列表與摘要；沒有商品時顯示空狀態 | 顯示錯誤狀態與重試按鈕 |
| 數量加減 | `updateCartItemQuantity` | 以回應的 `Cart` 更新整頁；`coupon.status` 為 `below_threshold` 時折扣列改顯示「未達門檻」 | `OUT_OF_STOCK`：數量退回原值並在該列顯示 `message` |
| 移除商品 | `removeCartItem` | 該列淡出後以回應更新 | 顯示錯誤提示，該列保留 |
| 套用優惠碼 | `applyCoupon` | 折扣列顯示金額與「移除」 | 在輸入欄下方顯示 `message`，輸入內容保留 |
| 移除優惠碼 | `removeCoupon` | 折扣列歸零 | 顯示錯誤提示 |
| 前往結帳 | — | 前往 `checkout.html` | 購物車有售完商品時按鈕停用 |

- 即時事件：

| 事件 | 畫面反應 |
|---|---|
| `cartItemSoldOut` | 該列加上「已售完」標記與紅框，頁面上方出現物品欄訊息「○○ 已售完」，前往結帳停用直到使用者移除該商品 |
| `cartItemPriceChanged` | 該列單價改為新價並以金色閃爍一次，頁面上方提示「○○ 價格已從 NT$a 調整為 NT$b」，摘要重新呼叫 `getCart` |

- 數量限制：減號在數量為 1 時停用；加號在數量為 99 時停用；不提供直接輸入數字

### 結帳頁

- 對應介面：`結帳頁面介面`
- 雛形：`prototype/checkout.html`
- 對應需求：FR-008、FR-009、FR-010、FR-012
- 四態：載入與錯誤沿用購物車頁的版型；空：購物車為空時導回購物車頁；正常
- 版面：
    - 左欄：收件人表單（姓名、手機、地址）
    - 右欄：商品明細（唯讀）與金額摘要、送出訂單
- 欄位驗證（送出前在前端先檢查，以 API 結果為準）：

| 欄位 | 規則 | 錯誤文案 |
|---|---|---|
| 姓名 | 必填，最多 50 字 | 請輸入收件人姓名 |
| 手機 | `09` 開頭的 10 碼數字 | 請輸入 09 開頭的 10 碼手機號碼 |
| 地址 | 必填，最多 200 字 | 請輸入收件地址 |

- 互動與呼叫：

| 操作 | 呼叫 | 成功時 | 失敗時 |
|---|---|---|---|
| 進入頁面 | `getCart`；產生一次 `Idempotency-Key` 並保存在頁面記憶體 | 顯示明細與摘要；購物車為空時導回購物車頁 | 顯示錯誤狀態 |
| 送出訂單 | `createOrder`，`expectedTotal` 帶畫面上的應付總額 | 前往 `complete.html?orderId=<orderId>` | 依下表處理 |

| 錯誤碼 | 畫面反應 |
|---|---|
| `PRICE_CHANGED` | 重新呼叫 `getCart`，以對話框顯示新總額，使用者確認後再送出，沿用同一個 `Idempotency-Key` |
| `OUT_OF_STOCK`、`PRODUCT_UNAVAILABLE` | 顯示 `message`，提供「回購物車調整」按鈕 |
| `CART_EMPTY` | 導回購物車頁 |
| `VALIDATION_FAILED` | 在表單上方顯示 `message` |
| 網路逾時 | 按鈕恢復可按，提示「訂單可能已送出，請再按一次確認」，重送沿用同一個 `Idempotency-Key` |

- 送出中：按鈕停用並顯示「送出中」，避免連點
- 即時事件：`cartItemSoldOut` 時在明細該列標記已售完，送出按鈕停用並提示回購物車調整

### 訂單完成頁

- 對應介面：`訂單完成頁面介面`
- 雛形：`prototype/complete.html`
- 對應需求：FR-011
- 四態：載入沿用購物車頁的版型；空與錯誤：找不到訂單（`?state=not-found`）；正常
- 版面：訂單編號、成立時間、商品明細快照、折扣、運費、總額、繼續購物
- 互動與呼叫：

| 操作 | 呼叫 | 成功時 | 失敗時 |
|---|---|---|---|
| 進入頁面 | `getOrder`，`orderId` 取自網址 | 顯示訂單內容 | `NOT_FOUND`：顯示「找不到這筆訂單」與回購物車按鈕 |

## 雛形

- 檔案：
    - `prototype/index.html`：購物車頁
    - `prototype/checkout.html`：結帳頁
    - `prototype/complete.html`：訂單完成頁
- 只呈現畫面與直接互動，不串接後端、不模擬 API
- 假資料：三項商品（亞麻襯衫 NT$1,280、帆布托特包 NT$890、羊毛襪 NT$320），跨頁以 `sessionStorage` 傳遞購物車內容
- 互動：
    - 優惠碼 `SAVE100`：商品小計滿 NT$1,000 折 NT$100；`OLD2025` 顯示過期文案；其他券碼顯示無效文案
    - 運費：小計扣除折扣後未滿 NT$1,500 收 NT$60
    - 進入購物車頁 8 秒後出現一次改價提示（羊毛襪 NT$320 → NT$290）
- 網址參數：

| 頁面 | 參數 | 呈現狀態 |
|---|---|---|
| `index.html` | `?state=loading` | 載入中 |
| `index.html` | `?state=empty` | 空購物車 |
| `index.html` | `?state=error` | `getCart` 失敗 |
| `index.html` | `?state=soldout` | 進入後 2 秒推播 `cartItemSoldOut`（帆布托特包） |
| `checkout.html` | `?state=price-changed` | 送出後回 `PRICE_CHANGED`，新總額多 NT$50 |
| `checkout.html` | `?state=out-of-stock` | 送出後回 `OUT_OF_STOCK` |
| `checkout.html` | `?state=timeout` | 送出後 5 秒逾時 |
| `complete.html` | `?state=not-found` | 找不到訂單 |

## 驗證

- 雙擊 `prototype/index.html` 可直接開啟，不需要伺服器
- 依「互動與呼叫」逐列操作，畫面反應與表格一致
- 依「網址參數」逐一開啟，每個狀態都能看到
- 視窗寬 375px 時無水平捲動，摘要固定在底部
- 只用鍵盤可以完成「調整數量 → 套用優惠碼 → 結帳 → 送出」
