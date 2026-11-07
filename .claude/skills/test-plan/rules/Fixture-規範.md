# Rule 1 - 共用的 Arrange 才立為 Fixture [MUST]
- 兩張以上案例卡會用到的前置狀態，立為 Fixture；只有一張卡用到的前置步驟直接寫在該卡的建立方式。
- Fixture 可以以其他 Fixture 為基礎往上疊，建立步驟中以名稱引用。

## Good Example
- 「對局進行中」被多張卡使用，立為 Fixture，並疊在「雙人同房」之上。

```
| API-FX-TWO-IN-ROOM | 雙人同房、準備中（配對碼 X） | API-FX-WAITING-ROOM（X）；B 為 API-FX-PLAYER；B 以 X 呼叫 `POST /rooms/match` | 200，`status` 等於 `preparing` | `room_with_two_players(client, code) -> (room_id, host, guest)` |
| API-FX-PLAYING | 對局進行中、輪到 A（A 答案 a、B 答案 b） | API-FX-TWO-IN-ROOM（1234）；A 以 a、B 以 b 呼叫 `PUT /rooms/{id}/answer` 並以 `{"ready": true}` 呼叫 `PUT /rooms/{id}/ready`；A 呼叫 `POST /rooms/{id}/start` | 200，A 經 `GET /rooms/{id}` 的 `my_turn` 等於 true | `started_game(client, host_answer, guest_answer) -> (room_id, host, guest)` |
```

## Bad Example
- 只有一張卡用到的「已累積 500 則訊息」也立成 Fixture，Fixtures 表膨脹成每張卡的前置步驟清單。

```
| UI-FX-500-MESSAGES | 房內已有 500 則訊息 | …… | …… | `fiveHundredMessages(page)` |
```

# Rule 2 - Fixture 依觀察 seam 分表並以狀態命名 [MUST]
- Fixtures 依觀察 seam 各自成表，表頭寫成 `### <seam> seam`；每個 Fixture 只放在建立它所用的那個 seam 的表內。
- Fixture 名稱寫成 `<seam>-FX-<狀態>`，seam 以大寫英文寫出所屬觀察 seam，狀態以大寫英文與連字號描述，例如 `API-FX-PLAYING`、`UI-FX-HOST-WAITING`。
- 建立步驟只能呼叫該 seam 的公開入口，不直接寫資料庫或呼叫內部函式；啟動受測系統、重建測試資料庫這類測試環境的 Fixture 不在此限。

## Good Example
- 放在 API seam 表內，名稱帶 seam 與狀態；建立步驟只用公開 API。

```
### API seam

| API-FX-WAITING-ROOM | 等待中的房間（配對碼 X） | A 為 API-FX-PLAYER；A 以 X 呼叫 `POST /rooms` | 201，`status` 等於 `waiting` | `open_room(client, code) -> (room_id, host)` |
```

## Bad Example
- 名稱是流水號看不出 seam 與狀態；UI 的 Fixture 混進 API 表；建立步驟直接寫資料表。

```
### API seam

| FX-2 | 等待中的房間 | INSERT INTO rooms (match_code, status) VALUES ('1234', 'waiting') | 無 | `open_room()` |
| UI-FX-HOST-WAITING | 房主在等待中的房間 | …… | …… | `hostOpensRoom(page, code) -> void` |
```

# Rule 3 - 寫出就緒條件與 helper 簽名 [MUST]
- 就緒條件寫出 helper 內要斷言的可觀察結果，前置狀態沒建好時讓測試失敗在 Arrange；確實沒有可斷言結果時寫「無」。
- Helper 寫出名稱、參數與回傳值，不寫實作本體。

## Good Example
- 就緒條件可觀察，helper 簽名完整。

```
| UI-FX-HOST-WAITING | 房主在等待中的房間（配對碼 X） | A 為 UI-FX-SERVER 的頁面；A 開啟 `/`；在輸入欄「四碼」填入 X，按按鈕「開房」 | 文字「等待另一位玩家加入」可見 | `hostOpensRoom(page, code) -> void` |
```

## Bad Example
- 沒有就緒條件，helper 只寫名稱，讀者不知道要傳什麼、拿回什麼。

```
| UI-FX-HOST-WAITING | 房主開好房 | 開房 | | hostOpensRoom |
```

# Rule 4 - 執行環境數值寫成 helper 參數與預設值 [MUST]
- 時限、瀏覽器、畫面寬度這類執行環境的數值，寫成啟動受測系統的 Fixture helper 的參數，並在建立步驟寫出未指定時的預設值。
- 只有個別卡片需要不同的值時，在該卡的建立方式以參數覆寫，不另開章節定義環境設定。

## Good Example
- 預設值寫在建立步驟，helper 以參數接收；需要不同寬度的卡片自行傳入。

```
| UI-FX-SERVER | 已啟動的前後端與第一位玩家的瀏覽器 | 以指定時限啟動後端，未指定時回合 4 秒、斷線 4 秒、等待 8 秒；以 Chromium 與指定寬度建立第一位玩家的 browser context，未指定時 1440 px | 首頁 `/` 回應 200 | `startApp(timeouts=None, viewport=1440) -> Page` |

- **建立方式**: 每個參數各呼叫一次 `startApp(viewport=<該參數的寬度>)` → A
```

## Bad Example
- 數值寫成計畫中的獨立環境章節，helper 沒有參數，讀者得在兩處對照。

```
## 執行環境
- 回合時限 4 秒、瀏覽器 Chromium、寬度 1440 px

| UI-FX-SERVER | 已啟動的前後端 | 依執行環境啟動 | 無 | `startApp() -> Page` |
```
