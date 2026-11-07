# Tasks: 004-full-amount-gift

**Plan**: `specs/plans/004-full-amount-gift`
**Truth**: `specs/truth`

---

## Phase 1: Setup

依 truth-delta 的 techstack 段補齊後端套件：新增十進位計算套件、升級驗證套件，後續的 green 才能以十進位比對門檻金額、以新版驗證寫贈品規則。

### 後端套件

- [ ] T001 `環境` 安裝 decimal.js 並將 zod 由 4.5.0 升級至 4.6.7 於 `backend/package.json`、`backend/package-lock.json`
  - Must Read:
    - `specs/truth/techstack.md` -> `Runtime Dependencies`
    - `research.md` -> `R2. 贈品規則驗證`, `R3. 門檻金額計算`
  - Why: 驗證套件跨小版本升級時既有的錯誤訊息格式可能改變，不照 research 定案的版本升級，既有結帳情境的錯誤斷言會在之後的 Phase 莫名轉紅。

**Checkpoint**: 後端 `npm ls decimal.js zod` 列出 `specs/truth/techstack.md` 的版本；`specs/truth/features/backend` 的既有情境結果與升級前相同

---

## Phase 2: Foundational

建立本 plan 新增、多個 Phase 共用、本身不帶行為的骨架：贈品發放資料表與測試資料庫對它的清空；不寫任何加贈判斷，滿額加贈的 `/bdd red` 仍會因行為不存在而失敗。

**Phase Must Read**:
- `plan.md` -> `Source Code (repository root)`

- [ ] T002 [P] `基礎` 新增贈品發放資料表 gift_grants 與發放時間欄位 granted_at 於 `backend/db/migrations/0005_gift_grants.sql`
  - Must Read:
    - `plan.md` -> `系統介面的盤點 › gift_grants 資料表介面`
    - `specs/truth/data/schema.dbml` -> `Table gift_grants`
  - Why: 訂單明細的對齊與滿額加贈都讀寫同一張發放表，分散在兩個 green 各自建表會讓同一支遷移被反覆改寫；只建表不寫讀寫，加贈的 red 仍因行為不存在而失敗。
- [ ] T003 [P] `基礎` 讓測試資料庫在每個情境開始時清空 gift_grants 資料表於 `backend/tests/bdd/shared/database.ts`
  - Must Read:
    - `specs/truth/features/backend/平臺共用/dsl.md` -> `附錄：共通規則`
  - Why: 情境之間不清空發放表，後一個情境就會讀到前一個情境發出的贈品，讓明細與加贈的斷言取決於執行順序。

**Checkpoint**: 測試資料庫遷移後有 `gift_grants` 表，且每個情境開始時該表為空；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠

---

## Phase 3: Truth Impact Audit

**Phase Must Read**:
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `002/FR-006`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `003/FR-009`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `Runtime Dependencies / zod`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `openapi.yaml › components.schemas.Order`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `openapi.yaml › components.schemas.Error`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `openapi.yaml › operationId cancelGift`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `schema.dbml › Table order_gifts.cancelled_at`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `backend/訂單/訂單明細.feature › Rule: 訂單明細必須列出購買內容 › Example: 阿明查看剛完成的訂單`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `backend/贈品/取消贈品.feature`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `backend/平臺共用/dsl.md › Given › {會員} 的購物車有以下商品：`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `frontend/訂單/訂單明細頁.feature › Rule: 訂單明細頁必須列出購買內容 › Example: 阿明在訂單明細頁看到商品與贈品`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `frontend/贈品/取消贈品.feature`

- [ ] T004 `盤點` 盤點 backend 受 truth 異動影響的 feature、step、helper、fixture 與產品行為於 `specs/plans/004-full-amount-gift/impact-audit.md`
  - Why: 購物車前置句型被搬到平臺共用，使用它的既有 Example 不只 truth-delta 列出的那一個，不先跑基準並記下每個 Example 的狀態，之後對齊時分不出紅燈是本次異動造成還是原本就壞的。
- [ ] T005 `盤點` 盤點 frontend 受 truth 異動影響的 feature、step、helper、fixture 與產品行為於 `specs/plans/004-full-amount-gift/impact-audit.md`
  - Why: 取消贈品的入口可能同時出現在訂單明細頁與贈品區，只盤點被刪除的 feature 檔會漏掉其他畫面上仍呼叫取消操作的元件。

**Checkpoint**: `impact-audit.md` 涵蓋 truth-delta 的全部 MODIFY、DELETE 列，且沒有 tasks.md 未涵蓋的影響

---

## Phase 4: MODIFY 既有需求異動 #1 › backend

**Phase Must Read**:
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `backend/訂單/訂單明細.feature › Rule: 訂單明細必須列出購買內容 › Example: 阿明查看剛完成的訂單`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `backend/平臺共用/dsl.md › Given › {會員} 的購物車有以下商品：`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `openapi.yaml › components.schemas.Order`
- `specs/plans/004-full-amount-gift/impact-audit.md` -> `backend`

- [ ] T006 `/bdd realign` 對齊 `specs/truth/features/backend/訂單/訂單明細.feature:9`、`specs/truth/features/backend/訂單/訂單明細.feature:18`、`specs/truth/features/backend/訂單/結帳.feature:8` 的測試碼於 `backend/tests/bdd/modules/訂單/前置.ts`、`backend/tests/bdd/modules/平臺共用/前置.ts`、`backend/tests/bdd/modules/訂單/斷言.ts`
  - Optional:
    - `specs/truth/contracts/openapi.yaml` -> `schemas.Order`
  - Why: 購物車前置句型的語意不變只是換了模組，若在兩個模組各留一份註冊，同一句型會被重複比對而讓所有使用它的 Example 都報歧義。
- [ ] T007 `/bdd green` 實作 `specs/truth/features/backend/訂單/訂單明細.feature:9`、`specs/truth/features/backend/訂單/訂單明細.feature:18`、`specs/truth/features/backend/訂單/結帳.feature:8` 的行為於 `backend/src/services/order-service.ts`、`backend/src/routes/orders.ts`、`backend/src/db/repositories/gift-grants.ts`
  - Must Read:
    - `specs/truth/contracts/openapi.yaml` -> `schemas.Order`
    - `specs/truth/data/schema.dbml` -> `Table gift_grants.granted_at`
  - Why: 訂單回應的贈品是與商品並列的獨立陣列，把贈品塞進商品陣列並標成零元，既有只讀商品的呼叫端會把贈品算進件數。
- [ ] T008 `/bdd refactor` 整理 `specs/truth/features/backend/訂單/訂單明細.feature:9`、`specs/truth/features/backend/訂單/訂單明細.feature:18`、`specs/truth/features/backend/訂單/結帳.feature:8` 的程式碼於 `backend/src/services/order-service.ts`、`backend/src/routes/orders.ts`、`backend/src/db/repositories/gift-grants.ts`、`backend/tests/bdd/modules/訂單/前置.ts`、`backend/tests/bdd/modules/平臺共用/前置.ts`、`backend/tests/bdd/modules/訂單/斷言.ts`
  - Why: 明細查詢與結帳共用同一段訂單組裝，整理時把贈品查詢併進結帳交易，結帳回應就會多出尚未發放的贈品。

**Checkpoint**: `specs/truth/features/backend/訂單/訂單明細.feature:9`、`specs/truth/features/backend/訂單/訂單明細.feature:18`、`specs/truth/features/backend/訂單/結帳.feature:8` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠

---

## Phase 5: MODIFY 既有需求異動 #1 › frontend

**Phase Must Read**:
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `frontend/訂單/訂單明細頁.feature › Rule: 訂單明細頁必須列出購買內容 › Example: 阿明在訂單明細頁看到商品與贈品`
- `specs/plans/004-full-amount-gift/impact-audit.md` -> `frontend`

- [ ] T009 `/bdd realign` 對齊 `specs/truth/features/frontend/訂單/訂單明細頁.feature:14` 的測試碼於 `frontend/tests/bdd/modules/訂單/畫面定義.ts`、`frontend/tests/bdd/modules/訂單/斷言.ts`
  - Optional:
    - `ui/frontend.md` -> `畫面 › 訂單明細 › 贈品列`
  - Why: 贈品列與商品列在畫面上是不同區塊，沿用商品列的定位方式斷言贈品，會在只有商品時也誤判為看到了贈品。
- [ ] T010 `/bdd green` 實作 `specs/truth/features/frontend/訂單/訂單明細頁.feature:14` 的行為於 `frontend/src/api/types.ts`、`frontend/src/components/OrderDetail.tsx`
  - Must Read:
    - `specs/truth/contracts/openapi.yaml` -> `schemas.Order`
    - `ui/frontend.md` -> `畫面 › 訂單明細 › 贈品列`
  - Why: 贈品在畫面上不顯示金額也不計入小計，照商品列的版型顯示零元，會讓會員以為贈品被收費後又折抵。
- [ ] T011 `/bdd refactor` 整理 `specs/truth/features/frontend/訂單/訂單明細頁.feature:14` 的程式碼於 `frontend/src/api/types.ts`、`frontend/src/components/OrderDetail.tsx`、`frontend/tests/bdd/modules/訂單/畫面定義.ts`、`frontend/tests/bdd/modules/訂單/斷言.ts`
  - Why: 明細元件的商品列之後會被結帳頁共用，整理時把贈品列抽成商品列的變體，會讓結帳頁在加贈前就顯示空的贈品區。

**Checkpoint**: `specs/truth/features/frontend/訂單/訂單明細頁.feature:14` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠

---

## Phase 6: DELETE clarify 2026-11-06：移除取消贈品 › frontend

**Phase Must Read**:
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `frontend/贈品/取消贈品.feature`
- `specs/plans/004-full-amount-gift/impact-audit.md` -> `frontend`

- [ ] T012 `移除` 移除 會員自行取消贈品 的測試與產品行為於 `frontend/tests/bdd/modules/贈品/操作.ts`、`frontend/tests/bdd/modules/贈品/斷言.ts`、`frontend/src/components/CancelGiftButton.tsx`、`frontend/src/api/client.ts`
  - Why: 取消按鈕的 step 與其他贈品句型共用同一個模組檔，整檔刪除會連帶拿掉滿額加贈之後還要用的贈品區定位。

**Checkpoint**: `specs/truth/features/frontend/贈品/取消贈品.feature` 已無殘留的測試與產品行為；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠

---

## Phase 7: DELETE clarify 2026-11-06：移除取消贈品 › backend

**Phase Must Read**:
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `backend/贈品/取消贈品.feature`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `openapi.yaml › operationId cancelGift`
- `specs/plans/004-full-amount-gift/truth-delta.md` -> `schema.dbml › Table order_gifts.cancelled_at`
- `specs/plans/004-full-amount-gift/impact-audit.md` -> `backend`

- [ ] T013 `移除` 移除 會員自行取消贈品 的測試與產品行為於 `backend/tests/bdd/modules/贈品/操作.ts`、`backend/tests/bdd/modules/贈品/斷言.ts`、`backend/src/routes/gifts.ts`、`backend/src/services/gift-service.ts`
  - Why: 取消操作的路由移除後若服務層仍保留取消分支，之後的加贈邏輯會沿用它而把已取消當成有效狀態判斷。
- [ ] T014 `基礎` 移除 order_gifts 資料表的 cancelled_at 欄位於 `backend/db/migrations/0006_drop_order_gifts_cancelled_at.sql`
  - Why: 欄位要在所有讀寫它的程式都移除之後才刪，先刪欄位會讓尚未移除的取消路徑在執行時直接失敗而不是在測試中被發現。

**Checkpoint**: `specs/truth/features/backend/贈品/取消贈品.feature` 已無殘留的測試與產品行為；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠

---

## Phase 8: `specs/truth/features/backend/贈品/滿額加贈.feature` (US1)

**Phase Must Read**:
- `specs/truth/features/backend/贈品/滿額加贈.feature`
- `specs/truth/features/backend/平臺共用/dsl.md` -> `附錄：共通規則`
- `spec.md` -> `使用者故事 1`, `FR-001`, `FR-002`
- `plan.md` -> `系統介面的盤點 › 贈品 API 介面`, `系統介面的盤點 › gift_grants 資料表介面`

- [ ] T015 [US1] `/bdd red` 撰寫 `specs/truth/features/backend/贈品/滿額加贈.feature` 的 step 於 `backend/tests/bdd/modules/贈品/前置.ts`、`backend/tests/bdd/modules/贈品/操作.ts`、`backend/tests/bdd/modules/贈品/斷言.ts`
  - Optional:
    - `specs/truth/contracts/openapi.yaml` -> `/checkout`, `schemas.Error`
  - Why: 贈品庫存的前置要直接寫進資料庫並由共通規則的資料列比對確認，透過結帳流程間接扣庫存會讓庫存不足的情境無法單獨重現。
- [ ] T016 [US1] `/bdd green` 實作 `specs/truth/features/backend/贈品/滿額加贈.feature` 的行為於 `backend/src/domain/gift-threshold.ts`、`backend/src/services/gift-service.ts`、`backend/src/services/checkout-service.ts`、`backend/src/db/repositories/gift-grants.ts`
  - Must Read:
    - `specs/truth/contracts/openapi.yaml` -> `/checkout`, `schemas.Order`, `schemas.Error`
    - `specs/truth/data/schema.dbml` -> `Table gift_grants.granted_at`
    - `research.md` -> `R3. 門檻金額計算`, `R4. 贈品發放時間`
  - Why: 門檻比對以十進位且以折扣後金額計算，用浮點數或折扣前金額比對，剛好等於門檻的訂單會被判成未達標。
- [ ] T017 [US1] `/bdd refactor` 整理 `specs/truth/features/backend/贈品/滿額加贈.feature` 的程式碼於 `backend/src/domain/gift-threshold.ts`、`backend/src/services/gift-service.ts`、`backend/src/services/checkout-service.ts`、`backend/src/db/repositories/gift-grants.ts`、`backend/tests/bdd/modules/贈品/前置.ts`、`backend/tests/bdd/modules/贈品/操作.ts`、`backend/tests/bdd/modules/贈品/斷言.ts`
  - Why: 贈品扣庫存與訂單成立在同一個交易內，整理時把加贈搬到交易之外，庫存不足時會出現訂單成立卻少發贈品而未告知會員的情況。

**Checkpoint**: `specs/truth/features/backend/贈品/滿額加贈.feature` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠

---

## Phase 9: `specs/truth/features/frontend/贈品/滿額加贈提示.feature` (US1)

**Phase Must Read**:
- `specs/truth/features/frontend/贈品/滿額加贈提示.feature`
- `specs/truth/features/frontend/平臺共用/dsl.md` -> `附錄：共通規則`
- `spec.md` -> `使用者故事 1`, `FR-002`
- `plan.md` -> `系統介面的盤點 › 結帳頁介面`

- [ ] T018 [US1] `/bdd red` 撰寫 `specs/truth/features/frontend/贈品/滿額加贈提示.feature` 的 step 於 `frontend/tests/bdd/modules/贈品/畫面定義.ts`、`frontend/tests/bdd/modules/贈品/操作.ts`、`frontend/tests/bdd/modules/贈品/斷言.ts`
  - Optional:
    - `ui/frontend.md` -> `畫面 › 結帳 › 贈品提示`
  - Why: 庫存不足的提示文字是 spec 明文，必須逐字斷言，只斷言提示存在會讓加贈成功與庫存不足兩種提示無法區分。
- [ ] T019 [US1] `/bdd green` 實作 `specs/truth/features/frontend/贈品/滿額加贈提示.feature` 的行為於 `frontend/src/components/GiftNotice.tsx`、`frontend/src/pages/CheckoutPage.tsx`
  - Must Read:
    - `ui/frontend.md` -> `畫面 › 結帳 › 贈品提示`
    - `specs/truth/contracts/openapi.yaml` -> `schemas.Error`
  - Why: 庫存不足時結帳照常成功，把這個錯誤碼當成結帳失敗處理，會讓會員以為訂單沒有成立而重複下單。
- [ ] T020 [US1] `/bdd refactor` 整理 `specs/truth/features/frontend/贈品/滿額加贈提示.feature` 的程式碼於 `frontend/src/components/GiftNotice.tsx`、`frontend/src/pages/CheckoutPage.tsx`、`frontend/tests/bdd/modules/贈品/畫面定義.ts`、`frontend/tests/bdd/modules/贈品/操作.ts`、`frontend/tests/bdd/modules/贈品/斷言.ts`
  - Why: 提示元件與結帳完成訊息共用同一個通知區，整理時合併成一則訊息，庫存不足的告知會被成功訊息蓋掉。

**Checkpoint**: `specs/truth/features/frontend/贈品/滿額加贈提示.feature` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠；可完成 `spec.md` 使用者故事 1 的 Independent Test；MVP 可展示

---

## Phase 10: NFR 重構

逐條檢視本 plan `spec.md` 的 NFR 與被 MODIFY 的 NFR：已有 feature 檔驗證的不另列任務；沒有 feature 覆蓋的，判定既有程式是否已達標，未達標或須量測才能確認者列 `重構` 任務。

| NFR | 驗證來源 | 判定 |
| --- | --- | --- |
| NFR-001 | 無 feature 覆蓋（`research.md` R5 的結帳延遲量測未落到 feature） | 列 T021 |
| NFR-002 | `specs/truth/features/frontend/贈品/滿額加贈提示.feature` 的「庫存不足仍照常結帳」Rule | 已由 feature 驗證 |

- [ ] T021 `重構` 在 `@nfr` 量測加入含加贈判斷的結帳負載，量測 NFR-001，未達門檻時重構門檻判斷與贈品庫存扣減路徑於 `backend/tests/bdd/modules/非功能品質/measure.ts`、`backend/src/services/checkout-service.ts`、`backend/src/services/gift-service.ts`
  - Must Read:
    - `spec.md` -> `NFR-001`
    - `research.md` -> `R5. 結帳延遲量測`
  - Optional:
    - `plan.md` -> `系統介面的盤點 › 後端共通介面`
  - Why: 加贈判斷多了一次贈品庫存的鎖定，只有多筆訂單同時結帳時延遲才會被拉長，功能 feature 都是單筆結帳而量不到；以量測 profile 實測 p95 才能確認是否達標，改動後全套 feature 仍須全綠。

**Checkpoint**: `npm run bdd:nfr` 的結帳負載量測中，含加贈判斷的結帳 p95 不超過 300 毫秒；`specs/truth/features/backend` 與 `specs/truth/features/frontend` 的全套 feature 仍全綠

---

## Phase 11: Acceptance Gates

**Phase Must Read**:
- `specs/truth/techstack.md` -> `Dev Dependencies`

- [ ] T022 `驗證` 以隨機順序執行 `specs/truth/features/backend` 的全套 feature 並確認全綠
  - Why: 各 Phase 的 Checkpoint 容許尚未處理的異動暫時失敗，只有最後整套打亂順序重跑，才能證明既有功能的情境沒有被本次的對齊與移除連帶破壞。
- [ ] T023 `驗證` 以隨機順序執行 `specs/truth/features/frontend` 的全套 feature 並確認全綠
  - Why: 前端情境共用同一個後端與資料庫，後端移除取消操作與 NFR 重構的調整可能破壞既有畫面行為，最後必須整套重跑一次。
- [ ] T024 `驗證` 以 /dsl-refine 的 check_trace.py 確認本 plan 前綴的 acceptance 檢查點都有端點 Example 覆蓋
  - Must Read:
    - `features/acceptance/滿額贈品.feature`
  - Why: acceptance 本身不會被執行，只有追溯檢查能證明本 plan 的每個業務檢查點都落到了已綠的端點 Example 上；其他 plan 的檢查點不在本次範圍。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**：無依賴，可立即開始
- **Foundational (Phase 2)**：依賴 Setup；完成前不得開始 Truth Impact Audit 與任何 MODIFY、DELETE、ADD Phase
- **Truth Impact Audit (Phase 3)**：依賴 Foundational；完成前不得開始任何 MODIFY、DELETE Phase
- **MODIFY Phase (Phase 4–5)**：皆依賴 Truth Impact Audit；提供方端點先於使用方端點，彼此的依賴見 Feature Dependencies
- **DELETE Phase (Phase 6–7)**：皆依賴 Truth Impact Audit；使用方端點先於提供方端點，被本 plan 的 ADD 取代者依賴取代它的 ADD Phase，見 Feature Dependencies
- **ADD Phase (Phase 8–9)**：皆依賴 Foundational；與其他 Phase 的依賴見 Feature Dependencies
- **NFR 重構 (Phase 10)**：依賴全部 MODIFY、DELETE、ADD Phase
- **Acceptance Gates (Phase 11)**：依賴 NFR 重構

### Feature Dependencies

| Phase | feature | 依賴 Phase | 依據 |
| --- | --- | --- | --- |
| 4 | `specs/truth/features/backend/訂單/訂單明細.feature`、`specs/truth/features/backend/訂單/結帳.feature` | 3 | 對齊的處理清單與基準狀態取自 Phase 3 產出的 impact-audit.md 後端段 |
| 5 | `specs/truth/features/frontend/訂單/訂單明細頁.feature` | 3、4 | 明細頁的贈品列讀取 Phase 4 在訂單回應新增的贈品陣列 |
| 6 | `specs/truth/features/frontend/贈品/取消贈品.feature` | 3 | 移除清單取自 impact-audit.md 前端段；使用方先移除，不需等後端 |
| 7 | `specs/truth/features/backend/贈品/取消贈品.feature` | 3、6 | Phase 6 先移除畫面上的取消入口，後端移除取消操作後才不會有畫面呼叫不存在的操作 |
| 8 | `specs/truth/features/backend/贈品/滿額加贈.feature` | 7 | 加贈寫入的贈品服務與 Phase 7 移除取消分支的是同一支服務，先移除才不會沿用取消狀態 |
| 9 | `specs/truth/features/frontend/贈品/滿額加贈提示.feature` | 6、8 | 庫存不足提示讀取 Phase 8 的錯誤碼；贈品 step 模組在 Phase 6 已移除取消句型 |

### Within Each Feature Phase

- MODIFY Phase：`/bdd realign` → `/bdd green` → `/bdd refactor` 依序執行：green 開始前 realign 須完成，refactor 開始前 green 須全綠；接在後面的 `基礎` 排在 refactor 之後
- DELETE Phase：`移除` 依序執行；接在後面的 `基礎` 排在全部 `移除` 之後
- ADD Phase：`/bdd red` → `/bdd green` → `/bdd refactor` 依序執行：green 開始前 red 須完成，refactor 開始前 green 須全綠
- 同一個 Phase 的任務不平行

### Parallel Opportunities

- Foundational 標 [P] 的 T002、T003 可平行
- Truth Impact Audit 的 T004、T005 寫同一份 `impact-audit.md`，須依序執行
- 後端與前端的 Phase 檔案不重疊：前端 Phase 在其依賴的 Phase 完成後，可與後端其餘 Phase 平行，形成後端線與前端線
- 同一端點的 Phase 共用 step 模組檔與產品檔（例如 `backend/tests/bdd/modules/贈品/操作.ts`、`backend/src/services/gift-service.ts`），須依序執行
- Acceptance Gates 的 T022、T023 分屬兩個端點，可平行

---

## Parallel Example: 後端線與前端線

```text
# Phase 3 完成後，後端線與前端線同時進行：
後端線：T006 → T007 → T008（Phase 4，specs/truth/features/backend/訂單/訂單明細.feature、specs/truth/features/backend/訂單/結帳.feature）
前端線：T012（Phase 6，specs/truth/features/frontend/贈品/取消贈品.feature，只依賴 Phase 3）

# Phase 4 與 Phase 6 都完成後，後端線移除取消操作，前端線對齊訂單明細頁：
後端線：T013 → T014（Phase 7，specs/truth/features/backend/贈品/取消贈品.feature）
前端線：T009 → T010 → T011（Phase 5，specs/truth/features/frontend/訂單/訂單明細頁.feature，依賴 Phase 3、4）
```
