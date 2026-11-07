# Rule 1 - Rule 區塊 [MUST]
- 一個 RuleFile 由一到多個 Rule 組成，依序編號。
- 每個 Rule 以一級標題 `# Rule N - 規則名稱 [等級]` 開頭，等級依 Rule 3 標記。
- 標題下以 bullet 條列規則內容，需要時可用 markdown table 補充資料。
- 之後依序接 `## Good Example` 與 `## Bad Example` 兩個區塊。

## Good Example
- 一級標題、bullet 條列、Good / Bad 兩個區塊依序齊全。

````markdown
# Rule 1 - Rule 區塊 [MUST]
- 每個 Rule 以一級標題 `# Rule N - 規則名稱 [等級]` 開頭。

## Good Example
- 一級標題、編號、` - `、規則名稱、等級五者齊全。

```
# Rule 1 - Rule 區塊 [MUST]
```

## Bad Example
- 標題用了二級，分隔符為 `:`。

```
## Rule 1: Rule 區塊
```
````

## Bad Example
- 規則寫成段落而非 bullet；缺少 Bad Example 區塊。

````markdown
# Rule 1 - Rule 區塊 [MUST]
每個 Rule 以一級標題開頭。

## Good Example
- 一級標題、編號、` - `、規則名稱、等級五者齊全。

```
# Rule 1 - Rule 區塊 [MUST]
```
````

# Rule 2 - Example 區塊 [MUST]
- Good Example 以 `## Good Example` 開頭，Bad Example 以 `## Bad Example` 開頭。
- 第一個 bullet 說明案例為何是好示範，或違反了哪一點，只強調重點或差異。
- 接著在 code section 放完整的案例資料，一筆或多筆皆可。
- 只有案例資料放在 code section，其餘內容直接用 markdown 語法。

## Good Example
- 說明以 bullet 點出重點，案例放在 code section。

````markdown
## Good Example
- 一級標題、編號、` - `、規則名稱、等級五者齊全。

```
# Rule 1 - Rule 區塊 [MUST]
```
````

## Bad Example
- 說明寫成段落且沒有指出重點；案例沒有放在 code section。

```markdown
## Good Example
這樣寫對。
# Rule 1 - Rule 區塊 [MUST]
```

# Rule 3 - 強制等級 [MUST]
- Rule 標題尾端以中括號標記強制等級，格式為 `# Rule N - 規則名稱 [等級]`，等級的意義與選擇依據見 `rules/RuleLevel-定義.md`。

## Good Example
- 等級放在標題尾端的中括號內，且取自定義檔。

```
# Rule 1 - Rule 標題必須是一級標題 [MUST]
# Rule 4 - 需要時可用 table 補充資料 [MAY]
```

## Bad Example
- 第一行的等級不在定義檔內；第二行把等級放在標題開頭而非尾端。

```
# Rule 1 - Rule 區塊 [REQUIRED]
# [SHOULD] Rule 2 - Example 區塊
```
