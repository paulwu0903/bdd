# Rule 1 - 觀察 seam 由上游推出 [MUST]
- 觀察 seam 指測試實際操作與觀察結果的公開入口（例如 API、UI），一律從 plan.md 的系統介面盤點與 research.md、techstack.md 的測試層級、測試工具與執行環境決策推出。
- 每個觀察 seam 都要能指回 research.md 中的某個測試決策，以及它所經過的 plan.md 系統介面；指不回上游的 seam 不設立。
- 只服務內部實作、上游沒有盤點也沒有決定要直接測的模組，不設為觀察 seam。

## Good Example
- research.md 的測試工具分成 API E2E 與 E2E 兩個子段，推出 API 與 UI 兩個觀察 seam，各自經過盤點中的系統介面。

```
research.md `R4. 測試與品質工具`：`› API E2E`（pytest + httpx，真實 MySQL）、`› E2E`（Playwright，Chromium）
→ API seam：經 `聊天 API 介面`、`chat_messages 資料表介面`
→ UI seam：經 `聊天室介面`、`聊天 API 介面`
```

## Bad Example
- 上游沒有決定直接測 service 或 repository，卻自行設立兩個 seam，產生一組上游沒有的測試層級。

```
### API seam
### ChatService seam
### ChatRepository seam
```

# Rule 2 - 計畫不重述上游內容 [MUST]
- test-plan.md 不寫受測介面總覽，也不重述 spec 的 FR、NFR 原文、User Story 的 Goal、research.md 的測試工具與決策，或 plan.md 的 Public Seam 與介面內容。
- 卡片以識別碼指向上游：「對應需求」寫 spec 項目 ID，「涉及系統介面」寫 plan.md 盤點的介面名稱；需要細節時由讀者與下游 skill 讀上游檔案。

## Good Example
- 卡片只寫 ID 與介面名稱，需求原文與工具留在上游檔案。

```
- **觀察 seam**: UI
- **涉及系統介面**: `聊天室介面`、`聊天 API 介面`
- **對應需求**: NFR-001
```

## Bad Example
- 另開總覽重述 Public Seam 與工具，並把 NFR 原文抄進卡片，上游一改兩邊就不一致。

```
## 受測介面總覽
- **Public Seam**: `GET /rooms/{id}/messages`、`POST /rooms/{id}/messages`
- **主要驗證方式**: 以 Playwright（Chromium）操作，pytest + httpx 讀回。

- **對應需求**: NFR-001（一方送出的訊息 MUST 在 2 秒內出現在另一方的聊天室）
```

# Rule 3 - 上游缺漏回報上游修正 [MUST]
- 推導需要的上游內容不存在時（例如盤點沒有卡片會經過的系統介面、research.md 沒有某個觀察 seam 的測試工具或執行環境、Source Code 樹沒有測試檔），不在 test-plan.md 自行補寫。
- 缺漏逐條列入最後回報的「需上游修正」，寫出缺的是哪個上游檔案的哪一段，由使用者回到對應的上游 skill 修正。

## Good Example
- 缺的負載量測工具回報給上游，計畫中不出現自訂的工具。

```
回報：
- 需上游修正：research.md `R4. 測試與品質工具` 沒有負載量測的子段，NFR-007 的量測卡無法定出工具，請以 /technical-research 補上。
```

## Bad Example
- 盤點沒有的介面直接寫進卡片，並在計畫中另開章節補寫工具決策。

```
- **涉及系統介面**: `聊天室介面`、`通知介面`

## 測試工具
- 負載量測使用 Locust（AI 補寫）
```
