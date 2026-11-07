# Rule 1 - Phase 固定序 [MUST]
- Phase 依序為 Setup、Foundational、Truth Impact Audit、所有 MODIFY Phase、所有 DELETE Phase、所有 ADD Phase、NFR 重構、Acceptance Gates。
- Truth Impact Audit 只在 truth-delta 任一段有 MODIFY 或 DELETE 時設立，此時一定要設；純 ADD 的 plan 不設。
- Foundational 沒有任何基礎任務時省略；NFR 重構即使不需要任務也保留判定表；Acceptance Gates 固定在最後。
- 先讓既有測試與產品對齊新的 truth（MODIFY、DELETE），再在對齊後的基礎上開發新功能（ADD）。

## Good Example
- 有 MODIFY 與 DELETE，Audit 在所有異動 Phase 之前，ADD 排在 MODIFY、DELETE 之後。

```
## Phase 1: Setup
## Phase 2: Foundational
## Phase 3: Truth Impact Audit
## Phase 4: MODIFY 既有需求異動 #1 › backend
## Phase 5: MODIFY 既有需求異動 #1 › frontend
## Phase 6: DELETE clarify 2026-11-06：移除取消贈品 › frontend
## Phase 7: DELETE clarify 2026-11-06：移除取消贈品 › backend
## Phase 8: `specs/truth/features/backend/贈品/滿額加贈.feature` (US1)
## Phase 9: NFR 重構
## Phase 10: Acceptance Gates
```

## Bad Example
- 有 MODIFY 卻沒有 Audit；ADD 排在 MODIFY 之前，新功能建立在還沒對齊的舊行為上。

```
## Phase 1: Setup
## Phase 2: `specs/truth/features/backend/贈品/滿額加贈.feature` (US1)
## Phase 3: MODIFY 既有需求異動 #1 › backend
## Phase 4: Acceptance Gates
```

# Rule 2 - Phase 的單位依異動類型決定 [MUST]
- ADD：每個有 ADD 的 feature 檔一個 Phase，標題為 `` `specs/truth/features/<端點>/<模組>/<檔>.feature` (<歸屬>) ``；整檔新增時範疇是整檔，在既有檔中新增 Example 時範疇是那些 Example 的 `檔:行`。
- MODIFY、DELETE：把 truth-delta 的 MODIFY 或 DELETE 列，依原因追到的最初依據（`既有需求異動 #n` 或 `clarify YYYY-MM-DD：…`；「連帶」沿觸發列往上追）與端點分組，每組一個 Phase，標題為 `MODIFY <最初依據> › <端點>` 或 `DELETE <最初依據> › <端點>`。
- 最初依據不是既有需求異動或 clarify 的低風險 MODIFY（例如句型換模組，原因為連帶某個 ADD feature）：同端點已有 MODIFY Phase 時併入，沒有時另設 `MODIFY 使用者故事 n › <端點>`。
- MODIFY 的範疇除了 truth-delta 列出的 Example，還包括 `list_changes.py` 列出的、使用被修改句型的所有 Example。
- `features/acceptance/` 是驗收依據，不建 Phase；truth 中沒有異動的 feature 檔不建 Phase。

## Good Example
- 兩列 MODIFY 都追到既有需求異動 #1，依端點分成兩個 Phase；範疇包含 truth-delta 沒列、但用到被改句型的 Example。

```
## Phase 4: MODIFY 既有需求異動 #1 › backend
範疇：`specs/truth/features/backend/聊天訊息/發言頻率.feature:13`、`specs/truth/features/backend/聊天訊息/送出訊息與對局.feature:88`
```

## Bad Example
- 每列 MODIFY 各開一個 Phase，同一個 step 檔被三個 Phase 先後改寫；還把沒有異動的 feature 檔也開了 Phase。

```
## Phase 4: MODIFY `backend/聊天訊息/dsl.md › Given › …`
## Phase 5: MODIFY `backend/聊天訊息/發言頻率.feature › …`
## Phase 6: `specs/truth/features/backend/配對與房間/配對與開房.feature` (US1)
```

# Rule 3 - 每個 Phase 歸屬一個故事或一條既有需求異動 [MUST]
- ADD Phase：先依 `list_changes.py` 對 `@spec` 編號的歸屬，編號寫在本 plan 哪個使用者故事底下就歸該故事，寫在全域需求或系統約束就歸 `(全域 NFR)`。
- 只有 `@ac` tag 時，比對 `features/acceptance/` 中該主題的 Journey 與 spec.md 各故事的敘述判定；涉及多個故事時歸優先序最高者。
- ADD 的 Example 若是因既有需求異動而新增（`@spec` 指向其他 plan 的編號），歸 `(既有需求異動 #n)`。
- MODIFY、DELETE Phase 的歸屬就是標題中的最初依據。
- 每個靠判斷歸屬的 Phase，都在完成回報中列出判定結果與依據。

## Good Example
- 新檔的 `@spec:004/FR-001` 在本 plan 的 US1；另一檔的新增 Example 帶 `@spec:002/FR-006`，歸既有需求異動 #2。

```
## Phase 8: `specs/truth/features/backend/贈品/滿額加贈.feature` (US1)
## Phase 9: `specs/truth/features/backend/訂單/訂單明細.feature` (既有需求異動 #2)
```

## Bad Example
- `@spec:002/FR-006` 在本 plan 的 spec.md 找不到，就依檔名猜成 US1。

```
## Phase 9: `specs/truth/features/backend/訂單/訂單明細.feature` (US1)
```

# Rule 4 - 同類 Phase 內依端點方向與故事排序 [MUST]
- MODIFY：提供方端點先（被引用契約的端點，通常是 backend），使用方後。
- DELETE：使用方端點先（通常是 frontend），提供方後；標題帶 `（由 Phase <M> 取代）` 的 DELETE（被本 plan 某個 ADD 取代的舊行為）排在 Phase M 之後、NFR 重構之前，避免功能中斷。
- ADD：先依故事優先序（P1、P2 …），`(既有需求異動 #n)` 排在故事之後，`(全域 NFR)` 最後；同一歸屬內提供方端點先；同一端點內依檔名排序。

## Good Example
- DELETE 先移除前端呼叫再移除後端路由；被新 API 取代的舊 API 在新 API 之後才刪。

```
## Phase 6: DELETE clarify 2026-11-06：移除取消贈品 › frontend
## Phase 7: DELETE clarify 2026-11-06：移除取消贈品 › backend
## Phase 8: `specs/truth/features/backend/贈品/滿額加贈.feature` (US1)
## Phase 9: DELETE 既有需求異動 #3 › backend（由 Phase 8 取代）
```

## Bad Example
- 先刪後端路由，前端還在呼叫，中間整個 truth 套件變紅；被取代的舊 API 在新 API 完成前就刪掉。

```
## Phase 6: DELETE clarify 2026-11-06：移除取消贈品 › backend
## Phase 7: DELETE 既有需求異動 #3 › backend
## Phase 8: `specs/truth/features/backend/贈品/滿額加贈.feature` (US1)
```

# Rule 5 - Checkpoint 寫可驗證的狀態 [MUST]
- 每個 Phase 末尾的 Checkpoint 寫做完後能實際執行來確認的狀態，不寫「本 Phase 完成」。
- ADD、MODIFY Phase 的 Checkpoint 固定以「`` `<範疇>` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠 ``」開頭；DELETE Phase 固定以「`` `<被移除的部位>` 已無殘留的測試與產品行為；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠 ``」開頭。
- Truth Impact Audit 的 Checkpoint 固定為「`impact-audit.md` 涵蓋 truth-delta 的全部 MODIFY、DELETE 列，且沒有 tasks.md 未涵蓋的影響」。
- Acceptance Gates 不寫 Checkpoint。

## Good Example
- MODIFY Phase 以範疇加整個 truth 套件開頭。

```
**Checkpoint**: `specs/truth/features/backend/聊天訊息/發言頻率.feature:13`、`specs/truth/features/backend/聊天訊息/送出訊息與對局.feature:88` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠
```

## Bad Example
- 只看本 Phase 與先前 Phase，改了既有句型後其他模組的 Example 變紅也不會被發現。

```
**Checkpoint**: `features/backend/發言頻率.feature` 全綠，先前 Phase 的 feature 仍全綠
```

# Rule 6 - Independent Test 只掛在故事的最後一個 Phase [MUST]
- 每個故事最後一個 ADD Phase 的 Checkpoint，在固定句後加「；可完成 `spec.md` 使用者故事 n 的 Independent Test」，以引用代替重寫流程；第一個故事再加「；MVP 可展示」。
- 之後的故事一併引用先前故事（「可分別完成 `spec.md` 使用者故事 1 與使用者故事 2 的 Independent Test」）；最後一個 `(全域 NFR)` Phase 加「；先前各使用者故事的 Independent Test 仍可完成」。
- 其他 Phase 不引用 Independent Test。

## Good Example
- US1 只有最後一個 ADD Phase 引用。

```
**Checkpoint**: `specs/truth/features/frontend/贈品/滿額加贈提示.feature` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠；可完成 `spec.md` 使用者故事 1 的 Independent Test；MVP 可展示
```

## Bad Example
- 後端第一個 Phase 就要求完成故事的 Independent Test，此時前端還沒實作，必然失敗。

```
**Checkpoint**: `specs/truth/features/backend/贈品/滿額加贈.feature` 全綠；可完成 `spec.md` 使用者故事 1 的 Independent Test
```
