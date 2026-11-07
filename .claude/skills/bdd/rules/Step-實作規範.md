# Rule 1 - 依 dsl.md 的實作語意逐項落地 [MUST]
- 每個 step definition 照 dsl.md 該句型的實作語意逐個 bullet 實作；與本檔其他 Rule 衝突時，以 dsl.md 為準。
- Given：`怎麼做` 用指定的操作佈置、`權威狀態落地` 不符就立即失敗、`回寫` 寫進 World 或 fixture、`不必查` 的項目不查。
- When：依 `使用 World`／`使用 fixture`、`Arrange 來源`、`API 操作`／`頁面操作`、`等待條件`、`回寫資料` 五項實作，只觸發一次。
- Then：`必查` 的呈現結果、權威狀態、再讀確認、不該發生都要有 assertion；`不必查` 的項目不查。
- 預設參數的值照 dsl.md 寫死在 step 或 driver 裡，不另外猜。

## Good Example
- Given 照 dsl.md 的 `怎麼做` 呼叫註冊 API，並檢查 `權威狀態落地`，和舊式「Given 一律走後門」不同，以 dsl.md 為準。

```ts
// dsl.md：怎麼做＝呼叫 POST /api/members；權威狀態落地＝members 恰新增 1 列；回寫＝會員身分表
Given('會員 {會員暱稱} 已註冊', async function (this: ShopWorld, nickname: string) {
  const member = await this.driver.registerMember(nickname)        // 怎麼做
  await this.driver.assertMemberRowCreated(nickname)                // 權威狀態落地
  this.members.set(nickname, member)                                // 回寫
})
```

## Bad Example
- 只查了呈現結果，漏掉 dsl.md 必查的權威狀態與再讀確認。

```ts
// dsl.md 必查：呈現結果、權威狀態（cart_items 恰 1 列）、再讀確認（getCart）、不該發生
Then('{會員暱稱} 的購物車有 {商品編號} 共 {數量} 件', async function (this: ShopWorld, m: string, sku: string, qty: number) {
  assert.equal(this.lastResponse.body.items[0].quantity, qty)
})
```

# Rule 2 - Step 只解析參數並委派 [MUST]
- Step definition 只做兩件事：取得已解析的參數、呼叫 driver / helper / page / service / API client；通常 1–3 行，Rule 1 的多項檢查也透過被呼叫的那一層完成。
- 業務邏輯、流程控制、資料組裝都放在被呼叫的那一層。

## Good Example
- 一行委派給 driver。

```ts
When('{玩家暱稱} 送出訊息 {訊息內容}', async function (this: ChatWorld, player: string, text: string) {
  this.lastResult = await this.driver.sendMessage(player, text)
})
```

## Bad Example
- 在 step 裡組 HTTP 請求、判斷狀態碼，step 變成實作的一部分。

```ts
When('{玩家暱稱} 送出訊息 {訊息內容}', async function (this: ChatWorld, player: string, text: string) {
  const res = await fetch(`${this.baseUrl}/api/rooms/${this.room}/chat-messages`, {
    method: 'POST',
    body: JSON.stringify({ content: text }),
  })
  this.lastResult = res.status === 201 ? await res.json() : { status: 'rejected' }
})
```

# Rule 3 - 透過 driver 或 fixture 介面存取被測系統 [SHOULD]
- cucumber-js：step 只依賴 driver 介面（port），in-memory、HTTP 等實作（adapter）由 World 依設定選用。
- playwright-bdd：step 只依賴 fixture 提供的 page object 或 helper，不在 step 裡直接 new 出被測系統的物件。
- 同一份 feature 與 step 不需修改，就能切換執行對象。

## Good Example
- World 依 worldParameters 選擇 adapter。

```ts
async init(): Promise<void> {
  this.driver =
    this.parameters.driver === 'http'
      ? new HttpChatDriver(this.parameters.baseUrl)
      : new InMemoryChatDriver()
}
```

## Bad Example
- Step 直接 new 出 domain service，之後要改成走 API 就得改每一個 step。

```ts
When('{玩家暱稱} 送出訊息 {訊息內容}', async function (this: ChatWorld, player: string, text: string) {
  this.lastResult = new ChatService(new MysqlRepo()).send(player, text)
})
```

# Rule 4 - 沿用該端既有的 step 分檔方式 [MUST]
- 新的 step 放進該端 step 目錄既有的分檔慣例（例如 `modules/<module>/*前置.ts`、`*操作.ts`、`*斷言.ts`），專案有結構檢查指令時一併通過。
- 沒有既有慣例時，一個主要領域概念一個 step 檔，不依 feature 或情境分檔；檔名與 step 文字都使用領域名詞。

## Good Example
- 專案已有 modules 分檔，新的聊天 step 照同一套放。

```
tests/bdd/modules/聊天/聊天前置.ts
tests/bdd/modules/聊天/聊天操作.ts
tests/bdd/modules/聊天/聊天斷言.ts
```

## Bad Example
- 無視既有慣例，依 feature 檔另開一套。

```
tests/bdd/靜音_feature_steps.ts
tests/bdd/發言頻率_feature_steps.ts
```

# Rule 5 - 只實作範疇內 slice 用到的句型 [MUST]
- 只為範疇內 slice 實際用到的 dsl.md 句型寫 step definition，不預先實作 dsl.md 裡其他句型。

## Good Example
- 範疇只有靜音.feature，只實作它用到的句型。

```ts
When('{玩家暱稱} 靜音對手', ...)
Then('{玩家暱稱} 已靜音對手', ...)
```

## Bad Example
- 範疇只有靜音，卻把 dsl.md 的發言頻率與紀錄保存句型一起寫好。

```ts
When('{玩家暱稱} 靜音對手', ...)
When('{玩家暱稱} 在 {秒數} 秒內連續送出 {則數} 則訊息', ...)
Then('房間 {房間代碼} 的聊天紀錄保留 {天數} 天', ...)
```

# Rule 6 - Step expression 與 dsl.md 句型一對一 [MUST]
- 每個 dsl.md 句型對應一個 step definition，使用 Cucumber Expression；同一個 expression 不混用 regex 語法。
- 不用可選文字或替代文字吸收 dsl.md 沒定義的寫法，也不為同一句型寫兩個 step。
- 括號在 Cucumber Expression 中表示可選文字，不是 capture group；字面上的 `(`、`{` 與 `/` 要用 `\` 跳脫。

## Good Example
- dsl.md 句型含半形括號與斜線，expression 加上跳脫，字面與句型完全相同；全形的「（」「／」不是語法字元，照原樣寫。

```ts
// dsl.md：{玩家暱稱} 看到傳送狀態(失敗)，未讀/已讀數為 {數量}
Then('{玩家暱稱} 看到傳送狀態\\(失敗)，未讀\\/已讀數為 {數量}', ...)
```

## Bad Example
- 用替代文字讓 expression 多吃 dsl.md 沒有的「傳送」說法，並混用 regex。

```ts
When('{玩家暱稱} 送出/傳送訊息 {訊息內容}', ...)
When(/^(\S+) 送出訊息 {訊息內容}$/, ...)
```

# Rule 7 - 領域名詞用自訂 Parameter Type [SHOULD]
- 暱稱、金額、房間代碼、拒絕原因這類領域名詞定義成 parameter type，轉換規則只寫一次，step 拿到的就是領域型別。
- 產 snippet 前已經明確的領域名詞先定義，snippet 會直接使用它。
- transformer 的參數個數等於 regexp 的 capture group 數；cucumber-js 中需要用 World（this）時不能寫成 arrow function；regexp 容易誤吃一般文字時設 `useForSnippets: false`。

## Good Example
- 引號字串集中在一處轉換。

```ts
defineParameterType({
  name: '玩家暱稱',
  regexp: /"([^"]+)"/,
  transformer: (name: string): PlayerName => name,
})
```

## Bad Example
- 每個 step 自己去掉引號，格式一改要改很多處。

```ts
When('{string} 靜音對手', function (this: ChatWorld, raw: string) {
  const name = raw.replace(/^"|"$/g, '')
})
```

# Rule 8 - Data Table 立刻轉成有型別的物件 [SHOULD]
- 進入 step 後第一件事就把表格轉成有型別的物件，後面的程式不再處理字串表格；欄位名稱以 dsl.md 的 Data Table 參數為準。
- cucumber-js 與 playwright-bdd 都沒有 DataTableType，用 `hashes()`（有表頭）、`rowsHash()`（兩欄 key-value）等方法取值，再交給轉換函式。

## Good Example
- 先轉成 MessageRow，再沿用暱稱與內容的轉換規則。

```ts
Given('房間 {房間代碼} 的聊天區已有以下訊息：', async function (this: ChatWorld, room: string, table: DataTable) {
  for (const row of table.hashes() as MessageRow[]) {
    await this.driver.seedMessage(room, row.發送者, row.內容)
  }
})
```

## Bad Example
- 用索引讀原始二維陣列，欄位順序一變就壞。

```ts
Given('房間 {房間代碼} 的聊天區已有以下訊息：', async function (this: ChatWorld, room: string, table: DataTable) {
  const raw = table.raw()
  for (let i = 1; i < raw.length; i++) await this.driver.seedMessage(room, raw[i][0], raw[i][1])
})
```

# Rule 9 - 失敗必須 throw [MUST]
- 步驟只有在 throw 時才算失敗；回傳 false 或 null 仍然算通過。
- Then 一律用 assertion：cucumber-js 用 Node.js 內建的 `node:assert/strict`，playwright-bdd 用 `@playwright/test` 的 `expect`。

## Good Example
- 不符合預期時 assertion 會 throw。

```ts
Then('{玩家暱稱} 的聊天紀錄共 {數量} 則', async function (this: ChatWorld, player: string, n: number) {
  assert.equal((await this.driver.historyOf(player)).length, n)
})
```

## Bad Example
- 回傳 false 不會讓步驟失敗，測試永遠是綠燈。

```ts
Then('{玩家暱稱} 的聊天紀錄共 {數量} 則', async function (this: ChatWorld, player: string, n: number) {
  return (await this.driver.historyOf(player)).length === n
})
```

# Rule 10 - 狀態只放在 World 或 fixture，情境之間不共享 [MUST]
- 同一情境內步驟之間要傳遞的值，cucumber-js 放在 World（`this`），playwright-bdd 放在 test 範圍的 fixture；每個情境都會拿到新的一份。
- 不用全域變數、模組層級的可變變數或 static 變數保存狀態。
- 外部資源（資料庫、瀏覽器 cookie、共用 server 的資料）在 Before hook 或 fixture 的 setup 清理或重設。
- 只把後續步驟真的需要讀的結果放進 World 或 fixture，不把它當雜物箱。

## Good Example
- 送出結果存在 World，供後面的 Then 讀取。

```ts
When('{玩家暱稱} 送出訊息 {訊息內容}', async function (this: ChatWorld, player: string, text: string) {
  this.lastResult = await this.driver.sendMessage(player, text)
})
```

## Bad Example
- 模組層級變數會把上一個情境的結果帶進下一個情境。

```ts
let lastResult: SendResult | undefined

When('{玩家暱稱} 送出訊息 {訊息內容}', async function (player: string, text: string) {
  lastResult = await sharedDriver.sendMessage(player, text)
})
```

# Rule 11 - cucumber-js 中使用 this 的函式不寫成 arrow function [MUST]
- cucumber-js 用 `this` 綁定 World，step、hook、parameter type transformer 要讀 World 時都用 `function`。
- 一定要用 arrow function 時，改用 `import { world } from '@cucumber/cucumber'`（v10.8.0 起）。
- playwright-bdd 以 fixture 參數傳入狀態，不用 `this`，不受本 Rule 限制。

## Good Example
- 用 function 並標註 this 的型別。

```ts
Given('{玩家暱稱} 已靜音對手', async function (this: ChatWorld, player: string) {
  await this.driver.mute(player)
})
```

## Bad Example
- arrow function 的 this 不是 World，執行時 this.driver 是 undefined。

```ts
Given('{玩家暱稱} 已靜音對手', async (player: string) => {
  await this.driver.mute(player)
})
```

# Rule 12 - 外部依賴用 stub，不用 mock [SHOULD]
- 盡量跑過完整的自有程式；第三方系統用 stub（in-memory 假實作或 HTTP 模擬器）取代，不在 step 裡設定呼叫次數之類的 mock 期望。
- stub 要有 contract test 確保它的行為和真實服務一致。
- 範疇以外的自有端點不是第三方系統，不用 stub 取代。

## Good Example
- 第三方內容審查服務用固定回應的 stub。

```ts
this.driver = new HttpChatDriver(baseUrl, { moderation: new StubModeration({ blocked: ['髒話'] }) })
```

## Bad Example
- 驗證內部呼叫次數，等於在測實作而不是行為。

```ts
Then('內容審查應被呼叫一次', function (this: ChatWorld) {
  expect(this.moderationMock.check).toHaveBeenCalledTimes(1)
})
```

# Rule 13 - 組合動作用 helper，不從 step 呼叫 step [MUST]
- 需要把多個動作收成一個步驟時，在程式語言層抽出 helper 再組合；cucumber-js 與 playwright-bdd 都不支援從 step 呼叫另一個 step。

## Good Example
- 一個 Given 呼叫兩個 driver 方法。

```ts
Given('{房主暱稱} 與 {對手暱稱} 都在房間 {房間代碼}，尚未開始遊戲', async function (this: ChatWorld, host: string, guest: string, room: string) {
  await this.driver.createRoom(host, room)
  await this.driver.joinRoom(guest, room)
})
```

## Bad Example
- 試圖在 step 裡觸發其他 Gherkin 步驟，框架沒有這個 API。

```ts
Given('{房主暱稱} 與 {對手暱稱} 都在房間 {房間代碼}，尚未開始遊戲', async function (this: ChatWorld, host: string, guest: string, room: string) {
  await this.runStep(`"${host}" 建立房間 "${room}"`)
  await this.runStep(`"${guest}" 加入房間 "${room}"`)
})
```
