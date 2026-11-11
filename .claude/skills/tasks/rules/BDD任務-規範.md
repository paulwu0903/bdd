# Rule 1 - ADD Phase 恰好 red、green、refactor [MUST]
- 每個 ADD Phase 依序恰好有一個 `/bdd red`、一個 `/bdd green`、一個 `/bdd refactor`，三者範疇相同：整檔新增時為該 feature 檔，在既有檔中新增 Example 時為這些 Example 的 `檔:行`。
- 不再依 Rule 拆分，也不把多個 feature 檔合成一組。

## Good Example
- 新檔的 ADD Phase 依序三個任務，範疇都是整檔。

```
- [ ] T020 [US1] `/bdd red` 撰寫 `specs/truth/features/backend/贈品/滿額加贈.feature` 的 step 於 `backend/tests/bdd/modules/贈品/前置.ts`、`backend/tests/bdd/modules/贈品/斷言.ts`
- [ ] T021 [US1] `/bdd green` 實作 `specs/truth/features/backend/贈品/滿額加贈.feature` 的行為於 `backend/src/services/gift-service.ts`
- [ ] T022 [US1] `/bdd refactor` 整理 `specs/truth/features/backend/贈品/滿額加贈.feature` 的程式碼於 `backend/src/services/gift-service.ts`、`backend/tests/bdd/modules/贈品/前置.ts`、`backend/tests/bdd/modules/贈品/斷言.ts`
```

## Bad Example
- 同一個 feature 依 Rule 拆成兩個 red，refactor 又合併了另一個 feature。

```
- [ ] T020 [US1] `/bdd red` 撰寫 `…/滿額加贈.feature` 的 step 於 …（只寫前兩個 Rule）
- [ ] T021 [US1] `/bdd red` 撰寫 `…/滿額加贈.feature` 的 step 於 …（後兩個 Rule）
- [ ] T023 [US1] `/bdd refactor` 整理 `…/滿額加贈.feature`、`…/贈品庫存.feature` 的程式碼於 …
```

# Rule 2 - MODIFY Phase 恰好 realign、green、refactor [MUST]
- 每個 MODIFY Phase 依序恰好有一個 `/bdd realign`、一個 `/bdd green`、一個 `/bdd refactor`，範疇相同，以 `檔:行` 列出本組受影響的全部 Example（truth-delta 列出的，以及 `list_changes.py` 找到的、使用被修改句型的 Example）。
- realign 先把既有測試碼改寫成符合最新的 truth，green 才改產品碼；需要 ALTER migration 時，以 `基礎` 任務接在 refactor 之後。

## Good Example
- realign 的路徑是被改句型的 step 檔與它引用的 fixture；ALTER 接在最後。

```
- [ ] T010 `/bdd realign` 對齊 `specs/truth/features/backend/聊天訊息/發言頻率.feature:13`、`specs/truth/features/backend/聊天訊息/送出訊息與對局.feature:88` 的測試碼於 `backend/tests/bdd/modules/聊天訊息/前置.ts`、`backend/tests/bdd/shared/fixtures/chat.ts`
- [ ] T011 `/bdd green` 實作 `…/發言頻率.feature:13`、`…/送出訊息與對局.feature:88` 的行為於 `backend/src/config.ts`、`backend/src/lib/sliding-window.ts`
- [ ] T012 `/bdd refactor` 整理 `…/發言頻率.feature:13`、`…/送出訊息與對局.feature:88` 的程式碼於 `backend/src/config.ts`、`backend/src/lib/sliding-window.ts`、`backend/tests/bdd/modules/聊天訊息/前置.ts`、`backend/tests/bdd/shared/fixtures/chat.ts`
```

## Bad Example
- 用 red 處理 MODIFY：句型字面沒變，red 找不到未定義的步驟，舊語意的 step 與 fixture 原封不動；範疇也漏掉了使用同一句型的其他 Example。

```
- [ ] T010 `/bdd red` 撰寫 `…/發言頻率.feature` 的 step 於 `backend/tests/bdd/modules/聊天訊息/前置.ts`
- [ ] T011 `/bdd green` 實作 `…/發言頻率.feature` 的行為於 `backend/src/config.ts`
```

# Rule 3 - DELETE Phase 以移除任務處理 [MUST]
- 每個 DELETE Phase 有一個以上的 `移除` 任務，路徑取自 `list_changes.py` 的靜態影響清單：註冊被刪除句型的 step 檔、只被它們使用的 helper 與 fixture，以及引用被刪除 operation 的產品檔。
- 使用方端點的 DELETE Phase 只列本端點的檔案；提供方端點的 DELETE Phase 在移除之後，以 `基礎` 任務接 DROP migration。

## Good Example
- 前端先移除呼叫與按鈕，後端再移除路由與欄位。

```
## Phase 6: DELETE clarify 2026-11-06：移除取消贈品 › frontend
- [ ] T014 `移除` 移除會員自行取消贈品的測試與產品行為於 `frontend/tests/bdd/modules/贈品/操作.ts`、`frontend/src/components/GiftCancelButton.tsx`、`frontend/src/api/client.ts`
## Phase 7: DELETE clarify 2026-11-06：移除取消贈品 › backend
- [ ] T015 `移除` 移除會員自行取消贈品的測試與產品行為於 `backend/tests/bdd/modules/贈品/操作.ts`、`backend/src/routes/gift.ts`、`backend/src/services/gift-service.ts`
- [ ] T016 `基礎` 刪除贈品的取消時間欄位於 `backend/db/migrations/0005_drop_gift_cancel.sql`
```

## Bad Example
- 用 red 驅動刪除，但被刪除的行為已不在 truth，沒有任何測試會因產品殘留而失敗；DROP 排在移除之前，產品碼還在讀這個欄位。

```
- [ ] T014 `基礎` 刪除贈品的取消時間欄位於 `backend/db/migrations/0005_drop_gift_cancel.sql`
- [ ] T015 `/bdd red` 撰寫取消贈品已移除的 step 於 `backend/tests/bdd/modules/贈品/斷言.ts`
```

# Rule 4 - Truth Impact Audit 每個受影響端點一個盤點任務 [MUST]
- Audit Phase 只放 `盤點` 任務：每個有 MODIFY 或 DELETE 的端點一個，產出寫入 plan 目錄的 `impact-audit.md`。
- 盤點任務的 Must Read 是 truth-delta 的 MODIFY、DELETE 列；Optional 是 `list_changes.py` 的靜態影響清單中屬於該端點的部分。

## Good Example
- 兩個端點都受影響，各一個盤點任務。

```
## Phase 3: Truth Impact Audit
- [ ] T005 `盤點` 盤點 backend 受 truth 異動影響的 feature、step、helper、fixture 與產品行為於 `specs/plans/004-full-amount-gift/impact-audit.md`
- [ ] T006 `盤點` 盤點 frontend 受 truth 異動影響的 feature、step、helper、fixture 與產品行為於 `specs/plans/004-full-amount-gift/impact-audit.md`
```

## Bad Example
- 有 MODIFY 卻沒有盤點，或在 Audit Phase 裡直接改程式。

```
## Phase 3: Truth Impact Audit
- [ ] T005 `/bdd realign` 對齊 `…/發言頻率.feature:13` 的測試碼於 …
```

# Rule 5 - refactor 的路徑是同 Phase 的 green 與 red 或 realign 路徑聯集 [MUST]
- refactor 的路徑依序列出同一 Phase green 的路徑，再接 red 或 realign 中尚未出現的路徑，不多不少。
- 不把其他 Phase 的檔案或整個端點目錄納入範疇。

## Good Example
- green 的產品檔加上 realign 的 step 與 fixture。

```
- [ ] T012 `/bdd refactor` 整理 `…/發言頻率.feature:13` 的程式碼於 `backend/src/config.ts`、`backend/tests/bdd/modules/聊天訊息/前置.ts`、`backend/tests/bdd/shared/fixtures/chat.ts`
```

## Bad Example
- 範疇用了整個端點目錄，step 與 fixture 都沒有被整理。

```
- [ ] T012 `/bdd refactor` 整理 `specs/truth/features/backend` 的程式碼於 `backend/src/config.ts`
```

# Rule 6 - Acceptance Gates 只放驗證任務 [MUST]
- Acceptance Gates 不放 `/bdd` 任務，只放 `驗證` 任務：每個端點一個「以隨機順序執行 `specs/truth/features/<端點>` 的全套 feature 並確認全綠」，最後一個「以 /dsl-refine 的 `check_trace.py --plan <plan 目錄>` 確認本 plan 前綴的 acceptance 檢查點都有端點 Example 覆蓋」。
- Acceptance Gates 的任務不標 [US]，也不放 refactor。

## Good Example
- 兩個端點各跑整個 truth 套件，最後追溯本 plan 前綴。

```
- [ ] T040 `驗證` 以隨機順序執行 `specs/truth/features/backend` 的全套 feature 並確認全綠
- [ ] T041 `驗證` 以隨機順序執行 `specs/truth/features/frontend` 的全套 feature 並確認全綠
- [ ] T042 `驗證` 以 /dsl-refine 的 `check_trace.py --plan <plan 目錄>` 確認本 plan 前綴的 acceptance 檢查點都有端點 Example 覆蓋
```

## Bad Example
- 只跑本次異動的 feature，其他模組因句型修改而變紅不會被發現。

```
- [ ] T040 `驗證` 以隨機順序執行 `specs/truth/features/backend/贈品` 的 feature 並確認全綠
```

# Rule 7 - red 與 realign 的檔案取 step 目錄的模組檔與靜態影響清單 [MUST]
- red 的路徑取自 plan.md Source Code 樹中該端 step 目錄下、標註了這個 feature 所涉系統介面的模組檔（例如 `modules/<模組>/前置.ts`、`操作.ts`、`斷言.ts`）；只列這個 feature 用到的句型會落在的檔案。
- realign 的路徑取自 `list_changes.py` 的靜態影響清單：註冊被修改句型的 step 檔，以及它們引用的 helper、fixture。
- 產品程式碼的檔案不列在 red 或 realign。

## Good Example
- realign 只列 step 檔與它引用的 fixture，不列產品碼。

```
- [ ] T010 `/bdd realign` 對齊 `…/發言頻率.feature:13` 的測試碼於 `backend/tests/bdd/modules/聊天訊息/前置.ts`、`backend/tests/bdd/shared/fixtures/chat.ts`
```

## Bad Example
- realign 只看 plan.md 樹，漏了寫死舊門檻的 fixture，還列了產品碼。

```
- [ ] T010 `/bdd realign` 對齊 `…/發言頻率.feature:13` 的測試碼於 `backend/tests/bdd/modules/聊天訊息/前置.ts`、`backend/src/config.ts`
```

# Rule 8 - green 的檔案取涉及系統介面在 plan.md 樹標註的實作檔 [MUST]
- green 的路徑取自這個範疇涉及的系統介面在 plan.md Source Code 樹中標註的實作檔，只列這個範疇的行為需要改動的檔案；MODIFY 另可取 `list_changes.py` 列出的既有產品檔。
- 只列本端點的檔案；step 檔與測試支援檔不列在 green。

## Good Example
- 後端的 green 只列後端的產品檔。

```
- [ ] T021 [US1] `/bdd green` 實作 `specs/truth/features/backend/贈品/滿額加贈.feature` 的行為於 `backend/src/routes/gift.ts`、`backend/src/services/gift-service.ts`
```

## Bad Example
- 後端的 green 列了前端檔案，還把 step 檔列進來。

```
- [ ] T021 [US1] `/bdd green` 實作 `…/滿額加贈.feature` 的行為於 `backend/src/services/gift-service.ts`、`frontend/src/components/GiftBadge.tsx`、`backend/tests/bdd/modules/贈品/斷言.ts`
```

# Rule 9 - Setup 依 truth-delta 的 techstack 段產生套件任務 [MUST]
- techstack 段的 ADD 與 MODIFY（新增或升級套件、執行環境）在 Setup 各列一個 `環境` 任務。
- techstack 段的 DELETE（移除套件）在所有 MODIFY、DELETE Phase 之後、第一個 ADD Phase 之前，以 `環境` 任務放在最後一個 DELETE Phase 的末尾；沒有 DELETE Phase 時放在最後一個 MODIFY Phase 的末尾，兩者皆無則放 Setup。
- 設定已用 glob 涵蓋 `specs/truth/features/<端點>/**`，不再列「把 feature 路徑加進設定」的任務；repo 已具備且 techstack 段沒有異動的工具不列任務。

## Good Example
- 新增套件在 Setup；移除舊套件要等所有測試與程式都不再使用它。

```
## Phase 1: Setup
- [ ] T001 [P] `環境` 安裝 decimal.js 4.x 於 `backend/package.json`
## Phase 7: DELETE clarify 2026-11-06：移除取消贈品 › backend
- [ ] T017 `環境` 移除不再使用的 date-fns 於 `backend/package.json`
```

## Bad Example
- 一開始就移除套件，既有測試與產品碼在對齊前就壞掉；還列了已不需要的設定任務。

```
## Phase 1: Setup
- [ ] T001 `環境` 移除 date-fns 於 `backend/package.json`
- [ ] T002 `環境` 在後端 feature 執行設定加入本功能的 feature 路徑於 `backend/cucumber.mjs`
```

# Rule 10 - Foundational 只放 ADD 的不帶行為骨架 [MUST]
- Foundational 只放不走 /bdd 的 `基礎` 任務，內容是 truth-delta data 段 ADD 的資料表或欄位遷移，以及至少兩個 ADD Phase 會用到、本身不帶行為的測試支援骨架。
- data 段的 MODIFY、DELETE（ALTER、DROP）不放 Foundational，依 Rule 2、Rule 3 接在對應 Phase 之後。
- 判準：放進去之後，沒有任何 `/bdd red` 會因此直接通過；帶邏輯的 service、route 仍由第一個需要它的 green 帶出。沒有符合的項目時省略 Foundational Phase。

## Good Example
- 新表在 Foundational；只建表、不寫讀寫。

```
- [ ] T003 [P] `基礎` 新增贈品發放紀錄資料表於 `backend/db/migrations/0004_gift_grants.sql`
```

## Bad Example
- 把 DROP 放進 Foundational，既有產品碼在移除任務之前就讀不到欄位。

```
- [ ] T003 `基礎` 刪除贈品的取消時間欄位於 `backend/db/migrations/0005_drop_gift_cancel.sql`
```
