# Rule 1 - 整體結構 [MUST]
- `# SOP` 為一級標題。
- Phase 為二級標題，格式固定為 `## Phase N -- Phase 標題`。
- 每個 Phase 下以阿拉伯數字編號列出步驟。

## Good Example
- 一級標題、Phase 二級標題與 `--` 分隔符、步驟阿拉伯數字編號三者皆符合。

```
# SOP

## Phase 1 -- 確認目標
1. READ 讀取目標 skill 的 SKILL.md 與既有 rules/ 內容，確認要新增、修改或重寫的 RuleFile 範圍。

## Phase 2 -- 整理規則
1. THINK 整理出最少必要的 Rule，同一種錯誤只示範一次。
```

## Bad Example
- Phase 用了三級標題且分隔符為 `:`；步驟用 `-` 條列而非阿拉伯數字編號。

```
# SOP

### Phase 1: 確認目標
- READ 讀取目標 skill 的 SKILL.md
- THINK 整理出最少必要的 Rule
```

# Rule 2 - 步驟格式 [MUST]
- 每一步為「動詞 描述」，動詞在前，後接此步驟所進行的行為描述。
- 動詞只能取自下表：

| 動詞 | 意義 |
|---|---|
| READ | 讀檔 |
| WRITE | 寫檔 |
| THINK | extended thinking |
| DELEGATE | 委派這一步職責給 script / 其他 skill |

## Good Example
- 每一步都以字彙表內的動詞開頭，後接一句行為描述。

```
1. READ 讀取 `rules/RuleFile-格式規範.md` 與 `rules/RuleLevel-定義.md`，依規範定出每條 Rule 的結構與等級。
2. WRITE 依規範寫入目標 skill 的 RuleFile。
```

## Bad Example
- 第一步沒有動詞，直接寫描述；第二步的動詞不在字彙表內。

```
1. 整理出最少必要的 Rule。
2. CHECK 確認結果符合規範。
```
