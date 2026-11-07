# Rule 1 - MUST [MUST]
- 讀到時：違反即修正，不接受任何理由。
- 標給：違反後檔案就無法被正確讀取或套用的規則。

## Good Example
- 標題不是一級標題，整條 Rule 就辨識不出來，只能是 MUST。

```
# Rule 1 - Rule 標題必須是一級標題 [MUST]
```

## Bad Example
- 檔名不清楚只是不好找，檔案照樣能用，應為 SHOULD。

```
# Rule 5 - 檔名應清楚表達主題 [MUST]
```

# Rule 2 - SHOULD [MUST]
- 讀到時：預設遵守，有明確理由才可偏離，並在交付時說明原因。
- 標給：平常該守、但可預見有合理例外的規則。

## Good Example
- 案例短才好讀，但少數規則要較長案例才說得清楚，偏離時說明即可，是 SHOULD。

```
# Rule 3 - 案例資料不超過五行 [SHOULD]
```

## Bad Example
- Good / Bad 順序顛倒讀者會認錯案例，沒有合理例外，應為 MUST。

```
# Rule 2 - Good Example 排在 Bad Example 之前 [SHOULD]
```

# Rule 3 - MAY [MUST]
- 讀到時：用不用都可以，不用不需說明。
- 標給：純屬補充或偏好、省略也不影響規則效力的規則。

## Good Example
- 要不要加 table 純看資料型態，省略也不影響規則，是 MAY。

```
# Rule 4 - 需要時可用 table 補充資料 [MAY]
```

## Bad Example
- 案例不放 code section 就分不出說明與資料，不能省略，應為 MUST。

```
# Rule 2 - 案例資料放在 code section [MAY]
```
