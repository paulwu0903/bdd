# Rule 1 - 依症狀把紅燈歸入一個類別 [MUST]
- 每次紅燈先依下表判定類別，再到該類別的修正位置動手；不在判定前改程式。

| 類別 | 典型症狀 | 修正位置 |
|---|---|---|
| 比對 | 步驟顯示 undefined 或 ambiguous | Cucumber Expression 或 parameter type |
| 資料 | Given 佈置不完整、依賴環境既有資料、找不到應存在的實體 | Given step 與 test data builder |
| 定位 | locator、endpoint、payload 格式錯誤，連線或解析失敗 | driver / page object / API client |
| 斷言 | Then 的 assertion 失敗 | 依 Rule 2 判斷是測試錯還是產品錯 |
| 狀態清理 | 單獨跑會過、一起跑會失敗，或反過來 | Before / After hook、World |
| 產品未實作 | 呼叫的產品函式、端點不存在或回傳尚未實作 | 內層產品碼（依 Rule 3） |

## Good Example
- 先從錯誤訊息判定類別，再到對應位置修正。

```
紅燈：Error: Cannot find module '../../src/bank.js'
類別：產品未實作
修正：進內層以單元測試 TDD 建立 Bank
```

## Bad Example
- 沒有判定類別就改 Then，把一個 404 當成斷言問題處理。

```
紅燈：AssertionError: expected 'approved', got undefined（driver 打到 404）
修正：把 Then 改成 assert.ok(true)
```

# Rule 2 - 斷言失敗先判斷是測試錯還是產品錯 [MUST]
- 預期值與已 review 的情境一致、實際值錯：產品錯，修產品碼。
- 預期值本身與已 review 的情境不一致（step 寫錯、轉換錯）：測試錯，修 step 或 parameter type。
- 不為了讓測試變綠去改 Then 或 .feature 的預期值來遷就產品。

## Good Example
- 情境寫 NT$700，step 也斷言 700，實際是 1000，判定產品還沒扣款。

```
情境：Then Alice's balance should be NT$700
紅燈：expected 700, actual 1000
判定：產品錯（提領沒有扣款）→ 修產品碼
```

## Bad Example
- 為了讓測試通過，把 .feature 的預期改成產品目前的錯誤行為。

```
情境：Then Alice's balance should be NT$700
紅燈：expected 700, actual 1000
修正：把 .feature 改成 Then Alice's balance should be NT$1000
```

# Rule 3 - 產品缺口只能在內層用 TDD 補 [MUST]
- 判定為產品未實作或產品錯時，在產品碼那一層先寫一個失敗的單元測試，再寫最少的產品碼讓它通過。
- 不在 step、driver 或 stub 裡寫假邏輯讓情境變綠。

## Good Example
- 先寫單元測試描述扣款，再實作。

```ts
test('withdraw deducts the amount from the balance', () => {
  const bank = new Bank(new InMemoryAccountRepository([{ owner: 'Alice', balance: 1000, withdrawnToday: 0 }]))
  bank.withdraw('Alice', 300)
  assert.equal(bank.balanceOf('Alice'), 700)
})
```

## Bad Example
- 在 in-memory driver 裡自己算餘額，情境變綠了，但產品碼根本沒有扣款。

```ts
async withdraw(owner: string, amount: number) {
  this.balances[owner] -= amount
  return { status: 'approved', dispensed: amount }
}
```
