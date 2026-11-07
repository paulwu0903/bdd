# Rule 1 - Feature Dependencies 依 Phase 用到的他 Phase 能力判定 [MUST]
- Feature Dependencies 表為每個 MODIFY、DELETE、ADD Phase 列一列，`依賴 Phase` 寫它的情境要能通過所必需的其他 Phase 編號（以「、」分隔），沒有就寫「—」；依據寫一句話說明用到對方的哪個能力。
- 所有 MODIFY、DELETE Phase 都依賴 Truth Impact Audit Phase。
- 使用方端點的 MODIFY 依賴提供方端點的同組 MODIFY；提供方端點的 DELETE 依賴使用方端點的同組 DELETE；標題帶「由 Phase M 取代」的 DELETE 依賴 Phase M。
- 前端 ADD 依它的情境實際用到的後端能力判定依賴的後端 Phase，不一律依賴全部後端 Phase。
- 依賴只能指向編號較小的 Phase；需要指向後面的 Phase 時，表示排序違反 `rules/Phase結構-規範.md` Rule 4，應回頭調整排序。

## Good Example
- 前端的 MODIFY 依賴後端的同組 MODIFY；後端的 DELETE 依賴前端的同組 DELETE。

```
| Phase | feature | 依賴 Phase | 依據 |
|---|---|---|---|
| 4 | `…/訂單/訂單明細.feature` | 3 | 依 impact-audit 的 backend 清單對齊 |
| 5 | `…/訂單/訂單明細頁.feature` | 3、4 | 畫面上的明細依賴後端回傳的贈品欄位 |
| 6 | `…/贈品/取消贈品.feature` | 3 | 先移除前端的取消按鈕與呼叫 |
| 7 | `…/贈品/取消贈品.feature` | 3、6 | 前端不再呼叫後才能移除路由 |
```

## Bad Example
- 後端 DELETE 不依賴前端 DELETE，兩者被當成可平行，路由先被刪除時前端還在呼叫。

```
| 6 | `…/贈品/取消贈品.feature` | 3 | 移除前端呼叫 |
| 7 | `…/贈品/取消贈品.feature` | 3 | 移除路由 |
```

# Rule 2 - Parallel Opportunities 以檔案重疊判定能否平行 [MUST]
- 標 [P] 的環境與基礎任務、分屬不同端點的 Acceptance Gates 全套回歸，列為可平行。
- 不同端點的 feature Phase 檔案不重疊，前端 Phase 在其依賴的後端 Phase 完成後，可與後端其餘 Phase 平行，形成後端線與前端線。
- 同一端點的 feature Phase 共用 step 模組檔與產品檔，寫明須依序執行並舉出共用的檔案。

## Good Example
- 指出兩條線的成立條件，以及同端點不能平行的具體共用檔。

```
- 後端與前端的 feature Phase 檔案不重疊：前端 Phase 在其依賴的後端 Phase 完成後，可與後端其餘 Phase 平行，形成後端線與前端線
- 同一端點的 feature Phase 共用 step 模組檔與產品檔（例如 `聊天訊息/前置.ts`、`backend/src/services/chat-service.ts`），須依序執行
```

## Bad Example
- 宣稱所有 feature Phase 都能平行，兩個後端 Phase 同時改 chat-service 會互相覆寫。

```
- 所有 feature Phase 互相獨立，可全部平行
```

# Rule 3 - Parallel Example 以實際任務編號示範兩條線 [MUST]
- Parallel Example 至少示範一組後端線與前端線同時進行：寫出觸發條件（哪個 Phase 完成後），每條線列實際的任務編號鏈、Phase 編號與 feature 路徑，前端線註明它依賴的 Phase。
- 示範的前端 Phase，其依賴的後端 Phase 必須都已在觸發條件中完成。

## Good Example
- Phase 3 完成後，前端線選只依賴 Phase 3 的 feature。

```text
# Phase 3 完成後，後端線與前端線同時進行：
後端線：T010 → T011 → T012（Phase 4，specs/truth/features/backend/聊天訊息/斷線與補齊.feature）
前端線：T031 → T032 → T033（Phase 11，specs/truth/features/frontend/聊天訊息/可見範圍與系統訊息.feature，只依賴 Phase 3）
```

## Bad Example
- 前端線選了依賴 Phase 9 的傳送狀態，Phase 9 此時還沒完成；也沒有寫任務編號。

```text
# Phase 3 完成後：
後端線：斷線與補齊
前端線：傳送狀態
```
