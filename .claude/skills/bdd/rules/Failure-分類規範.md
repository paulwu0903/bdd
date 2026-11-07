# Rule 1 - 依症狀把紅燈歸入一個類別 [MUST]
- 每次紅燈先依下表判定類別，再到該類別的修正位置動手；判定之前不改程式。

| 類別 | 典型症狀 | 修正位置 |
|---|---|---|
| 比對 | 步驟顯示 undefined 或 ambiguous | Cucumber Expression 或 parameter type；ambiguous 來自兩份 dsl.md 同句不同義時屬上游缺口 |
| 資料 | Given 佈置不完整、依賴環境既有資料、找不到應存在的實體 | Given step 與 test data builder |
| 定位 | locator、endpoint、payload 格式錯誤，連線或解析失敗 | driver / page object / API client |
| 斷言 | Then 的 assertion 失敗 | 依 Rule 2 判斷是測試錯還是產品錯 |
| 狀態清理 | 單獨跑會過、一起跑會失敗，或反過來 | Before / After hook、World 或 fixture |
| 產品未實作 | 本端呼叫的產品函式、端點或畫面不存在，或回傳尚未實作 | 本端產品碼（green 處理） |
| 他端未實作 | 失敗原因落在範疇以外的端點，例如前端 slice 需要的後端操作不存在 | 不在本範疇修正，先對該端點執行 /bdd |

## Good Example
- 先從錯誤訊息判定類別，再到對應位置修正；前端 slice 等的是後端端點，歸為他端未實作。

```
紅燈：Error: Cannot find module '../../src/services/chat.js'
類別：產品未實作 → green 補本端產品碼

紅燈：前端送出訊息後收到 404 Not Found（POST /api/rooms/4821/chat-messages）
類別：他端未實作 → 回報缺後端的送出訊息操作，建議先對 features/backend 執行 /bdd
```

## Bad Example
- 沒有判定類別就改 Then，把一個 404 當成斷言問題處理。

```
紅燈：AssertionError: expected 'sent', got undefined（driver 打到 404）
修正：把 Then 改成 assert.ok(true)
```

# Rule 2 - 斷言失敗先判斷是測試錯還是產品錯 [MUST]
- 預期值與 feature、dsl.md 一致，實際值錯：產品錯，修產品碼。
- 預期值本身與 feature、dsl.md 不一致（step 寫錯、轉換錯、漏了 dsl.md 的必查項）：測試錯，修 step 或 parameter type。
- 預期值與 feature、dsl.md 一致，但 feature、dsl.md 本身與需求矛盾：依上游缺口判準交還，不改 Then 或 .feature 的預期值來遷就產品。

## Good Example
- 情境寫 1 則，step 也斷言 1 則，實際是 0 則，判定產品還沒送出系統訊息。

```
情境：Then "阿明" 的聊天紀錄共 1 則
紅燈：expected 1, actual 0
判定：產品錯（離開房間沒有產生系統訊息）→ 修產品碼
```

## Bad Example
- 為了讓測試通過，把 .feature 的預期改成產品目前的錯誤行為。

```
情境：Then "阿明" 的聊天紀錄共 1 則
紅燈：expected 1, actual 0
修正：把 .feature 改成 Then "阿明" 的聊天紀錄共 0 則
```
