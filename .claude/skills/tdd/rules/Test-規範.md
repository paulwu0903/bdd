# Rule 1 - 透過 public interface 驗證行為 [MUST]
- 測試驗證的是呼叫端在意的行為，只使用 public API，經由真實介面測試，不 mock 內部零件；程式可以整個重寫，測試不該跟著改。
- 以下任一情況即為耦合實作：mock 內部協作者、測 private 方法、斷言呼叫次數或順序、繞過介面驗證（例如直接查資料庫而不是透過介面取回）。
- 判準：重構時行為沒變，測試卻壞了。

## Good Example
- 透過 public API 操作並驗證可觀察的結果，內部怎麼實作都不影響測試。

```typescript
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});

test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

## Bad Example
- 第一筆 mock 內部協作者並斷言呼叫內容；第二筆繞過介面直接查資料庫，兩者都會在重構時壞掉。

```typescript
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});

test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});
```

# Rule 2 - 預期值來自獨立的真實來源 [MUST]
- 預期值必須來自獨立的真實來源：已知正確的 literal、手算過的範例或規格。
- 不得用與程式相同的算法重算預期值，也不得用同樣方式手推 snapshot 或讓常數等於自己；這種測試在構造上必然通過，永遠不會與程式不一致。

## Good Example
- 預期值 15 是獨立的已知 literal。

```typescript
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```

## Bad Example
- 預期值以程式相同的加總方式重算，程式算錯時測試也跟著錯。

```typescript
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});
```

# Rule 3 - 一個測試一個邏輯斷言 [SHOULD]
- 每個測試只驗證一個邏輯上的結果；多個 `expect` 共同描述同一個結果時仍算一個邏輯斷言。

## Good Example
- 兩個測試各自驗證一個結果，失敗時一看就知道是哪個行為壞了。

```typescript
test("checkout with valid cart is confirmed", async () => {
  const result = await checkout(validCart, paymentMethod);
  expect(result.status).toBe("confirmed");
});

test("checkout with declined card is rejected", async () => {
  const result = await checkout(validCart, declinedCard);
  expect(result.status).toBe("rejected");
});
```

## Bad Example
- 一個測試塞進兩個不相干的結果，前一個失敗時後一個根本不會被檢查。

```typescript
test("checkout works", async () => {
  expect((await checkout(validCart, paymentMethod)).status).toBe("confirmed");
  expect((await checkout(validCart, declinedCard)).status).toBe("rejected");
});
```

# Rule 4 - 測試名稱以領域詞彙描述 WHAT [SHOULD]
- 測試名稱要讀起來像規格，描述系統做到什麼（WHAT），不描述怎麼做到（HOW）。
- 專案有 `GLOSSARY.md` 時，名稱沿用其中的領域詞彙。

## Good Example
- 名稱直接說出存在什麼能力，並使用領域詞彙 cart、checkout。

```typescript
test("user can checkout with valid cart", async () => { /* ... */ });
```

## Bad Example
- 名稱描述內部呼叫了什麼，是 HOW 而不是 WHAT。

```typescript
test("checkout calls paymentService.process", async () => { /* ... */ });
```

# Rule 5 - 只在系統邊界 mock [MUST]
- 可以 mock 的只有系統邊界：外部 API（付款、email 等）、時間與隨機性；資料庫與檔案系統只在必要時 mock，資料庫優先改用測試用資料庫。
- 不得 mock 自己的 class 與 module、內部協作者，以及任何自己控制的東西。

## Good Example
- 只替換外部金流 client 與時鐘，自己寫的 `checkout` 與 `Cart` 用真的。

```typescript
test("checkout records payment time", async () => {
  const paymentClient = { charge: async () => ({ ok: true }) };
  const clock = { now: () => new Date("2026-01-01T00:00:00Z") };
  const result = await checkout(createCart([product]), paymentClient, clock);
  expect(result.paidAt).toEqual(new Date("2026-01-01T00:00:00Z"));
});
```

## Bad Example
- mock 的是自己控制的 `Cart` module，測到的是假的購物車而不是真實行為。

```typescript
jest.mock("./cart");
test("checkout records payment time", async () => {
  const result = await checkout(new Cart(), paymentClient, clock);
  expect(result.paidAt).toBeDefined();
});
```

# Rule 6 - 測試以 3A 結構撰寫並加註解 [MUST]
- 每個測試依序分成 Arrange（準備前置狀態）、Act（執行被測行為）、Assert（斷言結果）三段，段與段之間以空行分隔。
- 每段開頭加上該語言的行註解標示：`// Arrange`、`// Act`、`// Assert`（Python 用 `# Arrange`、`# Act`、`# Assert`）。
- Act 段只放一個被測行為；Assert 段只斷言 Act 的結果。
- 多人情境（例如兩位玩家）的前置操作屬於 Arrange，輪流操作中真正被驗證的那一步才是 Act。
- 共用的 helper 與 fixture 不加三段註解；參數化測試的測試函式本身仍要標示三段。

## Good Example
- 三段各有註解並以空行分隔，Act 只有 `checkout` 一個行為。

```typescript
test("user can checkout with valid cart", async () => {
  // Arrange
  const cart = createCart();
  cart.add(product);

  // Act
  const result = await checkout(cart, paymentMethod);

  // Assert
  expect(result.status).toBe("confirmed");
});
```

## Bad Example
- 沒有註解與空行，準備、執行與斷言混在一起；斷言之後又繼續操作，分不出哪一步才是被測行為。

```typescript
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
  cart.add(otherProduct);
  expect((await checkout(cart, paymentMethod)).status).toBe("confirmed");
});
```
