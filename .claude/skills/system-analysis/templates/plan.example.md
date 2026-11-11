# 系統分析規劃

## Project Structure

### Documentation (plan package 與本次修改的 truth)

```text
specs/
├── plans/003-chat-reactions/      # Plan：本次要改什麼、怎麼做
│   ├── spec.md                    # 表情回應的功能規格與既有需求異動 #1（/specify 產出）
│   ├── features/acceptance/       # 驗收 Journey（/spec-by-example 產出）
│   ├── research.md                # 本次的技術決策（/technical-research 產出）
│   ├── plan.md                    # 本檔案
│   ├── ui/
│   │   ├── frontend.md            # 前端端點的表情回應與聊天區異動的畫面規格（ui-plan 產出）
│   │   └── prototype/             # 前端端點的可操作視覺雛形，依現行聊天畫面重做受影響的頁面（ui-plan 產出）
│   ├── truth-delta.md             # 本次對 truth 的 ADD／MODIFY／DELETE 紀錄（/specify 建立，各 truth owner 記錄）
│   ├── impact-audit.md            # 既有測試與程式受 truth 異動影響的盤點（/implement 依 tasks.md 產出）
│   └── tasks.md                   # 任務清單（/tasks 產出）
└── truth/                         # Truth：系統現在是什麼（全專案一份，本次就地修改）
    ├── requirements.md            # 新增表情回應的需求、修改 002/FR-002 的字數上限（/specify 修改）
    ├── contracts/openapi.yaml     # 新增表情回應 API，修改訊息上限、狀態快照與錯誤碼（api-plan 修改）
    ├── data/schema.dbml           # 新增 message_reactions，修改 chat_messages.content 與共通交易（data-plan 修改）
    └── features/                  # 表情回應與 500 字上限的端點 feature 檔與 dsl.md（/dsl-refine 修改）
```

### Source Code (repository root，只列本次新增、修改、刪除的檔案)

```text
backend/
├── db/
│   └── migrations/
│       └── 0003_reactions.sql   # 建立表情回應資料表、放寬訊息內容的長度與檢查限制（新增；資料庫共通介面、message_reactions 資料表介面、chat_messages 資料表介面）
├── src/
│   ├── app.ts                   # 掛載表情回應資源入口（修改；後端共通介面）
│   ├── db/
│   │   ├── maintenance.ts       # 24 小時清除連帶刪除表情回應（修改；資料庫共通介面）
│   │   └── repositories/
│   │       └── reactions.ts     # 表情回應的寫入、改選、移除與依訊息彙總（新增；message_reactions 資料表介面）
│   ├── routes/
│   │   └── reactions.ts         # 加上、改選與移除表情回應（新增；表情回應 API 介面）
│   ├── services/
│   │   ├── reaction-service.ts  # 回應者為房內成員的檢查、每人每則一個回應、寫入後喚醒雙方（新增；表情回應 API 介面）
│   │   └── snapshot.ts          # 快照與結果聊天紀錄帶出每則訊息的回應數量與自己的選擇（修改；狀態同步 API 介面）
│   ├── domain/
│   │   ├── chat-format.ts       # 字數上限改為 500、總量上限隨之調整，前後端共用（修改；聊天訊息 API 介面、聊天區介面）
│   │   ├── schemas.ts           # 新增表情回應的請求與快照欄位型別，前後端共用（修改；後端共通介面、前端共通介面）
│   │   └── error-codes.ts       # 新增表情回應錯誤碼，前後端共用（修改；後端共通介面、前端共通介面）
│   └── lib/                     # 不變更
└── tests/                       # 測試步驟由 /tasks 依 features 的異動規劃

frontend/
├── src/
│   ├── api/
│   │   └── client.ts            # 新增加上、改選與移除表情回應的呼叫（修改；前端共通介面）
│   ├── state/
│   │   └── store.ts             # 依快照合併回應數量，送出中的回應先行顯示（修改；表情回應操作介面）
│   ├── lib/
│   │   └── messages.ts          # 字數提示改為 500 字、新增表情回應錯誤碼文案（修改；前端共通介面、聊天區介面）
│   ├── components/
│   │   ├── ChatInput.tsx        # 字數提示與計數門檻改為 500 字（修改；聊天區介面）
│   │   ├── ChatMessageList.tsx  # 每則訊息下方顯示表情回應列（修改；聊天區介面、結果聊天紀錄介面）
│   │   └── ReactionBar.tsx      # 👍、❤️、😂 三個回應按鈕、數量與自己的選擇（新增；表情回應操作介面）
│   ├── styles/
│   │   └── chat.css             # 表情回應列在 375 px 下不換行溢出（修改；聊天區介面）
│   └── pages/                   # 不變更
└── tests/                       # 測試步驟由 /tasks 依 features 的異動規劃
```

**Structure Decision**: 沿用 repository 現行的切分，不新增目錄：第一層依可獨立建置的 `前端端點` 與 `後端端點` 分成 `frontend/`、`backend/`；`資料庫端點` 的遷移檔接在 `backend/db/migrations/` 既有檔案之後，存取放在 `backend/src/db/repositories/`。端點下依角色分層，表情回應只在既有的 routes、services、repositories、components 中新增檔案；500 字上限只改前後端共用的 `chat-format.ts` 與前端文案，讓同一套計字規則仍只有一個出處。樹中只列本次新增、修改的檔案，沒有異動的資料夾只列到目錄層；每個程式檔的說明標明異動與對應的系統介面，/tasks 依此定位落點，現行程式的其餘檔案以 repository 為準。

## 分析流程規劃

### 系統介面的盤點

本次需求共盤點出 `11` 個系統介面。

1. `前端共通介面`
    - 端點類型：`前端端點`
    - 異動：修改既有
    - 主要介面：表情回應的 API 呼叫、表情回應錯誤碼的文案對應；現行程式：`frontend/src/api/client.ts`、`frontend/src/lib/messages.ts`；features：`frontend/平臺共用`
    - 需求原文依據：需求要求表情回應失敗時提示原因且不改變畫面上的數量；對應 `FR-005`。

2. `聊天區介面`
    - 端點類型：`前端端點`
    - 異動：修改既有
    - 主要介面：字數提示與計數門檻、每則訊息下方的表情回應列、表情回應列不擠壓輸入框；現行程式：`frontend/src/components/ChatInput.tsx`、`frontend/src/components/ChatMessageList.tsx`；features：`frontend/聊天訊息`
    - 需求原文依據：使用者描述要求「訊息上限改成 500 字，然後可以對訊息按 👍、❤️、😂」；對應 `FR-003`、`NFR-001` 與 `002/FR-002`。

3. `表情回應操作介面`
    - 端點類型：`前端端點`
    - 異動：新增
    - 主要介面：三個回應按鈕、自己的選擇高亮、再按一次取消、改選另一個、各回應的數量、送出中先行顯示與失敗還原
    - 需求原文依據：使用者描述要求「可以對訊息按 👍、❤️、😂」；對應 `FR-001`、`FR-002`、`FR-003` 與 `FR-005`。

4. `結果聊天紀錄介面`
    - 端點類型：`前端端點`
    - 異動：修改既有
    - 主要介面：結果畫面的唯讀聊天紀錄顯示回應數量、不提供回應按鈕；現行程式：`frontend/src/pages/ResultPage.tsx`、`frontend/src/components/ChatMessageList.tsx`；features：`frontend/聊天訊息`
    - 需求原文依據：需求要求對局結束後，結果畫面的聊天紀錄保留回應數量但不能再回應；對應 `FR-004`。

5. `後端共通介面`
    - 端點類型：`後端端點`
    - 異動：修改既有
    - 主要介面：表情回應資源的掛載、表情回應錯誤碼、表情回應負載下的容量目標
    - 需求原文依據：需求要求表情回應在 1 秒內出現在雙方畫面，且 500 個房間同時回應時仍維持既有的延遲門檻；對應 `NFR-001` 與 `NFR-002`。

6. `表情回應 API 介面`
    - 端點類型：`後端端點`
    - 異動：新增
    - 主要介面：加上、改選與移除回應、回應者為房間目前成員的檢查、對局結束後拒絕、每人每則訊息至多一個回應、只接受三種表情、寫入後喚醒雙方
    - 需求原文依據：使用者描述要求「可以對訊息按 👍、❤️、😂」；對應 `FR-001`、`FR-002`、`FR-004` 與 `FR-005`。

7. `聊天訊息 API 介面`
    - 端點類型：`後端端點`
    - 異動：修改既有
    - 主要介面：訊息字數與總量上限、超過上限時的拒絕條件
    - 需求原文依據：使用者描述要求「訊息上限改成 500 字」；對應 `002/FR-002`。

8. `狀態同步 API 介面`
    - 端點類型：`後端端點`
    - 異動：修改既有
    - 主要介面：快照中每則訊息的回應數量與自己的選擇、回應變動時的增量、結果快照的唯讀聊天紀錄帶出回應數量
    - 需求原文依據：需求要求雙方看到相同的回應數量，斷線回來時補齊斷線期間的回應；對應 `FR-003`、`FR-004` 與 `NFR-001`。

9. `資料庫共通介面`
    - 端點類型：`資料庫端點`
    - 異動：修改既有
    - 主要介面：表情回應資料表的遷移、鎖定順序與表情回應的交易、表情回應隨房間在 24 小時內清除
    - 需求原文依據：需求要求表情回應與聊天紀錄同樣在 24 小時內刪除；對應 `NFR-003`。

10. `chat_messages 資料表介面`
    - 端點類型：`資料庫端點`
    - 異動：修改既有
    - 主要介面：訊息內容欄位的長度與檢查限制
    - 需求原文依據：使用者描述要求「訊息上限改成 500 字」；對應 `002/FR-002`。

11. `message_reactions 資料表介面`
    - 端點類型：`資料庫端點`
    - 異動：新增
    - 主要介面：回應所屬訊息與回應者、表情種類、每人每則訊息至多一列、回應時間
    - 需求原文依據：需求要求每位玩家對同一則訊息至多保留一個回應，改選時取代原本的回應；對應 `FR-001`、`FR-002` 與 `NFR-003`。

### 分析流程的安排

#### Wave 1

- 平行分析端點：
    - `後端端點`
- 安排理由：表情回應的 API、訊息上限與快照的修改，都能直接由使用者描述、`spec.md` 的既有需求異動與 truth 的現行契約推出，不需要等待其他端點的分析結果。
- 委派 skill：
    - `後端端點` → `api-plan`

#### Wave 2

- 平行分析端點：
    - `前端端點`
    - `資料庫端點`
- 安排理由：前端的回應按鈕與字數提示要引用 `後端端點` 修改後契約的 operationId、快照欄位與錯誤碼，表情回應資料表與訊息內容的限制取決於各 API 的讀寫操作，因此都排在 Wave 1 之後；兩者之間沒有依賴，可平行分析。
- 委派 skill：
    - `前端端點` → `ui-plan`
    - `資料庫端點` → `data-plan`
