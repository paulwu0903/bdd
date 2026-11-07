# Rule 1 - 外部依賴以 dependency injection 傳入 [SHOULD]
- 位於系統邊界的外部依賴，由呼叫端傳入，不在函式或 class 內部自行建立，讓測試能在邊界替換它。

## Good Example
- 金流 client 由參數傳入，測試可直接換成假的 client。

```typescript
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}
```

## Bad Example
- client 在函式內部建立並讀取環境變數，測試無法在邊界替換。

```typescript
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

# Rule 2 - 外部操作採用 SDK-style 個別函式 [SHOULD]
- 每個外部操作各自一個具名函式，不寫一個靠參數分流的通用 fetcher。
- 這樣每個 mock 只回傳一種固定形狀、測試 setup 不需要條件邏輯、一眼看得出測試打了哪些 endpoint，且每個 endpoint 各自有型別。

## Good Example
- 每個操作各自一個函式，可個別 mock。

```typescript
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};
```

## Bad Example
- 只有一個通用 fetch，mock 時必須在 mock 內依 endpoint 寫條件分支。

```typescript
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```
