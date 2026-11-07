# Rule 1 - 描述行為，不描述實作 [MUST]
- 每一行寫「做什麼」，不寫「怎麼做」；判準：實作方式改變時，這句話需要跟著改，就要改寫。
- 不出現 UI 或技術詞彙：click、press、button、field、page、URL、API endpoint、資料表名稱。
- 先寫行為，不從 UI 操作回推 Gherkin。

## Good Example
- 只說明意圖，登入方式改成指紋時不用改。

```gherkin
Scenario: Free subscribers see only the free articles
  Given Free Frieda has a free subscription
  When Free Frieda logs in with her valid credentials
  Then she sees a Free article
```

## Bad Example
- 逐步描述表單操作，綁死目前的 UI。

```gherkin
Scenario: Free subscribers see only the free articles
  When I type "freeFrieda@example.com" in the email field
  And I type "validPassword123" in the password field
  And I press the "Submit" button
  Then I see "FreeArticle1" on the home page
```

# Rule 2 - Given 只陳述既有狀態 [MUST]
- Given 描述情境開始前已經成立的狀態（過去式或狀態陳述），不描述使用者互動。

## Good Example
- 陳述帳戶已有的餘額。

```gherkin
Given Alice has a balance of NT$1000
```

## Bad Example
- Given 裡在描述操作流程。

```gherkin
Given Alice opens the deposit page and deposits NT$1000
```

# Rule 3 - 一個情境只有一個 When [SHOULD]
- When 描述觸發行為的單一事件；需要兩個事件時，通常是兩個情境，或前一個事件應改寫成 Given 的狀態。

## Good Example
- 先前的提領寫成狀態，When 只有一個事件。

```gherkin
Given Carol has already withdrawn NT$15000 today
When Carol withdraws NT$5001
Then the withdrawal should be rejected
```

## Bad Example
- 兩個 When 串成流程，失敗時無法判斷是哪個事件的行為出錯。

```gherkin
When Carol withdraws NT$15000
And Carol withdraws NT$5001
Then the withdrawal should be rejected
```

# Rule 4 - Then 只驗證可觀察的輸出 [MUST]
- Then 寫使用者或外部系統觀察得到的結果（回應、訊息、畫面上的資訊、報表、送出的通知）。
- 不驗證資料庫紀錄、內部欄位或呼叫次數。

## Good Example
- 驗證使用者看得到的結果。

```gherkin
Then Bob should be told "Insufficient funds"
And Bob's balance should be NT$100
```

## Bad Example
- 驗證資料表內容，屬於內部實作。

```gherkin
Then the withdrawals table should have 0 rows for Bob
```

# Rule 5 - Given 與 Then 使用不同句型 [MUST]
- 比對 step definition 時不看關鍵字，Given 與 Then 不能是同一句話。
- Given 用狀態陳述（has、is），Then 用 should。

## Good Example
- 兩句文字不同，各自對到不同的 step definition。

```gherkin
Given Alice has a balance of NT$430
Then Alice's balance should be NT$430
```

## Bad Example
- 同一句話同時當前置條件與預期結果，會被視為同一個步驟。

```gherkin
Given there is money in Alice's account
Then there is money in Alice's account
```

# Rule 6 - 不寫連接詞步驟 [SHOULD]
- 一個步驟只表達一件事；兩件事用 And 分成兩行。

## Good Example
- 拆成兩個可以各自重用的步驟。

```gherkin
Given Alice has a premium membership
And Alice has a balance of NT$1000
```

## Bad Example
- 用 and 把兩件事塞進同一步，這個步驟幾乎無法被其他情境重用。

```gherkin
Given Alice has a premium membership and a balance of NT$1000
```

# Rule 7 - 一個情境只示範一條業務規則 [MUST]
- 每個 Example 只說明一條規則；同一條規則的多個例子放在同一個 Rule 底下。
- 判準：改動另一條規則時，這個情境不應該跟著失敗。

## Good Example
- 餘額規則與單日上限規則各自分組，互不影響。

```gherkin
Rule: A withdrawal cannot exceed the available balance
  Example: Withdrawal over balance is rejected
    ...

Rule: The daily withdrawal limit is NT$20000
  Example: Withdrawal over the daily limit is rejected
    ...
```

## Bad Example
- 一個情境同時驗證餘額、單日上限與手續費，任何一條規則改變都會讓它失敗。

```gherkin
Example: Withdrawal rules
  Given Alice has a balance of NT$30000
  When Alice withdraws NT$25000
  Then the withdrawal should be rejected
  And Alice should be charged a NT$15 fee
```

# Rule 8 - 使用能揭露邊界的具體資料 [SHOULD]
- 用具體值（金額、日期、數量）取代模糊描述，並優先挑選貼近邊界的值。

## Good Example
- 剛好等於上限、剛好超過上限。

```gherkin
| already  | amount   | outcome  |
| NT$0     | NT$20000 | approved |
| NT$15000 | NT$5001  | rejected |
```

## Bad Example
- 「很多錢」無法判斷邊界在哪裡。

```gherkin
When Carol withdraws a large amount
Then the withdrawal should be rejected
```

# Rule 9 - 情境自己建立需要的資料 [MUST]
- 情境需要的資料都由自己的 Given（或 Background）建立，不假設環境裡已經有某筆資料。

## Good Example
- 由 Given 建立客戶與餘額。

```gherkin
Given Alice has a balance of NT$1000
```

## Bad Example
- 假設正式環境中一定存在客戶 1234。

```gherkin
Given customer 1234 logs in
```

# Rule 10 - 只保留示範規則所需的細節 [SHOULD]
- 不影響這條規則結果的資訊（日期、地址、無關欄位）不寫進情境。

## Good Example
- 只留下與餘額規則有關的資訊。

```gherkin
Given Bob has a balance of NT$100
When Bob withdraws NT$500
Then Bob should be told "Insufficient funds"
```

## Bad Example
- 開戶日期、分行、帳號類型都與這條規則無關。

```gherkin
Given Bob opened a savings account at the Taipei branch on 2024-03-01
And Bob has a balance of NT$100
When Bob withdraws NT$500 on 2026-11-01 at 10:30
Then Bob should be told "Insufficient funds"
```

# Rule 11 - 每個情境 3–5 個步驟 [SHOULD]
- 超過 5 步時，把細節收進更高階的步驟，或拆成多個情境。

## Good Example
- 4 個步驟完整表達一個例子。

```gherkin
Given Alice has a balance of NT$1000
When Alice withdraws NT$300
Then Alice should receive NT$300
And Alice's balance should be NT$700
```

## Bad Example
- 前置細節攤開成多行，讀者抓不到重點。

```gherkin
Given Alice is a customer
And Alice has an account
And the account is active
And the account currency is TWD
And Alice has a balance of NT$1000
And Alice has a debit card
When Alice withdraws NT$300
Then Alice should receive NT$300
```

# Rule 12 - Background 只放讀者需要知道的共同前置條件 [SHOULD]
- 只放 Given，不超過 4 行，用有畫面感的名字（Free Frieda），不用 User A。
- 每個 Feature 或 Rule 只能有一個 Background；不同情境需要不同前置條件時，拆成多個 Rule 或 Feature。
- 讀者不需要知道的技術前置作業（啟動瀏覽器、清資料）交給 hook，不寫進 Background。

## Good Example
- 簡短、只有業務相關的前置條件。

```gherkin
Background:
  Given Greg is a global administrator
  And Dr. Bill owns the blog "Expensive Therapy"
```

## Bad Example
- 混入技術前置作業，且用沒有意義的名字。

```gherkin
Background:
  Given the browser is launched
  And the database is cleaned
  And User A exists
  And User B exists
  And Site 1 exists
```

# Rule 13 - Scenario Outline 只用於同一條規則的資料變化 [SHOULD]
- 步驟相同、只有資料不同時才用 Outline；每一列代表不同規則時，拆成獨立的 Example。
- Examples 表格的每個欄位都要在步驟中被使用。

## Good Example
- 同一條上限規則，只換資料。

```gherkin
Scenario Outline: Daily limit is NT$20000
  Given Carol has already withdrawn <already> today
  When Carol withdraws <amount>
  Then the withdrawal should be <outcome>

  Examples:
    | already  | amount   | outcome  |
    | NT$0     | NT$20000 | approved |
    | NT$15000 | NT$5001  | rejected |
```

## Bad Example
- 每一列其實是不同的規則，還有沒被使用的欄位 note。

```gherkin
Scenario Outline: Withdrawals
  When <owner> withdraws <amount>
  Then the result should be <result>

  Examples:
    | owner | amount   | result             | note                |
    | Alice | NT$300   | approved           | normal              |
    | Bob   | NT$500   | Insufficient funds | balance rule        |
    | Carol | NT$25000 | rejected           | daily limit rule    |
```

# Rule 14 - 結構化資料用 Data Table，大段文字用 Doc String [MAY]
- 多筆實體或 key-value 設定用 Data Table；JSON payload、Email 內文等大段文字用 Doc String。

## Good Example
- 多筆帳戶用表格一次給。

```gherkin
Given the following accounts exist:
  | owner | balance |
  | Alice | NT$1000 |
  | Bob   | NT$100  |
```

## Bad Example
- 把多筆資料硬塞進一行字串。

```gherkin
Given accounts "Alice:1000,Bob:100" exist
```

# Rule 15 - Tag 只使用約定的字彙 [SHOULD]
- 只使用專案約定的 tag（例如 @wip、@smoke、@ui、@api、對應 issue 編號的 tag）。
- Tag 可以加在 Feature、Rule、Scenario、Scenario Outline、Examples 上，不能加在 Background 或步驟上。
- 所有情境都有的 tag 加在 Feature 上，不在每個情境重複。

## Good Example
- 共同的 tag 放在 Feature，個別的 tag 放在情境上。

```gherkin
@wip
Feature: Withdraw cash

  @boundary
  Scenario Outline: Daily limit is NT$20000
```

## Bad Example
- 每個情境重複同一個 tag，還出現沒有約定的 tag。

```gherkin
Feature: Withdraw cash

  @wip @todo-maybe
  Example: Withdrawal within balance succeeds

  @wip
  Example: Withdrawal over balance is rejected
```

# Rule 16 - 使用業務語言，不用多義詞 [SHOULD]
- 名詞與動詞取自領域專家實際使用的用語；user、account、address、date 這類多義詞要換成具體角色或概念。
- 全檔使用領域專家使用的自然語言；非英文時第一行加上 `# language: <code>`（例如 `# language: zh-TW`）。

## Good Example
- 用領域角色取代多義的 user。

```gherkin
Given Alice is an account holder with a balance of NT$1000
```

## Bad Example
- user 可能指客戶、行員或管理員，讀者無法判斷。

```gherkin
Given the user has NT$1000
```
