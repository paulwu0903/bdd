# Rule 1 - name 等於目錄名 [MUST]
- frontmatter 的 `name` 與 skill 所在目錄名完全相同。

## Good Example
- 目錄名與 name 一致。

```
.claude/skills/skill-engineering/SKILL.md
name: skill-engineering
```

## Bad Example
- 目錄名與 name 不一致，呼叫時找不到對應的 skill。

```
.claude/skills/skill-engineering/SKILL.md
name: skill-engineer
```

# Rule 2 - description 寫明觸發時機 [MUST]
- description 以「<情境>時，必須使用此 skill」句式說明何時用，情境要具體到讀者能判斷當下是否符合。
- 只寫 skill 做什麼而不寫何時用的 description 不合格。

## Good Example
- 情境具體，讀者能判斷當下是否該觸發。

```
description: 當要撰寫 SKILL，且涉及 SOP section 的新增、修改或重寫時，必須使用此 skill。
```

## Bad Example
- 只說做什麼，沒有說何時用。

```
description: 幫忙寫 SOP。
```

# Rule 3 - compatibility 與 scripts/ 同進退 [MUST]
- skill 內有 scripts/ 時，frontmatter 必有 `compatibility: Requires Python >=3.11 and uv`，內容固定；沒有 scripts/ 時不寫這一行。

## Good Example
- 有 scripts/，且有固定內容的 compatibility 行。

```
scripts/skill_lint.py
compatibility: Requires Python >=3.11 and uv
```

## Bad Example
- 有 scripts/ 卻沒有 compatibility，執行者不知道需要 uv。

```
scripts/skill_lint.py
（frontmatter 無 compatibility）
```
