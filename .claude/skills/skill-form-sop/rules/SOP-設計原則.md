# Rule 1 - 按需載入 [MUST]
- 規則檔只在真的要用它的那一步被 READ，該步的描述要寫明讀來做什麼，不出現只讀不用的步驟。
- 不在流程開頭預先載入，也不在其他步驟重複點名規則檔。

## Good Example
- 下方兩筆 Bad Example 的改良版：規範到 Phase 2 要定結構與等級時才讀，一次讀完直接用，之後不再點名。

```
## Phase 1 -- 確認目標
1. READ 讀取目標 skill 的 SKILL.md 與既有 rules/ 內容，確認要新增、修改或重寫的 RuleFile 範圍。

## Phase 2 -- 整理規則
1. THINK 整理出最少必要的 Rule。
2. READ 讀取 `rules/RuleFile-格式規範.md` 與 `rules/RuleLevel-定義.md`，依規範定出每條 Rule 的結構與等級。
```

## Bad Example
- 同一流程，開頭先把兩份規範全部讀起來放，Phase 2 才用到。

```
## Phase 1 -- 載入規則與目標
1. READ 讀取 `rules/RuleFile-格式規範.md`。
2. READ 讀取 `rules/RuleLevel-定義.md`。
3. READ 讀取目標 skill 的 SKILL.md 與既有 rules/ 內容，確認要新增、修改或重寫的 RuleFile 範圍。

## Phase 2 -- 整理規則
1. THINK 依規範整理出最少必要的 Rule 與等級。
```

- 同一流程，Phase 2 內每步各自點名規則檔，同一份檔案被重複點名。

```
## Phase 2 -- 整理規則
1. THINK 依 `rules/RuleLevel-定義.md` 判斷每條 Rule 的等級。
2. THINK 依 `rules/RuleFile-格式規範.md` 整理 Rule 的結構。
3. THINK 依 `rules/RuleFile-格式規範.md` 與 `rules/RuleLevel-定義.md` 規劃案例。
```

# Rule 2 - 最短可執行路徑 [SHOULD]
- 每一步都要有動作，不出現只描述背景或複述規則檔內容的步驟。
- 能用一步完成的不拆成多步。

## Good Example
- 下方 Bad Example 的改良版：前情提要刪除，複述規則的兩步併回一個 THINK，判準留在規則檔內。

```
## Phase 2 -- 整理規則
1. THINK 整理出最少必要的 Rule，同一種錯誤只示範一次。
```

## Bad Example
- 第 1 步只是前情提要，沒有動作；第 2、3 步在複述規則檔的內容，沒有產生新的判斷；真正的整理被推到第 4 步。

```
## Phase 2 -- 整理規則
1. THINK 確認本次任務是為目標 skill 撰寫 RuleFile。
2. THINK 判斷每條 Rule 的等級，避免把偏好誤寫成硬性規則，或把必要結構降成可選項。
3. THINK 確認標題、等級、規則描述、Good Example、Bad Example 的固定順序。
4. THINK 整理出最少必要的 Rule，同一種錯誤只示範一次。
```
