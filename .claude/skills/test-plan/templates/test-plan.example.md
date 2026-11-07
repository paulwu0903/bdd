# 測試計畫：房內聊天室

## Fixtures

### API seam

| Fixture | 前置狀態 | 建立步驟 | 就緒條件 | Helper |
|---|---|---|---|---|
| API-FX-SERVER | 已啟動的後端 | 以指定時限建立 app 與 HTTP client，未指定時各時限 600 秒；可再次呼叫以模擬重啟 | 無 | `start_server(timeouts=None) -> client` |
| API-FX-PLAYER | 已註冊玩家 | 呼叫 `POST /players` | 201 | `new_player(client) -> headers` |
| API-FX-WAITING-ROOM | 等待中的房間（配對碼 X） | A 為 API-FX-PLAYER；A 以 X 呼叫 `POST /rooms` | 201，`status` 等於 `waiting` | `open_room(client, code) -> (room_id, host)` |
| API-FX-TWO-IN-ROOM | 雙人同房、準備中（配對碼 X） | API-FX-WAITING-ROOM（X）；B 為 API-FX-PLAYER；B 以 X 呼叫 `POST /rooms/match` | 200，`status` 等於 `preparing` | `room_with_two_players(client, code) -> (room_id, host, guest)` |
| API-FX-PLAYING | 對局進行中、輪到 A（A 答案 a、B 答案 b） | API-FX-TWO-IN-ROOM（1234）；A 以 a、B 以 b 呼叫 `PUT /rooms/{id}/answer` 並以 `{"ready": true}` 呼叫 `PUT /rooms/{id}/ready`；A 呼叫 `POST /rooms/{id}/start` | 200，A 經 `GET /rooms/{id}` 的 `my_turn` 等於 true | `started_game(client, host_answer, guest_answer) -> (room_id, host, guest)` |
| API-FX-FINISHED | 對局已結束、A 獲勝（A 答案 5678、B 答案 9012） | API-FX-PLAYING（5678、9012）；A 以 `9012` 呼叫 `POST /rooms/{id}/guesses` | 200，`a` 等於 4 | `finish_game(client, room_id, host) -> None` |
| API-FX-MESSAGE-SENT | 某成員已送出訊息 m | 該成員以 `{"content": m}` 呼叫 `POST /rooms/{id}/messages` | 201 | `send_message(client, room_id, headers, content) -> dict` |

### UI seam

| Fixture | 前置狀態 | 建立步驟 | 就緒條件 | Helper |
|---|---|---|---|---|
| UI-FX-SERVER | 已啟動的前後端與第一位玩家的瀏覽器 | 以指定時限啟動後端，未指定時回合 4 秒、斷線 4 秒、等待 8 秒；以 Chromium 與指定寬度建立第一位玩家的 browser context，未指定時 1440 px | 首頁 `/` 回應 200 | `startApp(timeouts=None, viewport=1440) -> Page` |
| UI-FX-UNIQUE-CODE | 唯一四碼 | 認領一組本次執行中沒有其他測試使用的四碼 | 無 | `uniqueCode() -> string` |
| UI-FX-GUEST | 另一位玩家 | 建立另一個獨立的 browser context，畫面寬度與第一位玩家相同 | 無 | `guestPage() -> Page` |
| UI-FX-HOST-WAITING | 房主在等待中的房間（配對碼 X） | A 為 UI-FX-SERVER 的頁面；A 開啟 `/`；在輸入欄「四碼」填入 X，按按鈕「開房」 | 文字「等待另一位玩家加入」可見 | `hostOpensRoom(page, code) -> void` |
| UI-FX-TWO-IN-ROOM | 雙人同房、準備中（配對碼 X） | UI-FX-HOST-WAITING（X）；B 為 UI-FX-GUEST，開啟 `/`，在「四碼」填入 X，按「配對」 | B：文字「玩家 2/2」可見 | `twoPlayersInRoom(host, guest, code) -> void` |
| UI-FX-PLAYING | 對局進行中、輪到 A（A 答案 a、B 答案 b） | UI-FX-TWO-IN-ROOM；A、B 各在輸入欄「我的答案」填入答案並按「準備」；A 按「開始遊戲」 | A：文字「輪到你猜」可見 | `startedGame(host, guest, {host, guest}) -> void` |
| UI-FX-MESSAGE-SENT | 某玩家已送出訊息 m | 該玩家在輸入欄「訊息」填入 m，按按鈕「送出訊息」 | 該玩家：文字「我：m」可見 | `sendMessage(page, text) -> void` |

## User Story 1 - 同房玩家在準備與對戰時即時傳送文字訊息

### SL-001 - 準備中送出的訊息雙方都看得到並標示發送者

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `SL-001 a message sent while preparing appears for both players with sender labels`
- **對應需求**: US1-1、FR-001、FR-002
- **唯一測試意圖**: 準備中 A 送出訊息，A 看到「我：」、B 不重新整理也在 2 秒內看到「對手：」與送出時間。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: A 在輸入欄「訊息」填入 `哈囉`，按按鈕「送出訊息」。
- **前置條件**: A（房主）與 B 同在配對碼 X 的房間，房間為準備中；聊天室沒有任何訊息。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`
- **要抓的錯誤實作**: 聊天室只在進房時載入一次、沒有輪詢，B 必須重新整理才看得到；發送者標示存成固定字串，B 也看到「我：哈囉」。
- **主要 oracle**:
  - A：文字「我：哈囉」可見
  - B：文字「對手：哈囉」2 秒內可見（自 A 的「我：哈囉」可見起算）
  - B：「對手：哈囉」訊息項的送出時間 符合 `^\d{2}:\d{2}$`
- **必須維持不變**: A 的輸入欄「訊息」：值 等於空字串
- **本案例不驗證**: 沒有訊息時的空狀態。

### SL-002 - 沒有任何訊息時顯示空狀態提示

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-002 empty chat shows a greeting prompt`
- **對應需求**: FR-007
- **唯一測試意圖**: 準備中的房間尚無訊息時，聊天室顯示空狀態提示且可以輸入。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 元件「聊天室」
- **受測操作**: 讀取 A 的聊天室。
- **前置條件**: A 與 B 同在配對碼 X 的房間，房間為準備中；聊天室沒有任何訊息。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`
- **要抓的錯誤實作**: 空列表直接渲染成空白區塊，沒有任何提示。
- **主要 oracle**:
  - A：文字「還沒有訊息，打聲招呼吧」可見
  - A：輸入欄「訊息」可用
- **必須維持不變**: 無
- **本案例不驗證**: 等待加入時的停用狀態。

### SL-003 - 對戰中的訊息依送出順序排列

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `test_sl_003_messages_during_game_are_listed_in_send_order`
- **對應需求**: US1-2、FR-001、FR-002
- **唯一測試意圖**: 對戰中雙方先後送出的訊息，依送出順序排列並帶遞增的 `seq`。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `GET /rooms/{id}/messages`
- **受測操作**: 讀取 A 的 `GET /rooms/{id}/messages`。
- **前置條件**: 對局 `status` 等於 `playing`，輪到 A；B 已送出「快點啦」，之後 A 送出「讓我想想」。
- **建立方式**: `started_game(client, "5678", "9012")` → `(room_id, A, B)`；`send_message(client, room_id, B, "快點啦")`；`send_message(client, room_id, A, "讓我想想")`
- **要抓的錯誤實作**: 列表依發送者分組（先列自己的訊息再列對手的），而不是依送出順序。
- **主要 oracle**:
  - A 的回應：`messages[*].content` 等於 `["快點啦", "讓我想想"]`
  - A 的回應：`messages[*].seq` 等於 `[1, 2]`
  - A 的回應：`messages[*].sender` 等於 `["opponent", "me"]`
- **必須維持不變**: 無
- **本案例不驗證**: 送出訊息對輪次的影響。

### SL-004 - 送出訊息不消耗回合也不新增猜測

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_004_sending_message_does_not_change_turn_or_guesses`
- **對應需求**: US1-2、FR-005
- **唯一測試意圖**: 輪到 A 時 A 送出內容恰為四碼的訊息，輪次與猜測紀錄保持原樣。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: A 以 `{"content": "9012"}` 送出訊息（內容恰好是 B 的答案）。
- **前置條件**: 對局 `status` 等於 `playing`，輪到 A；猜測紀錄為 0 筆；A 答案 5678、B 答案 9012。
- **建立方式**: `started_game(client, "5678", "9012")` → `(room_id, A, B)`
- **要抓的錯誤實作**: 訊息與猜測共用同一個提交流程，內容是四碼時被當成猜測處理並換手。
- **主要 oracle**:
  - A 的回應：status code 等於 201
- **必須維持不變**: A 經 `GET /rooms/{id}`：`my_turn` 等於 true；A 經 `GET /rooms/{id}`：`guesses` 數量為 0；A 經 `GET /rooms/{id}`：`status` 等於 `playing`
- **本案例不驗證**: 回合計時是否被重設。

### SL-005 - 送出訊息不重設回合計時

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_005_sending_message_does_not_reset_turn_timer`
- **對應需求**: US1-3、FR-005
- **唯一測試意圖**: 回合中途送出訊息後，回合仍依原本的起算點逾時。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `GET /rooms/{id}`
- **受測操作**: 讀取 B 的 `GET /rooms/{id}`（自 A 的回合開始起算 1.8 秒時）。
- **前置條件**: 回合時限 1.5 秒；對局 `status` 等於 `playing`，輪到 A；A 在回合開始後 0.8 秒送出「再等我一下」，之後未提交猜測。
- **建立方式**: `start_server(Timeouts(turn_seconds=1.5, disconnect_seconds=600, waiting_seconds=600))` → client；`started_game(client, "5678", "9012")` → `(room_id, A, B)`，記下開局時刻 t0；等到 t0 + 0.8 秒；`send_message(client, room_id, A, "再等我一下")`；等到 t0 + 1.8 秒
- **要抓的錯誤實作**: 送出訊息時更新 `turn_started_at`（例如把「最後活動時間」與回合起算點共用同一欄位），回合被延長到 t0 + 2.3 秒。
- **主要 oracle**:
  - B 的回應：`my_turn` 等於 true
  - B 的回應：`turn_timed_out` 等於 `host`
- **必須維持不變**: 無
- **本案例不驗證**: 回合逾時本身的規則。

### SL-006 - 對戰中可以聊天且輪次提示不受影響

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-006 players can chat during the game without affecting the turn`
- **對應需求**: US1-2、FR-001、FR-005
- **唯一測試意圖**: 對戰中非輪到的玩家送出訊息，雙方看到訊息，輪次提示維持不變。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: B 在輸入欄「訊息」填入 `快點啦`，按按鈕「送出訊息」。
- **前置條件**: 對局進行中，A 答案 5678、B 答案 9012，輪到 A。
- **建立方式**: `startedGame(A, B, {host: "5678", guest: "9012"})`
- **要抓的錯誤實作**: 對戰中把聊天室收起或停用，只在準備中開放。
- **主要 oracle**:
  - B：文字「我：快點啦」可見
  - A：文字「對手：快點啦」2 秒內可見（自 B 的「我：快點啦」可見起算）
- **必須維持不變**: A：文字「輪到你猜」可見；A：按鈕「送出猜測」可用
- **本案例不驗證**: 回合計時是否被重設。

### SL-007 - 空白與過長的訊息被拒絕

- **案例類型**: TDD Slice
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_007_blank_or_too_long_message_is_rejected`
- **對應需求**: US1-4、FR-003
- **唯一測試意圖**: 去除前後空白後為空、或超過 200 個字元的訊息被拒絕並說明原因，且不寫入房間。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: A 以下列參數各送出一次：`blank`：`"   "`（期望 detail「訊息不可為空白」）、`empty`：`""`（期望 detail「訊息不可為空白」）、`too_long`：`"字" * 201`（期望 detail「訊息最多 200 字」）。
- **前置條件**: A 與 B 同在配對碼 1234 的房間，`status` 等於 `preparing`；房間沒有任何訊息。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_id, A, B)`
- **要抓的錯誤實作**: 長度檢查在去除空白之前做，`"   "` 長度為 3 被當成合法訊息寫入。
- **主要 oracle**:
  - 每個參數，A 的回應：status code 等於 422
  - 每個參數，A 的回應：`detail` 等於該參數的期望 detail
- **必須維持不變**: 每個參數，B 經 `GET /rooms/{id}/messages`：`messages` 數量為 0
- **本案例不驗證**: 恰好 200 個字元的邊界與去除空白後的保存內容。

### SL-008 - 被拒絕的訊息在畫面上顯示原因

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-008 a rejected message shows the reason and never appears in the chat`
- **對應需求**: US1-4、FR-003
- **唯一測試意圖**: 只含空白的訊息被拒絕時畫面顯示原因，雙方聊天室都沒有新訊息。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: A 在輸入欄「訊息」填入 `   `（三個空白），按按鈕「送出訊息」。
- **前置條件**: A 與 B 同在配對碼 X 的房間，房間為準備中；聊天室沒有任何訊息。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`
- **要抓的錯誤實作**: 前端先在畫面上樂觀地加入訊息，被拒絕後沒有撤下，A 看到一則空白訊息。
- **主要 oracle**:
  - A：文字「訊息不可為空白」可見
- **必須維持不變**: A：文字「還沒有訊息，打聲招呼吧」可見；B：文字「還沒有訊息，打聲招呼吧」可見
- **本案例不驗證**: 超過 200 個字元的拒絕。

### SL-009 - 恰好 200 個字元的訊息以去除前後空白後的內容保存

- **案例類型**: TDD Slice
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `test_sl_009_message_at_limit_is_saved_trimmed`
- **對應需求**: FR-003、NFR-005
- **唯一測試意圖**: 去除前後空白後恰好 200 個字元的訊息被接受，並以去除空白後的內容保存，emoji 每個記 1 個字元。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: A 以下列參數各送出一次：`cjk`：`"  " + "字" * 200 + "  "`（期望保存 `"字" * 200`）、`emoji`：`"👍" * 200`（期望保存 `"👍" * 200`，200 個 code point）。
- **前置條件**: A 與 B 同在配對碼 1234 的房間，`status` 等於 `preparing`。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_id, A, B)`
- **要抓的錯誤實作**: 以 UTF-8 位元組數計算長度，200 個中文字（600 bytes）被判為過長；資料表欄位以 `utf8` 而非 `utf8mb4` 建立，emoji 寫入失敗；保存原字串而沒有去除前後空白。
- **主要 oracle**:
  - 每個參數，A 的回應：status code 等於 201
  - 每個參數，B 經 `GET /rooms/{id}/messages`：最後一則的 `content` 等於該參數的期望保存內容
- **必須維持不變**: 無
- **本案例不驗證**: 超過上限的拒絕訊息。

### SL-010 - 等待加入的房間不接受訊息

- **案例類型**: TDD Slice
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_010_waiting_room_does_not_accept_messages`
- **對應需求**: US1-5、FR-004
- **唯一測試意圖**: 只有房主一人的 `waiting` 房間拒絕訊息並說明原因。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: A 以 `{"content": "有人嗎"}` 送出訊息。
- **前置條件**: A 的房間配對碼 1234，`status` 等於 `waiting`，房內只有 A。
- **建立方式**: `open_room(client, "1234")` → `(room_id, A)`
- **要抓的錯誤實作**: 只檢查送出者是否為房間成員，沒有檢查房間狀態，房主在 `waiting` 時也能送出。
- **主要 oracle**:
  - A 的回應：status code 等於 409
  - A 的回應：`detail` 等於 `對手加入後即可聊天`
- **必須維持不變**: A 經 `GET /rooms/{id}/messages`：`messages` 數量為 0
- **本案例不驗證**: 已關閉房間的拒絕。

### SL-011 - 等待加入時聊天室停用並提示

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-011 chat is disabled while waiting for an opponent`
- **對應需求**: US1-5、FR-004
- **唯一測試意圖**: 房內只有房主時，訊息輸入欄停用並說明原因。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 元件「聊天室」
- **受測操作**: 讀取 A 的聊天室。
- **前置條件**: A 的房間配對碼 X，為等待加入，房內只有 A。
- **建立方式**: `uniqueCode()` → X；`hostOpensRoom(A, X)`
- **要抓的錯誤實作**: 聊天室不論房間狀態都顯示可用的輸入欄，送出後才收到後端的 409。
- **主要 oracle**:
  - A：輸入欄「訊息」停用
  - A：按鈕「送出訊息」停用
  - A：文字「對手加入後即可聊天」可見
- **必須維持不變**: 無
- **本案例不驗證**: 後端對等待中房間的拒絕。

### SL-012 - 非成員讀不到房間的訊息

- **案例類型**: TDD Slice
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_012_non_member_cannot_read_room_messages`
- **對應需求**: US1-7、NFR-003
- **唯一測試意圖**: 不屬於房間的玩家讀取該房間訊息時得到 404，看不到任何內容。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `GET /rooms/{id}/messages`
- **受測操作**: C 讀取 A 房間的 `GET /rooms/{id}/messages`。
- **前置條件**: A、B 在配對碼 1234 的房間，A 已送出「秘密」；C 在配對碼 5678 的另一個房間。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_id, A, B)`；`send_message(client, room_id, A, "秘密")`；`room_with_two_players(client, "5678")` → `(_, C, D)`
- **要抓的錯誤實作**: 讀取訊息只驗證 token 有效，不驗證是否為該房間成員。
- **主要 oracle**:
  - C 的回應：status code 等於 404
  - C 的回應：回應本文 不包含 `秘密`
- **必須維持不變**: 無
- **本案例不驗證**: 非成員送出訊息。

### SL-013 - 非成員不能對房間送出訊息

- **案例類型**: TDD Slice
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_013_non_member_cannot_send_to_room`
- **對應需求**: US1-7、NFR-003
- **唯一測試意圖**: 不屬於房間的玩家對該房間送出訊息時得到 404，房間訊息不增加。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: C 以 `{"content": "亂入"}` 對 A 的房間送出訊息。
- **前置條件**: A、B 在配對碼 1234 的房間，沒有任何訊息；C 在配對碼 5678 的另一個房間。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_id, A, B)`；`room_with_two_players(client, "5678")` → `(_, C, D)`
- **要抓的錯誤實作**: 送出訊息的 endpoint 沒有沿用成員檢查，任何持有 token 的玩家都能寫入任意房間。
- **主要 oracle**:
  - C 的回應：status code 等於 404
- **必須維持不變**: A 經 `GET /rooms/{id}/messages`：`messages` 數量為 0
- **本案例不驗證**: 非成員讀取訊息。

### SL-014 - 每個房間只列出自己的訊息

- **案例類型**: TDD Slice
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `test_sl_014_each_room_lists_only_its_own_messages`
- **對應需求**: US1-7、NFR-003
- **唯一測試意圖**: 另一個房間的成員讀取自己房間的訊息時，看不到別的房間的訊息。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `GET /rooms/{id}/messages`
- **受測操作**: C 讀取自己房間（配對碼 5678）的 `GET /rooms/{id}/messages`。
- **前置條件**: A、B 在配對碼 1234 的房間，A 已送出「秘密」；C、D 在配對碼 5678 的房間，D 已送出「嗨」。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_x, A, B)`；`room_with_two_players(client, "5678")` → `(room_y, C, D)`；`send_message(client, room_x, A, "秘密")`；`send_message(client, room_y, D, "嗨")`
- **要抓的錯誤實作**: 查詢訊息時漏掉房間條件，回傳全平台的訊息。
- **主要 oracle**:
  - C 的回應：`messages[*].content` 等於 `["嗨"]`
- **必須維持不變**: 無
- **本案例不驗證**: 非成員直接讀取別的房間。

### SL-015 - 同一房間雙方同時送出時每則恰好保存一次且順序一致

- **案例類型**: TDD Slice
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `test_sl_015_concurrent_messages_in_one_room_are_all_kept_in_one_order`
- **對應需求**: US1-6、NFR-002
- **唯一測試意圖**: 同一房間大量同時送出的訊息全部保存，`seq` 不重複，雙方讀到的順序相同。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: A 與 B 以 20 個執行緒同時送出訊息：A 送 `A1` 至 `A10`，B 送 `B1` 至 `B10`。
- **前置條件**: A 與 B 同在配對碼 1234 的房間，`status` 等於 `preparing`；房間沒有任何訊息。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_id, A, B)`；20 個執行緒以 barrier 同步後同時送出
- **要抓的錯誤實作**: 以「目前訊息數 + 1」計算 `seq` 且沒有加鎖，兩則訊息拿到相同 `seq` 而排序不穩定。
- **主要 oracle**:
  - 每個請求，送出者的回應：status code 等於 201
  - A 經 `GET /rooms/{id}/messages`：`messages` 數量為 20
  - A 經 `GET /rooms/{id}/messages`：`messages[*].seq` 等於 `[1, 2, …, 20]`
  - B 經 `GET /rooms/{id}/messages`：`messages[*].content` 等於 A 讀回的 `messages[*].content`
- **必須維持不變**: 無
- **本案例不驗證**: 不同房間之間的同時送出。

### SL-016 - 不同房間同時送出互不干擾

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `test_sl_016_concurrent_messages_in_different_rooms_do_not_interfere`
- **對應需求**: NFR-002、NFR-003
- **唯一測試意圖**: 兩個房間同時大量送出時，各房間的 `seq` 各自獨立連號。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: 房間 X 的 A、B 與房間 Y 的 C、D 以 20 個執行緒同時送出，每人 5 則（內容為 `<玩家代號><1-5>`）。
- **前置條件**: A、B 在配對碼 1234 的房間 X；C、D 在配對碼 5678 的房間 Y；兩房間都沒有訊息。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_x, A, B)`；`room_with_two_players(client, "5678")` → `(room_y, C, D)`；20 個執行緒以 barrier 同步後同時送出
- **要抓的錯誤實作**: `seq` 以全平台共用的計數器產生，各房間的 `seq` 出現跳號；或鎖住整張表，使另一房間的請求逾時。
- **主要 oracle**:
  - A 經 `GET /rooms/{id}/messages`（房間 X）：`messages[*].seq` 等於 `[1, 2, …, 10]`
  - C 經 `GET /rooms/{id}/messages`（房間 Y）：`messages[*].seq` 等於 `[1, 2, …, 10]`
  - C 經 `GET /rooms/{id}/messages`（房間 Y）：`messages[*].content` 不包含 `A1`
- **必須維持不變**: 無
- **本案例不驗證**: 同一房間內的順序一致性。

### SL-017 - 含 HTML 與腳本的訊息以純文字顯示

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`
- **測試名稱**: `SL-017 html in a message is shown as plain text`
- **對應需求**: US1-8、NFR-004
- **唯一測試意圖**: 訊息中的 HTML 標籤與腳本經過保存與讀回後逐字顯示，不被解析也不執行。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: B 在輸入欄「訊息」填入 `<b>hi</b><script>alert(1)</script>`，按按鈕「送出訊息」。
- **前置條件**: A 與 B 同在配對碼 X 的房間，房間為準備中；A 的頁面已註冊 dialog 監聽。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；在 A 的頁面記錄所有 `dialog` 事件
- **要抓的錯誤實作**: 前端以 `dangerouslySetInnerHTML` 渲染訊息內容；或後端先轉成 HTML entity 再保存，畫面出現 `&lt;b&gt;`。
- **主要 oracle**:
  - A：文字「對手：<b>hi</b><script>alert(1)</script>」可見
  - A：聊天室內的 `b` 元素 數量為 0
- **必須維持不變**: A 的 dialog 事件：數量為 0
- **本案例不驗證**: 中文、全形字元與 emoji。

### SL-018 - 中文、全形字元與 emoji 原樣顯示

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`
- **測試名稱**: `SL-018 cjk fullwidth and emoji characters are shown as typed`
- **對應需求**: US1-9、NFR-005
- **唯一測試意圖**: 含 emoji 與全形英文的訊息經過保存與讀回後，在雙方畫面逐字顯示。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: A 在輸入欄「訊息」填入 `加油 👍 ＡＢＣ`，按按鈕「送出訊息」。
- **前置條件**: A 與 B 同在配對碼 X 的房間，房間為準備中。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`
- **要抓的錯誤實作**: 後端把全形字元正規化成半形；輸入欄以 `maxLength` 依 UTF-16 長度截斷 emoji。
- **主要 oracle**:
  - A：文字「我：加油 👍 ＡＢＣ」可見
  - B：文字「對手：加油 👍 ＡＢＣ」2 秒內可見（自 A 的「我：加油 👍 ＡＢＣ」可見起算）
- **必須維持不變**: 無
- **本案例不驗證**: 200 個字元上限的計算方式。

### SL-019 - 不提供刪除或撤回訊息的入口

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_019_messages_cannot_be_deleted_or_recalled`
- **對應需求**: US1-10、FR-006
- **唯一測試意圖**: 對已送出訊息的刪除請求沒有對應的入口，訊息維持原樣。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `DELETE /rooms/{id}/messages/{seq}`
- **受測操作**: A 呼叫 `DELETE /rooms/{id}/messages/1`。
- **前置條件**: A 與 B 同在配對碼 1234 的房間，A 已送出「哈囉」（`seq` 為 1）。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_id, A, B)`；`send_message(client, room_id, A, "哈囉")`
- **要抓的錯誤實作**: 為了實作「收回訊息」加上刪除單則訊息的 endpoint，正式環境也開放。
- **主要 oracle**:
  - A 的回應：status code 屬於 {404, 405}
- **必須維持不變**: B 經 `GET /rooms/{id}/messages`：`messages[*].content` 等於 `["哈囉"]`
- **本案例不驗證**: 畫面上的修改與刪除操作。

### SL-020 - 已送出的訊息在畫面上沒有修改與刪除操作

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-020 sent messages offer no edit delete or recall action`
- **對應需求**: US1-10、FR-006
- **唯一測試意圖**: 聊天室內找不到任何修改、刪除或收回訊息的操作。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 元件「聊天室」
- **受測操作**: 讀取 A 的聊天室（含右鍵點擊「我：哈囉」後的畫面）。
- **前置條件**: A 與 B 同在配對碼 X 的房間，A 已送出「哈囉」。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；`sendMessage(A, "哈囉")`；A 右鍵點擊「我：哈囉」
- **要抓的錯誤實作**: 訊息項 hover 時出現「刪除」小按鈕。
- **主要 oracle**:
  - A：按鈕「編輯」數量為 0
  - A：按鈕「刪除」數量為 0
  - A：按鈕「收回」數量為 0
- **必須維持不變**: 無
- **本案例不驗證**: 後端是否存在刪除的入口。

### SL-021 - 送出失敗時顯示錯誤與重試並保留輸入內容

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-021 failed send shows an error with retry and keeps the draft`
- **對應需求**: FR-007
- **唯一測試意圖**: 送出訊息的請求連線失敗時，顯示失敗提示與重試按鈕，輸入內容保留。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: A 在輸入欄「訊息」填入 `哈囉`，按按鈕「送出訊息」。
- **前置條件**: A 與 B 同在配對碼 X 的房間，房間為準備中；A 的 `POST **/api/rooms/*/messages` 請求會被中斷。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；在 A 的 context 以 `route.abort()` 中斷 `POST **/api/rooms/*/messages`
- **要抓的錯誤實作**: 送出前就清空輸入欄，失敗後內容遺失；錯誤被吞掉，畫面沒有任何提示。
- **主要 oracle**:
  - A：文字「訊息傳送失敗」可見
  - A：按鈕「重試」可見
  - A 的輸入欄「訊息」：值 等於 `哈囉`
- **必須維持不變**: B：文字「還沒有訊息，打聲招呼吧」可見
- **本案例不驗證**: 按下重試後的結果。

### SL-022 - 連線恢復後按重試即送出

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-022 retry after a failed send delivers the message`
- **對應需求**: FR-007
- **唯一測試意圖**: 送出失敗後連線恢復，按「重試」即送出原本的內容並清除失敗提示。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「重試」
- **受測操作**: A 按按鈕「重試」。
- **前置條件**: A 與 B 同在配對碼 X 的房間；A 送出「哈囉」時連線失敗，畫面顯示「訊息傳送失敗」，輸入欄保留「哈囉」；之後連線已恢復。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；在 A 的 context 中斷 `POST **/api/rooms/*/messages`；A 在「訊息」填入 `哈囉` 並按「送出訊息」，等到文字「訊息傳送失敗」可見；移除中斷規則
- **要抓的錯誤實作**: 「重試」重新載入整個房間而沒有重送訊息。
- **主要 oracle**:
  - A：文字「我：哈囉」可見
  - B：文字「對手：哈囉」2 秒內可見（自 A 按下「重試」起算）
- **必須維持不變**: A：文字「訊息傳送失敗」數量為 0
- **本案例不驗證**: 送出中的防重複送出。

### SL-023 - 送出中停用按鈕避免重複送出

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-023 send button is disabled while a message is being sent`
- **對應需求**: FR-007
- **唯一測試意圖**: 送出請求進行中無法再次送出，同一次輸入只產生一則訊息。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: A 在輸入欄「訊息」填入 `哈囉`，連按兩次按鈕「送出訊息」。
- **前置條件**: A 與 B 同在配對碼 X 的房間，聊天室沒有任何訊息；A 的 `POST **/api/rooms/*/messages` 請求會被延遲 1.5 秒。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；將 A 的 context 中 `POST **/api/rooms/*/messages` 的請求延遲 1.5 秒
- **要抓的錯誤實作**: 送出時沒有鎖住按鈕，連點產生兩則相同的訊息。
- **主要 oracle**:
  - A：按鈕「送出訊息」停用（在第一次按下後、回應抵達前）
  - B：文字「對手：哈囉」數量為 1（自 A 的「我：哈囉」可見後再等 2 秒）
- **必須維持不變**: 無
- **本案例不驗證**: 送出失敗的處理。

### SL-024 - 新訊息出現時捲動到最新一則

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-024 chat scrolls to the newest message`
- **對應需求**: FR-007
- **唯一測試意圖**: 聊天室訊息超過可視高度後，對手的新訊息到達時自動捲動到最新一則。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 元件「聊天室」
- **受測操作**: B 在輸入欄「訊息」填入 `訊息 30`，按按鈕「送出訊息」。
- **前置條件**: A 與 B 同在配對碼 X 的房間；B 已依序送出「訊息 1」至「訊息 29」，A 的聊天室已出現「對手：訊息 29」。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；以迴圈呼叫 `sendMessage(B, "訊息 " + i)`，i 為 1 至 29；等到 A：文字「對手：訊息 29」可見
- **要抓的錯誤實作**: 列表固定停在頂端，新訊息加在可視範圍之外。
- **主要 oracle**:
  - A：文字「對手：訊息 30」2 秒內可見（自 B 的「我：訊息 30」可見起算）
  - A：聊天室列表的捲動位置 等於 最底端
- **必須維持不變**: 無
- **本案例不驗證**: 500 則訊息的完整性。

### SL-025 - 一方送出的訊息 2 秒內出現在另一方畫面

- **案例類型**: NFR 量測
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`
- **測試名稱**: `SL-025 every message reaches the opponent within 2 seconds`
- **對應需求**: NFR-001
- **唯一測試意圖**: 單一房間連續互傳時，每一則訊息都在 2 秒內出現在對手畫面。
- **測試檔**: `frontend/e2e/chat-nfr.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: A 與 B 交替送出共 20 則訊息（A 送 `a1` 至 `a10`，B 送 `b1` 至 `b10`），每則等到送出者的「我：<內容>」可見後才送下一則。
- **量測條件**: 單一房間；每則量測自送出者的「我：<內容>」可見起，至對手的「對手：<內容>」可見止的時間。
- **前置條件**: A 與 B 同在配對碼 X 的房間，房間為準備中；聊天室沒有任何訊息。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`
- **要抓的錯誤實作**: 輪詢間隔設為 3 秒；或每次輪詢都重新抓取全部訊息並整份重繪，訊息變多後延遲超過 2 秒。
- **主要 oracle**:
  - 20 則訊息中，送達時間在 2 秒內者：數量為 20
- **必須維持不變**: 無
- **本案例不驗證**: 100 間房同時聊天時的同步時限。

### SL-026 - 兩位玩家進房後互傳訊息的完整旅程

- **案例類型**: 旅程（預期不先紅）
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `SL-026 two players open a room and exchange messages`
- **對應需求**: US1-1、FR-001、FR-002
- **唯一測試意圖**: 從首頁開房與配對，到雙方互傳一來一往的訊息，全程不需重新整理。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: 依序操作，順序本身是受測行為：(1) A 在「訊息」填入 `哈囉` 並按「送出訊息」；(2) 等到 B：文字「對手：哈囉」可見；(3) B 在「訊息」填入 `你好` 並按「送出訊息」。
- **前置條件**: A 與 B 都位於首頁；配對碼 X 尚未被使用。
- **建立方式**: `uniqueCode()` → X；`hostOpensRoom(A, X)`；B 開啟 `/`，在「四碼」填入 X 並按「配對」，等到 B：文字「玩家 2/2」可見
- **要抓的錯誤實作**: 聊天室只在房主那側輪詢，挑戰者的回覆不會出現在房主畫面。
- **主要 oracle**:
  - 步驟 (1) B：文字「對手：哈囉」2 秒內可見（自 A 的「我：哈囉」可見起算）
  - 步驟 (3) A：文字「對手：你好」2 秒內可見（自 B 的「我：你好」可見起算）
- **必須維持不變**: 無
- **本案例不驗證**: 重新整理後的紀錄還原。

## User Story 2 - 聊天紀錄延續：重新整理、換挑戰者與賽後檢視

### SL-027 - 新挑戰者看到歷史訊息且已離開者標示為「已離開的玩家」

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`
- **測試名稱**: `SL-027 new challenger sees earlier messages labelled with the departed player`
- **對應需求**: US2-2、FR-009
- **唯一測試意圖**: 開局前換挑戰者後，新挑戰者看到全部歷史，前一位挑戰者的訊息對房內所有成員顯示「已離開的玩家」。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 元件「聊天室」
- **受測操作**: 讀取 C 的聊天室。
- **前置條件**: A（房主）送出「哈囉」、B 送出「你好」後，B 按「離開」回到首頁；C 以配對碼 X 加入同一房間。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；`sendMessage(A, "哈囉")`；`sendMessage(B, "你好")`；B 按按鈕「離開」，等到 B 的網址等於 `/`；`guestPage()` → C；C 開啟 `/`，在「四碼」填入 X 並按「配對」，等到 C：文字「玩家 2/2」可見
- **要抓的錯誤實作**: 後端依「送出時的角色」計算發送者，B 的訊息對 C 顯示為「對手」；或前端只區分「我」與「對手」，把 `departed` 也顯示成「對手」。
- **主要 oracle**:
  - C：文字「對手：哈囉」可見
  - C：文字「已離開的玩家：你好」可見
  - A：文字「已離開的玩家：你好」2 秒內可見（自 C 的「玩家 2/2」可見起算）
- **必須維持不變**: 無
- **本案例不驗證**: 已離開的 B 能否再讀取訊息。

### SL-028 - 已離開的玩家讀不到原房間的訊息

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_028_departed_player_cannot_read_former_room_messages`
- **對應需求**: US2-3、NFR-003
- **唯一測試意圖**: 開局前離開的挑戰者，之後讀取原房間訊息得到 404。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `GET /rooms/{id}/messages`
- **受測操作**: B 讀取原房間的 `GET /rooms/{id}/messages`。
- **前置條件**: A、B 在配對碼 1234 的房間，B 送出「你好」後離開；C 已加入並送出「新來的」。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_id, A, B)`；`send_message(client, room_id, B, "你好")`；B 呼叫 `POST /rooms/{id}/leave`（200）；`new_player(client)` → C，C 以 `1234` 呼叫 `POST /rooms/match`（200）；`send_message(client, room_id, C, "新來的")`
- **要抓的錯誤實作**: 權限以「曾經送出過訊息的玩家」判斷，離開者仍能讀到之後的對話。
- **主要 oracle**:
  - B 的回應：status code 等於 404
  - B 的回應：回應本文 不包含 `新來的`
- **必須維持不變**: 無
- **本案例不驗證**: 已離開者送出訊息。

### SL-029 - 已離開的玩家不能對原房間送出訊息

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_029_departed_player_cannot_send_to_former_room`
- **對應需求**: US2-3、NFR-003
- **唯一測試意圖**: 開局前離開的挑戰者，之後對原房間送出訊息得到 404，房間訊息不增加。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: B 以 `{"content": "我又回來了"}` 對原房間送出訊息。
- **前置條件**: A、B 在配對碼 1234 的房間，A 已送出「哈囉」，B 已離開，房間 `status` 等於 `waiting`。
- **建立方式**: `room_with_two_players(client, "1234")` → `(room_id, A, B)`；`send_message(client, room_id, A, "哈囉")`；B 呼叫 `POST /rooms/{id}/leave`（200）
- **要抓的錯誤實作**: 送出訊息時以訊息表中的歷史發送者判斷成員資格。
- **主要 oracle**:
  - B 的回應：status code 等於 404
- **必須維持不變**: A 經 `GET /rooms/{id}/messages`：`messages[*].content` 等於 `["哈囉"]`
- **本案例不驗證**: 已離開者讀取訊息。

### SL-030 - 房間關閉後不接受新訊息

- **案例類型**: TDD Slice
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`
- **測試名稱**: `test_sl_030_closed_room_does_not_accept_messages`
- **對應需求**: US2-4、FR-010
- **唯一測試意圖**: 對局結束、房間關閉後，成員送出訊息被拒絕並說明原因，既有紀錄保留。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: B 以 `{"content": "再一局"}` 送出訊息。
- **前置條件**: 對局中 A 送出「加油」、B 送出「GG」，之後 A 猜中 9012 獲勝，`status` 等於 `closed`。
- **建立方式**: `started_game(client, "5678", "9012")` → `(room_id, A, B)`；`send_message(client, room_id, A, "加油")`；`send_message(client, room_id, B, "GG")`；`finish_game(client, room_id, A)`
- **要抓的錯誤實作**: 狀態檢查只擋 `waiting`，`closed` 房間仍可寫入訊息；或房間關閉時連同訊息一起刪除。
- **主要 oracle**:
  - B 的回應：status code 等於 409
  - B 的回應：`detail` 等於 `對局已結束，聊天室僅供檢視`
- **必須維持不變**: A 經 `GET /rooms/{id}/messages`：`messages[*].content` 等於 `["加油", "GG"]`
- **本案例不驗證**: 結算畫面的唯讀呈現。

### SL-031 - 對局結束後結算畫面的聊天室為唯讀

- **案例類型**: TDD Slice
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-031 chat becomes read only on the result screen`
- **對應需求**: US2-4、FR-010
- **唯一測試意圖**: 房間關閉後，結算畫面仍依序顯示聊天紀錄，輸入欄停用並說明原因。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 元件「聊天室」
- **受測操作**: B 在輸入欄「猜測」填入 `5678`，按按鈕「送出猜測」（B 猜中而獲勝、房間關閉）。
- **前置條件**: 對局進行中，A 答案 5678、B 答案 9012；A 已送出「加油」、B 已送出「GG」；A 已猜 9120，輪到 B。
- **建立方式**: `startedGame(A, B, {host: "5678", guest: "9012"})`；`sendMessage(A, "加油")`；`sendMessage(B, "GG")`；A 在「猜測」填入 `9120` 並按「送出猜測」，等到 B：文字「輪到你猜」可見
- **要抓的錯誤實作**: 結算畫面整個替換房間畫面，聊天室隨之消失。
- **主要 oracle**:
  - A：文字「你落敗了」2 秒內可見（自 B 的「你獲勝了」可見起算）
  - A：聊天室訊息項的文字依序 等於 `["我：加油", "對手：GG"]`
  - A：輸入欄「訊息」停用
  - A：文字「對局已結束，聊天室僅供檢視」可見
- **必須維持不變**: 無
- **本案例不驗證**: 後端對已關閉房間的拒絕。

### SL-032 - 後端重啟後聊天紀錄完整讀回

- **案例類型**: 防回歸（預期不先紅）
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `test_sl_032_chat_history_survives_server_restart`
- **對應需求**: US2-1、FR-008
- **唯一測試意圖**: 後端重新啟動後，成員讀到與重啟前相同的完整紀錄。
- **測試檔**: `backend/tests/test_chat.py`
- **受測部位**: `GET /rooms/{id}/messages`
- **受測操作**: 以重啟後的 client 讀取 A 的 `GET /rooms/{id}/messages`。
- **前置條件**: A、B 在配對碼 1234 的房間依序送出「哈囉」「你好」「準備好了嗎」；後端已重新啟動（共用同一個測試資料庫）。
- **建立方式**: `start_server()` → client1；`room_with_two_players(client1, "1234")` → `(room_id, A, B)`；依序 `send_message(client1, room_id, A, "哈囉")`、`send_message(client1, room_id, B, "你好")`、`send_message(client1, room_id, A, "準備好了嗎")`；`start_server()` → client2
- **要抓的錯誤實作**: 訊息只存在行程記憶體中的 list，重啟後全部消失。
- **主要 oracle**:
  - A 的回應：`messages[*].content` 等於 `["哈囉", "你好", "準備好了嗎"]`
  - A 的回應：`messages[*].sender` 等於 `["me", "opponent", "me"]`
- **必須維持不變**: 無
- **本案例不驗證**: 前端重新整理後的還原時限。

### SL-033 - 重新整理後 3 秒內依序還原聊天紀錄

- **案例類型**: NFR 量測
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-033 reloading the room restores the full chat history within 3 seconds`
- **對應需求**: US2-1、FR-008、NFR-006、SC-004
- **唯一測試意圖**: 房內已有多則訊息時，每次重新整理都在 3 秒內依原順序還原全部訊息與發送者標示。
- **測試檔**: `frontend/e2e/chat-nfr.spec.ts`
- **受測部位**: `/rooms/[id]` · 元件「聊天室」
- **受測操作**: A 重新整理頁面 10 次，每次等到「對手：m30」可見後才進行下一次。
- **量測條件**: 房內 30 則訊息；每次量測自 A 觸發重新整理起，至「對手：m30」可見止的時間。
- **前置條件**: A 與 B 同在配對碼 X 的房間；A、B 交替送出 `m1` 至 `m30`（奇數為 A、偶數為 B）。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；以迴圈呼叫 `sendMessage(i 為奇數 ? A : B, "m" + i)`，i 為 1 至 30
- **要抓的錯誤實作**: 聊天紀錄只保存在前端 state，重新整理後只剩之後的新訊息；或重新整理後逐則分頁載入，30 則需要超過 3 秒。
- **主要 oracle**:
  - 10 次重新整理中，「對手：m30」在 3 秒內可見者：數量為 10
  - 第 10 次重新整理後，A：聊天室訊息項 數量為 30
  - 第 10 次重新整理後，A：聊天室第一個訊息項的文字 等於 `我：m1`
- **必須維持不變**: 無
- **本案例不驗證**: 斷線後重連。

## 跨故事旅程

### SL-034 - 從開房聊天、換挑戰者到賽後檢視的完整旅程

- **案例類型**: 旅程（預期不先紅）
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `SL-034 chat history follows the room through a new challenger to the result screen`
- **對應需求**: US1-1、US2-2、US2-4、FR-001、FR-009、FR-010
- **唯一測試意圖**: 同一間房從互傳訊息、換挑戰者到對局結束，聊天紀錄全程延續並在結束後轉為唯讀。
- **測試檔**: `frontend/e2e/chat.spec.ts`
- **受測部位**: `/rooms/[id]` · 元件「聊天室」
- **受測操作**: 依序操作，順序本身是受測行為：(1) A 在「訊息」填入 `哈囉` 並按「送出訊息」，等到 B：文字「對手：哈囉」可見；(2) B 按「離開」，等到 B 的網址等於 `/`；(3) C 在「四碼」填入 X 並按「配對」，等到 C：文字「玩家 2/2」可見；(4) A 在「我的答案」填入 `5678`、C 填入 `9012`，雙方按「準備」，A 按「開始遊戲」；(5) C 在「訊息」填入 `加油` 並按「送出訊息」；(6) A 在「猜測」填入 `9012` 並按「送出猜測」。
- **前置條件**: A 與 B 同在配對碼 X 的房間，房間為準備中，聊天室沒有任何訊息；C 位於首頁。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；`guestPage()` → C；C 開啟 `/`
- **要抓的錯誤實作**: 換挑戰者時重設了房間的聊天紀錄；或結算時以新的房間狀態重新載入聊天室，遺失換人前的訊息。
- **主要 oracle**:
  - 步驟 (3) C：文字「對手：哈囉」可見
  - 步驟 (6) A：文字「你獲勝了」可見
  - 步驟 (6) C：聊天室訊息項的文字依序 等於 `["對手：哈囉", "我：加油"]`
  - 步驟 (6) C：文字「對局已結束，聊天室僅供檢視」可見
- **必須維持不變**: 無
- **本案例不驗證**: 已離開的玩家的訊息標示。

## 全域 NFR

### SL-035 - 100 間房同時聊天時訊息仍在 2 秒內送達

- **案例類型**: NFR 量測
- **觀察 seam**: API
- **涉及系統介面**: `聊天 API 介面`、`chat_messages 資料表介面`
- **測試名稱**: `test_sl_035_messages_arrive_within_2_seconds_with_100_rooms_chatting`
- **對應需求**: NFR-007、SC-002
- **唯一測試意圖**: 100 間房同時聊天時，至少 95% 的訊息在 2 秒內被對手讀到，且沒有訊息遺失。
- **測試檔**: `backend/tests/load/test_chat_load.py`
- **受測部位**: `POST /rooms/{id}/messages`
- **受測操作**: 100 間房的雙方交替每 1 秒送出 1 則訊息，持續 60 秒；接收方每 1 秒呼叫一次 `GET /rooms/{id}/messages`。
- **量測條件**: 200 位玩家同時連線；每則量測自送出者收到 201 起，至接收方的讀回首次包含該則止的時間。
- **前置條件**: 100 間房各有 2 位玩家且皆為準備中，配對碼依序取「4 個互不相同數字」的前 100 組；所有房間都沒有訊息。
- **建立方式**: `start_server()` → client；對每組配對碼呼叫 `room_with_two_players(client, code)` → 100 組 `(room_id, A, B)`
- **要抓的錯誤實作**: 配發 `seq` 時鎖住整張 `chat_messages` 表，房間之間互相排隊；或列出訊息缺少 `(room_id, seq)` 索引而全表掃描。
- **主要 oracle**:
  - 全部訊息中，送達時間在 2 秒內者所占比例：至少 0.95
  - 全部訊息中，接收方從未讀到者：數量為 0
- **必須維持不變**: 無
- **本案例不驗證**: 畫面渲染所需的時間。

### SL-036 - 單一房間 500 則訊息仍完整依序顯示並即時同步

- **案例類型**: NFR 量測
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`
- **測試名稱**: `SL-036 a room with 500 messages shows them all in order and stays in sync`
- **對應需求**: NFR-007
- **唯一測試意圖**: 房間累積 500 則訊息後，聊天室一則不漏地依序顯示，新訊息仍在 2 秒內同步。
- **測試檔**: `frontend/e2e/chat-nfr.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出訊息」
- **受測操作**: A 在輸入欄「訊息」填入 `m501`，按按鈕「送出訊息」。
- **量測條件**: 房內 500 則訊息；量測自 A 的「我：m501」可見起，至 B 的「對手：m501」可見止的時間。
- **前置條件**: A 與 B 同在配對碼 X 的房間；A 已依序送出 `m1` 至 `m500`，B 的聊天室已出現「對手：m500」。
- **建立方式**: `uniqueCode()` → X；`twoPlayersInRoom(A, B, X)`；以 A 的身分直接呼叫 `POST /rooms/{id}/messages` 500 次（內容 `m1` 至 `m500`）；等到 B：文字「對手：m500」可見
- **要抓的錯誤實作**: 列表加上預設分頁只回最新 100 則，又沒有提供取得更早訊息的方式；或每次輪詢都整份重繪 500 則，同步延遲超過 2 秒。
- **主要 oracle**:
  - B：聊天室訊息項 數量為 501
  - B：聊天室第一個訊息項的文字 等於 `對手：m1`
  - B：文字「對手：m501」2 秒內可見（自 A 的「我：m501」可見起算）
- **必須維持不變**: 無
- **本案例不驗證**: 100 間房同時聊天的容量。

### SL-037 - 375 px 至 1440 px 下聊天室與遊戲操作皆可使用

- **案例類型**: NFR 量測
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`
- **測試名稱**: `SL-037 chat and game controls stay usable from 375 to 1440 px`
- **對應需求**: NFR-008
- **唯一測試意圖**: 各種畫面寬度下，聊天室有多則訊息時仍能送出訊息，且不遮擋送出猜測。
- **測試檔**: `frontend/e2e/chat-nfr.spec.ts`
- **受測部位**: `/rooms/[id]` · 按鈕「送出猜測」
- **受測操作**: A 以下列參數的畫面寬度各執行一次：`narrow`：375 px、`tablet`：768 px、`desktop`：1440 px；每次在輸入欄「猜測」填入 `9120`，按按鈕「送出猜測」。
- **量測條件**: 每個參數各建立一局新對局；不捲動頁面，直接點擊元素。
- **前置條件**: 對局進行中，A 答案 5678、B 答案 9012，輪到 A；B 已送出「訊息 1」至「訊息 10」。
- **建立方式**: 每個參數各呼叫一次 `startApp(viewport=<該參數的寬度>)` → A；`startedGame(A, B, {host: "5678", guest: "9012"})`；以迴圈呼叫 `sendMessage(B, "訊息 " + i)`，i 為 1 至 10；等到 A：文字「對手：訊息 10」可見
- **要抓的錯誤實作**: 聊天室在手機寬度以 `position: fixed` 疊在畫面下半部，蓋住「送出猜測」，點擊被攔截。
- **主要 oracle**:
  - 每個參數，A：文字「9120：1A3B」可見（9 位置相同；0、1、2 存在但位置不同）
- **必須維持不變**: 每個參數，A：輸入欄「訊息」可用
- **本案例不驗證**: Chromium 以外的瀏覽器。

## 未涵蓋項目

- **US2-1**（部分涵蓋）：重新整理後的還原由 SL-032、SL-033 驗證；「斷線 10 秒後重連」的分支未單獨驗證，因 E2E 斷線時限為 4 秒，10 秒會被判離開。
- **FR-006**（部分涵蓋）：刪除入口由 SL-019、畫面上的修改與刪除操作由 SL-020 驗證；後端的修改入口（`PUT`、`PATCH`）未另立案例。
- **SC-001**（未涵蓋）：新玩家 30 秒內完成首次對話的成功率需要真人可用性測試；流程可行性由 SL-026 驗證。
- **SC-003**（部分涵蓋）：SL-012、SL-013、SL-014、SL-028、SL-029 驗證訊息不外流，未量測「次數為 0」的長期統計。
- **SC-004**（部分涵蓋）：SL-033 驗證 10 次重新整理皆在 3 秒內還原，未量測 ≥ 99% 的母體比例。

## 變更紀錄

| 日期 | 案例 | 變更 | 原因 | 依據 |
|---|---|---|---|---|
