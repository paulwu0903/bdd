# Rule 1 - Step 只解析參數並委派 [MUST]
- Step definition 只做兩件事：取得已解析的參數、呼叫 driver / helper / page / service / API client；通常 1–3 行。
- 業務邏輯、流程控制、資料組裝都放在被呼叫的那一層。

## Good Example
- 一行委派給 driver。

```ts
When('{actor} withdraws {money}', async function (this: BankWorld, actor: Actor, amount: Money) {
  this.lastResult = await this.driver.withdraw(actor.name, amount)
})
```

## Bad Example
- 在 step 裡組 HTTP 請求、判斷狀態碼，step 變成實作的一部分。

```ts
When('{actor} withdraws {money}', async function (this: BankWorld, actor: Actor, amount: Money) {
  const res = await fetch(`${this.parameters.baseUrl}/accounts/${actor.name}/withdrawals`, {
    method: 'POST',
    body: JSON.stringify({ amount }),
  })
  this.lastResult = res.status === 201 ? await res.json() : { status: 'rejected' }
})
```

# Rule 2 - Given、When、Then 各走各的路徑 [MUST]
- Given：用最快的方式直接佈置狀態（seed、factory、測試用端點），不經過被測介面。
- When：透過被測介面觸發（domain API、HTTP、UI）。
- Then：讀取可觀察的結果並以 assertion 比對預期值。

| 關鍵字 | 路徑 | 例子 |
|---|---|---|
| Given | 後門佈置 | `driver.openAccount()`、`driver.seedWithdrawnToday()` |
| When | 被測介面 | `driver.withdraw()` |
| Then | 可觀察輸出 + assertion | `assert.equal(await driver.balanceOf(...), expected)` |

## Good Example
- Given 直接寫入當日提領紀錄，不重演一次提領流程。

```ts
Given('{actor} has already withdrawn {money} today', async function (this: BankWorld, actor: Actor, amount: Money) {
  await this.driver.seedWithdrawnToday(actor.name, amount)
})
```

## Bad Example
- Given 透過被測介面重演提領，提領功能壞掉時，所有需要這個前置條件的情境都會跟著失敗。

```ts
Given('{actor} has already withdrawn {money} today', async function (this: BankWorld, actor: Actor, amount: Money) {
  await this.driver.withdraw(actor.name, amount)
})
```

# Rule 3 - 透過 driver 介面存取被測系統 [SHOULD]
- Step 只依賴 driver 介面（port）；in-memory、HTTP、UI 各有一個實作（adapter），由 World 依設定選用。
- 同一份 feature 與 step 不需修改，就能切換執行對象。

## Good Example
- World 依 worldParameters 選擇 adapter。

```ts
async init(): Promise<void> {
  this.driver =
    this.parameters.driver === 'http'
      ? new HttpBankDriver(this.parameters.baseUrl)
      : new InMemoryBankDriver()
}
```

## Bad Example
- Step 直接 new 出 domain service，之後要改成走 API 就得改每一個 step。

```ts
When('{actor} withdraws {money}', async function (this: BankWorld, actor: Actor, amount: Money) {
  this.lastResult = new Bank(new PostgresRepo()).withdraw(actor.name, amount)
})
```

# Rule 4 - Step 檔依領域概念分檔 [MUST]
- 一個主要領域概念一個 step 檔（account、withdrawal、authentication），不依 feature 或情境分檔。
- 檔名與 step 文字都使用領域名詞。

## Good Example
- 依領域概念切分，不同 feature 可以共用。

```
features/step_definitions/
  account.steps.ts
  withdrawal.steps.ts
  authentication.steps.ts
```

## Bad Example
- 依 feature 切分，每個 feature 各寫一套相似的 step。

```
features/step_definitions/
  withdraw_cash_feature_steps.ts
  transfer_money_feature_steps.ts
  edit_profile_feature_steps.ts
```

# Rule 5 - 只實作 feature 中出現的步驟 [MUST]
- 只為目前 feature 實際用到的步驟寫 step definition，不預先寫「之後可能用得到」的 step。

## Good Example
- 情境用到 withdraws，只實作 withdraws。

```ts
When('{actor} withdraws {money}', ...)
```

## Bad Example
- 情境只有提領，卻預先寫好存款與轉帳。

```ts
When('{actor} withdraws {money}', ...)
When('{actor} deposits {money}', ...)
When('{actor} transfers {money} to {actor}', ...)
```

# Rule 6 - 使用 Cucumber Expression [SHOULD]
- 優先使用 Cucumber Expression；同一個 expression 不混用 regex 語法。
- 用可選文字 `cucumber(s)` 與替代文字 `belly/stomach` 吸收單複數與同義詞，不為文法差異多寫一個 step。
- 括號在 Cucumber Expression 中表示可選文字，不是 capture group；字面上的 `(` 與 `{` 要用 `\` 跳脫。

## Good Example
- 一個 expression 同時涵蓋單複數與同義詞。

```ts
When('{actor} withdraw(s) {money} from the ATM/counter', ...)
```

## Bad Example
- 為單複數各寫一個 step，且混用 regex 語法。

```ts
When('{actor} withdraws {money} from the ATM', ...)
When('{actor} withdraw {money} from the ATM', ...)
When(/^(\w+) withdraws {money} from the counter$/, ...)
```

# Rule 7 - 領域名詞用自訂 Parameter Type [SHOULD]
- 金額、角色、狀態這類領域名詞定義成 parameter type，轉換規則只寫一次，step 拿到的就是領域型別。
- 產 snippet 前已經明確的領域名詞先定義，snippet 會直接使用它；其餘等重構時再抽。
- transformer 的參數個數等於 regexp 的 capture group 數；需要用 World（this）時不能寫成 arrow function；regexp 容易誤吃一般文字時設 `useForSnippets: false`。

## Good Example
- 金額格式集中在一處轉換。

```ts
defineParameterType({
  name: 'money',
  regexp: /NT\$(\d+)/,
  transformer: (amount: string): Money => Number(amount),
})
```

## Bad Example
- 每個 step 自己解析金額字串，格式一改要改很多處。

```ts
When('{actor} withdraws NT${int}', ...)
Then('{actor} should receive {string}', function (this: BankWorld, _a: Actor, raw: string) {
  const expected = Number(raw.replace('NT$', ''))
})
```

# Rule 8 - Data Table 立刻轉成有型別的物件 [SHOULD]
- 進入 step 後第一件事就把表格轉成有型別的物件，後面的程式不再處理字串表格。
- cucumber-js 沒有 DataTableType，用 `hashes()`（有表頭）、`rowsHash()`（兩欄 key-value）等方法取值，再交給轉換函式；Cucumber-JVM 才有 `@DataTableType` 可以自動轉換。

## Good Example
- 先轉成 AccountRow，再沿用金額的轉換規則。

```ts
Given('the following accounts exist:', async function (this: BankWorld, table: DataTable) {
  for (const row of table.hashes() as AccountRow[]) {
    await this.driver.openAccount(row.owner, parseMoney(row.balance))
  }
})
```

## Bad Example
- 用索引讀原始二維陣列，欄位順序一變就壞，而且沒有轉換金額。

```ts
Given('the following accounts exist:', async function (this: BankWorld, table: DataTable) {
  const raw = table.raw()
  for (let i = 1; i < raw.length; i++) {
    await this.driver.openAccount(raw[i][0], raw[i][1] as any)
  }
})
```

# Rule 9 - 失敗必須 throw [MUST]
- 步驟只有在 throw 時才算失敗；回傳 false 或 null 仍然算通過。
- Then 一律用 assertion（cucumber-js 用 Node.js 內建的 `node:assert/strict`）。

## Good Example
- 不符合預期時 assertion 會 throw。

```ts
Then("{actor}'s balance should be {money}", async function (this: BankWorld, actor: Actor, expected: Money) {
  assert.equal(await this.driver.balanceOf(actor.name), expected)
})
```

## Bad Example
- 回傳 false 不會讓步驟失敗，測試永遠是綠燈。

```ts
Then("{actor}'s balance should be {money}", async function (this: BankWorld, actor: Actor, expected: Money) {
  return (await this.driver.balanceOf(actor.name)) === expected
})
```

# Rule 10 - 狀態只放在 World，情境之間不共享 [MUST]
- 同一情境內步驟之間要傳遞的值放在 World（`this`）；每個情境都會拿到新的 World。
- 不用全域變數、模組層級的可變變數或 static 變數保存狀態。
- 外部資源（資料庫、瀏覽器 cookie、共用 server 的資料）在 Before hook 清理或重設。
- 只把後續步驟真的需要讀的結果放進 World，不把 World 當雜物箱。

## Good Example
- 提領結果存在 World，供後面的 Then 讀取。

```ts
When('{actor} withdraws {money}', async function (this: BankWorld, actor: Actor, amount: Money) {
  this.lastResult = await this.driver.withdraw(actor.name, amount)
})
```

## Bad Example
- 模組層級變數會把上一個情境的結果帶進下一個情境。

```ts
let lastResult: WithdrawResult | undefined

When('{actor} withdraws {money}', async function (actor: Actor, amount: Money) {
  lastResult = await sharedDriver.withdraw(actor.name, amount)
})
```

# Rule 11 - 使用 this 的函式不寫成 arrow function [MUST]
- cucumber-js 用 `this` 綁定 World，step、hook、parameter type transformer 要讀 World 時都用 `function`。
- 一定要用 arrow function 時，改用 `import { world } from '@cucumber/cucumber'`（v10.8.0 起）。

## Good Example
- 用 function 並標註 this 的型別。

```ts
Given('{actor} has a balance of {money}', async function (this: BankWorld, actor: Actor, balance: Money) {
  await this.driver.openAccount(actor.name, balance)
})
```

## Bad Example
- arrow function 的 this 不是 World，執行時 this.driver 是 undefined。

```ts
Given('{actor} has a balance of {money}', async (actor: Actor, balance: Money) => {
  await this.driver.openAccount(actor.name, balance)
})
```

# Rule 12 - 外部依賴用 stub，不用 mock [SHOULD]
- 盡量跑過完整的自有程式；第三方系統用 stub（in-memory 假實作或 HTTP 模擬器）取代，不在 step 裡設定呼叫次數之類的 mock 期望。
- stub 要有 contract test 確保它的行為和真實服務一致。

## Good Example
- 匯率服務用固定回應的 stub。

```ts
this.driver = new InMemoryBankDriver({ fxRates: new StubFxRates({ USD: 32.1 }) })
```

## Bad Example
- 驗證內部呼叫次數，等於在測實作而不是行為。

```ts
Then('the exchange rate should be fetched once', function (this: BankWorld) {
  expect(this.fxMock.getRate).toHaveBeenCalledTimes(1)
})
```

# Rule 13 - 相似步驟合併成參數化的 step [SHOULD]
- 行為相同、只有值不同的步驟，重構時合併成一個帶參數的 step。

## Good Example
- 三個開頁面的步驟合併成一個。

```ts
Given('Alice goes to the {string} page', async function (this: ShopWorld, page: string) {
  await this.driver.openPage(page)
})
```

## Bad Example
- 三個 step 做的是同一件事。

```ts
Given('Alice goes to the home page', ...)
Given('Alice checks the about page', ...)
Given('Alice gets the contact details', ...)
```

# Rule 14 - 組合動作用 helper，不從 step 呼叫 step [MUST]
- 需要把多個動作收成一個高階步驟時，在程式語言層抽出 helper 再組合；cucumber-js 與 Cucumber-JVM 刻意不支援從 step 呼叫另一個 step。

## Good Example
- 高階步驟呼叫兩個 helper。

```ts
Given('{actor} is a premium member', async function (this: BankWorld, actor: Actor) {
  await this.driver.openAccount(actor.name, 0)
  await this.driver.upgradeToPremium(actor.name)
})
```

## Bad Example
- 試圖在 step 裡觸發其他 Gherkin 步驟，cucumber-js 沒有這個 API。

```ts
Given('{actor} is a premium member', async function (this: BankWorld, actor: Actor) {
  await this.runStep(`${actor.name} has a balance of NT$0`)
  await this.runStep(`${actor.name} upgrades to premium`)
})
```
