# 前端畫面規格：{{feature name}}

## 範疇

- 端點類型：`前端端點`
- 本次涵蓋的前端介面：
    - `{{frontend interface name}}`
- 不在範疇：{{out of scope}}
- 上游契約：
    - HTTP API：`analysis/openapi.yaml`
    - 即時事件：`analysis/asyncapi.yaml`
- 雛形入口：`prototype/index.html`

## 視覺風格

- 風格：{{visual style}}
- 色彩：

| Token | 色碼 | 用途 |
|---|---|---|
| `{{color token}}` | `{{color hex}}` | {{color usage}} |

- 字型：{{fonts}}
- 元件：
    - {{component style}}

## {{common interface name}}

- {{common rule topic}}：{{common rule}}

## 畫面

### {{screen name}}

- 對應介面：`{{frontend interface name}}`
- 雛形：`prototype/{{page file}}`
- 對應需求：{{requirement ids}}
- 四態：{{four states}}
- 版面：
    - {{layout region}}：{{region content}}
- {{field validation title}}：

| 欄位 | 規則 | 錯誤文案 |
|---|---|---|
| {{field}} | {{field rule}} | {{error copy}} |

- 互動與呼叫：

| 操作 | 呼叫 | 成功時 | 失敗時 |
|---|---|---|---|
| {{user action}} | {{operation id}} | {{on success}} | {{on failure}} |

- 即時連線送出：

| 操作 | 送出訊息 | 受理時 | 拒絕時 |
|---|---|---|---|
| {{user action}} | `{{message name}}` | {{on accepted}} | {{on rejected}} |

| 錯誤碼 | 畫面反應 |
|---|---|
| `{{error code}}` | {{error reaction}} |

- 即時事件：

| 事件 | 畫面反應 |
|---|---|
| `{{message name}}` | {{event reaction}} |

- {{screen rule topic}}：{{screen rule}}

## 雛形

- 檔案：
    - `prototype/{{page file}}`：{{screen name}}
- 只呈現畫面與直接互動，不串接後端、不模擬 API
- 假資料：{{fake data}}
- 互動：
    - {{interaction}}
- 網址參數：

| 頁面 | 參數 | 呈現狀態 |
|---|---|---|
| `{{page file}}` | `?state={{state name}}` | {{state description}} |

## 驗證

- 雙擊 `prototype/index.html` 可直接開啟，不需要伺服器
- 依「互動與呼叫」逐列操作，畫面反應與表格一致
- 依「網址參數」逐一開啟，每個狀態都能看到
- {{verification item}}
