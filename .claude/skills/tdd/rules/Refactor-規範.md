# Rule 1 - repo 標準優先於 code smell [MUST]
- repo 文件化的寫碼標準一律優先；標準明確允許、而下列 smell 會標記的寫法，不當作 smell 處理。
- 工具（linter、formatter、型別檢查）已強制的項目不在 refactor 時另行處理。

## Good Example
- `CONTRIBUTING.md` 明訂 handler 一律透過 `Router` 轉發，雖然像 Middle Man，仍依 repo 標準保留。

```
CONTRIBUTING.md：所有 HTTP handler 必須經由 Router.dispatch() 轉發，不直接呼叫 service。
判斷：Router 看似 Middle Man → repo 標準允許 → 不動
```

## Bad Example
- 無視 repo 標準，把文件規定必須保留的 Router 當成 Middle Man 拆掉；又手動調整 formatter 本來就會處理的縮排。

```
CONTRIBUTING.md：所有 HTTP handler 必須經由 Router.dispatch() 轉發，不直接呼叫 service。
refactor：移除 Router，handler 直接呼叫 service；逐行調整縮排
```

# Rule 2 - smell 是待判斷的 heuristic [MUST]
- 每個 smell 都只是「可能有問題」的標記（例如「可能是 Feature Envy」），不是硬性違規。
- 對照下列 smell 判斷整理後是否確實更清楚；不是每個符合描述的地方都必須改。

## Good Example
- 先標記為「可能」，判斷後只改確實受益的那處。

```
可能是 Data Clumps：(lat, lng) 在 6 個函式中一起傳遞 → 包成 Coordinate，確有改善
可能是 Data Clumps：(width, height) 只在 1 個函式中出現 → 不動
```

## Bad Example
- 把 smell 當硬性違規，只要出現兩個參數一起傳就全部包成型別。

```
違規：(width, height) 一起傳遞 → 強制包成 Size
違規：(start, end) 一起傳遞 → 強制包成 Range
```

# Rule 3 - Mysterious Name [SHOULD]
- 函式、變數或型別的名稱說不出它做什麼或裝什麼時，改名。
- 想不出誠實的名稱，代表設計本身不清楚。

## Good Example
- 名稱直接說出內容。

```typescript
function calculateDiscount(cart: Cart): Money { /* ... */ }
const eligibleItems = cart.items.filter(isDiscountable);
```

## Bad Example
- `process`、`data2` 看不出用途。

```typescript
function process(c: Cart): Money { /* ... */ }
const data2 = c.items.filter(check);
```

# Rule 4 - Duplicated Code [SHOULD]
- 同一種邏輯形狀出現在多處時，抽出共用的形狀，各處改為呼叫它。

## Good Example
- 兩處共用同一個抽出的函式。

```typescript
const subtotal = (items: Item[]) => items.reduce((sum, i) => sum + i.price * i.qty, 0);

function cartTotal(cart: Cart) { return subtotal(cart.items); }
function invoiceTotal(invoice: Invoice) { return subtotal(invoice.lines); }
```

## Bad Example
- 同一段加總邏輯複製在兩處，改一處就得記得改另一處。

```typescript
function cartTotal(cart: Cart) {
  return cart.items.reduce((sum, i) => sum + i.price * i.qty, 0);
}
function invoiceTotal(invoice: Invoice) {
  return invoice.lines.reduce((sum, i) => sum + i.price * i.qty, 0);
}
```

# Rule 5 - Feature Envy [SHOULD]
- 方法存取另一個物件的資料多於自己的資料時，把方法搬到它羨慕的資料所在處。

## Good Example
- 運費計算放在擁有地址資料的 `Address` 上。

```typescript
class Address {
  shippingFee(): Money { return this.country === "TW" ? 60 : 300; }
}
```

## Bad Example
- `Order` 的方法只在讀 `Address` 的欄位。

```typescript
class Order {
  shippingFee(): Money { return this.address.country === "TW" ? 60 : 300; }
}
```

# Rule 6 - Data Clumps [SHOULD]
- 同一組欄位或參數總是一起出現時（一個想誕生的型別），把它們包成一個型別再傳遞。

## Good Example
- 一起出現的 `amount` 與 `currency` 包成 `Money`。

```typescript
type Money = { amount: number; currency: string };
function charge(customerId: string, price: Money) { /* ... */ }
function refund(customerId: string, price: Money) { /* ... */ }
```

## Bad Example
- 同一對參數在每個函式中重複出現。

```typescript
function charge(customerId: string, amount: number, currency: string) { /* ... */ }
function refund(customerId: string, amount: number, currency: string) { /* ... */ }
```

# Rule 7 - Primitive Obsession [SHOULD]
- 用 primitive 或字串代表一個值得擁有自己型別的領域概念時，給該概念一個小型別。

## Good Example
- Email 有自己的型別，建立時就驗證。

```typescript
class Email {
  constructor(readonly value: string) {
    if (!value.includes("@")) throw new Error("invalid email");
  }
}
function sendWelcome(to: Email) { /* ... */ }
```

## Bad Example
- Email 只是 `string`，任何字串都能傳進來。

```typescript
function sendWelcome(to: string) { /* ... */ }
```

# Rule 8 - Repeated Switches [SHOULD]
- 針對同一型別的同一組 `switch` 或 `if` 串在多處重複出現時，改用多型，或讓各處共用同一個 map。

## Good Example
- 兩處共用同一個 map。

```typescript
const PLAN = {
  free: { price: 0, seats: 1 },
  pro: { price: 20, seats: 5 },
} as const;

const priceOf = (p: keyof typeof PLAN) => PLAN[p].price;
const seatsOf = (p: keyof typeof PLAN) => PLAN[p].seats;
```

## Bad Example
- 同一個 `switch (plan)` 在兩個函式中重複，新增方案時兩處都要改。

```typescript
function priceOf(plan: string) {
  switch (plan) { case "free": return 0; case "pro": return 20; }
}
function seatsOf(plan: string) {
  switch (plan) { case "free": return 1; case "pro": return 5; }
}
```

# Rule 9 - Shotgun Surgery [SHOULD]
- 一個邏輯上的改動卻要在多個檔案零散修改時，把會一起改變的東西集中到同一個 module。

## Good Example
- 稅率相關的邏輯集中在 `tax.ts`，調整稅率只改一個檔案。

```
src/tax.ts        ← TAX_RATE、applyTax()、formatTaxLine()
src/cart.ts       ← 呼叫 applyTax()
src/invoice.ts    ← 呼叫 applyTax()、formatTaxLine()
```

## Bad Example
- 稅率 0.05 散落三個檔案，調整一次要改三處。

```
src/cart.ts       ← total * 1.05
src/invoice.ts    ← total * 0.05 列為稅額
src/receipt.ts    ← "含稅 5%"
```

# Rule 10 - Divergent Change [SHOULD]
- 同一個檔案或 module 會因為多個互不相關的理由被修改時，拆開，讓每個 module 只因一個理由改變。

## Good Example
- 計價與匯出各自一個 module，改 CSV 格式不會碰到計價。

```
src/pricing.ts    ← 折扣、稅金
src/export.ts     ← CSV、PDF 匯出
```

## Bad Example
- 改折扣規則和改 CSV 欄位都得修改同一個 `order.ts`。

```
src/order.ts      ← 折扣、稅金、CSV 匯出、PDF 匯出、寄信
```

# Rule 11 - Speculative Generality [SHOULD]
- spec 沒有要求的抽象、參數或 hook 一律刪除，inline 回去，等真正需要時再加。

## Good Example
- 只有一種折扣，就只寫一個函式。

```typescript
function calculateDiscount(cart: Cart): Money {
  return cart.total >= 1000 ? 100 : 0;
}
```

## Bad Example
- spec 只要求滿千折百，卻預先加了策略介面、註冊表與未使用的 hook。

```typescript
interface DiscountStrategy { apply(cart: Cart): Money; }
class DiscountRegistry {
  register(name: string, s: DiscountStrategy, onApply?: () => void) { /* ... */ }
}
```

# Rule 12 - Message Chains [SHOULD]
- 呼叫端依賴一長串 `a.b().c().d()` 導覽時，把這段導覽藏到第一個物件的一個方法後面。

## Good Example
- 呼叫端只問 `order` 要結果。

```typescript
const city = order.shippingCity();
```

## Bad Example
- 呼叫端得知道 `order` 內部的整條結構。

```typescript
const city = order.getCustomer().getAddress().getCity().getName();
```

# Rule 13 - Middle Man [SHOULD]
- class 或函式大部分只是把呼叫往下轉手時，移除它，直接呼叫真正的目標。

## Good Example
- 直接呼叫 `userRepository`。

```typescript
const user = await userRepository.findById(id);
```

## Bad Example
- `UserManager` 每個方法都只是原樣轉給 `userRepository`。

```typescript
class UserManager {
  findById(id: string) { return userRepository.findById(id); }
  save(user: User) { return userRepository.save(user); }
}
```

# Rule 14 - Refused Bequest [SHOULD]
- 子類別或實作者忽略或覆寫了大部分繼承來的內容時，拿掉繼承，改用 composition。

## Good Example
- `ReadOnlyList` 只包住需要的能力，不繼承用不到的方法。

```typescript
class ReadOnlyList<T> {
  constructor(private readonly items: T[]) {}
  get(i: number) { return this.items[i]; }
  get length() { return this.items.length; }
}
```

## Bad Example
- 繼承 `Array` 後把大部分方法都覆寫成丟錯。

```typescript
class ReadOnlyList<T> extends Array<T> {
  push(): number { throw new Error("read only"); }
  pop(): T { throw new Error("read only"); }
  splice(): T[] { throw new Error("read only"); }
}
```
