# Rule 1 - 每條修訂過的條目都要比對 acceptance [MUST]
- 修改 spec.md 後，把這次修訂過的每一條 FR、NFR、Edge Case 與 Assumption，逐一和 spec.md 同目錄 `features/acceptance/` 下的所有 feature 檔比對。
- 比對的是修訂後的條目內容，不是修訂前的版本。
- `features/acceptance/` 不存在時，回報「尚無 acceptance feature 檔，未比對」，不略過不說。

## Good Example
- 兩條修訂都列出，各自比對過哪些 feature 檔。

```
修訂 FR-002（移除控制字元、2,000 code point 上限）→ 比對 4 個 feature 檔，相關檔：訊息內容與發言頻率.feature
修訂 FR-006（結果畫面含開局前訊息）→ 比對 4 個 feature 檔，相關檔：聊天紀錄的範圍與保留.feature
```

## Bad Example
- 只比對了其中一條修訂，FR-002 的缺口沒有人發現。

```
修訂 FR-006 → 比對 聊天紀錄的範圍與保留.feature，無衝突
（FR-002 也被修訂，但沒有比對）
```

# Rule 2 - 新增或改變的規則沒有 Example 驗到時列為缺口 [MUST]
- 修訂新增的規則，或修訂改變的行為，在 acceptance 中找不到任何一個 Example 的 When / Then 會驗到它時，列為「缺口」。
- 判準：照現有的 acceptance 寫出測試並全部通過，仍無法證明修訂後的行為成立。
- 既有 Example 沒有違反修訂後的條目、只是沒有驗到新增的部分，仍是缺口，不是衝突。

## Good Example
- 現有 Example 只放對局中的訊息，沒有違反 FR-006，但驗不到「含開局前訊息」，判為缺口。

```
FR-006 → 聊天紀錄的範圍與保留.feature
  Example「阿明猜中獲勝，結果畫面唯讀保留本局聊天紀錄，回首頁後重開的同代碼房間沒有舊訊息」
  聊天區只有對局中的 2 則訊息，驗不到開局前訊息是否出現在結果畫面 → 缺口
```

## Bad Example
- 只因為沒有 Example 和新條目矛盾就判為沒問題，漏掉了 2,000 code point 上限完全沒有情境。

```
FR-002 → 訊息內容與發言頻率.feature：沒有與新規則矛盾的 Example → 無影響
```

# Rule 3 - Example 與修訂後條目矛盾時列為衝突 [MUST]
- Example 的 Given、When 或 Then 依修訂後的條目會得到不同結果時，列為「衝突」。
- 判準：照這個 Example 寫出測試，依修訂後的條目實作時，測試會失敗。

## Good Example
- 修訂後超過 2,000 code point 要被拒絕，Example 卻期望送出成功，判為衝突。

```
FR-002 → 訊息內容與發言頻率.feature
  Example「組合符號疊加的訊息照常送出」：Then 雙方聊天區出現這則訊息（內容 2,400 個 code point）
  修訂後應拒絕並提示「訊息最多 200 字」→ 衝突
```

## Bad Example
- Example 期望的結果已和修訂後的條目相反，卻因為「Example 仍然存在」而判為缺口，讀者會以為只要補情境、不必改舊情境。

```
FR-002 → Example「組合符號疊加的訊息照常送出」→ 缺口
```

# Rule 4 - 回報每一項的條目、位置、類型與補齊方式 [MUST]
- 每一項寫出：spec 條目編號、feature 檔名與 Example 名稱（缺口沒有對應的 Example 時寫「無對應 Example」）、類型（缺口 / 衝突）。
- 回報的最後提醒：進入下一個 skill 前，先以 `/spec-by-example` 補齊或修正這些情境。
- 比對後沒有任何受影響的情境時，明確回報「修訂未影響任何 acceptance 情境」，不省略回報。

## Good Example
- 兩項都寫齊位置與類型，最後提醒補齊方式。

```
| spec 條目 | feature 檔 / Example | 類型 |
|---|---|---|
| FR-002 | 訊息內容與發言頻率.feature / 無對應 Example | 缺口 |
| FR-006 | 聊天紀錄的範圍與保留.feature / 阿明猜中獲勝，結果畫面唯讀保留本局聊天紀錄… | 缺口 |

進入 /system-analysis 前，請先以 /spec-by-example 補齊上述情境。
```

## Bad Example
- 只說有缺口，沒有位置、類型與補齊方式，讀者不知道要補哪裡、用什麼補。

```
spec 有修訂，acceptance 可能需要更新。
```

# Rule 5 - 不直接修改 acceptance feature 檔 [MUST]
- 缺口與衝突只回報，不在本 skill 中新增、修改或刪除 `features/acceptance/` 下的任何檔案。
- 補齊與修正交給 `/spec-by-example`，由它依自己的規範產出情境。

## Good Example
- 只回報並指向 `/spec-by-example`，feature 檔維持原狀。

```
FR-002 缺口已回報；features/acceptance/ 未變更，待 /spec-by-example 補齊。
```

## Bad Example
- 在 technical-research 中自行追加 Example，繞過了 spec-by-example 的格式與審查。

```
已在 訊息內容與發言頻率.feature 追加 Example「超過 2,000 code point 的訊息被拒絕」。
```
