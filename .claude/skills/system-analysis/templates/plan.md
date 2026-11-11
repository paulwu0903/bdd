# 系統分析規劃

## Project Structure

### Documentation (plan package 與本次修改的 truth)

```text
specs/
├── plans/{{plan directory name}}/      # Plan：本次要改什麼、怎麼做
{{plan package tree}}
└── truth/                         # Truth：系統現在是什麼（全專案一份，本次就地修改）
{{modified truth tree}}
```

### Source Code (repository root，只列本次新增、修改、刪除的檔案)

```text
{{source code tree}}
```

**Structure Decision**: {{structure decision}}

## 分析流程規劃

### 系統介面的盤點

本次需求共盤點出 `{{interface count}}` 個系統介面。

{{interface number}}. `{{interface name}}`
    - 端點類型：`{{endpoint type}}`
    - 異動：{{新增|修改既有|刪除既有}}
    - 主要介面：{{main interface}}
    - 需求原文依據：{{requirement source}}

### 分析流程的安排

#### Wave {{wave number}}

- 平行分析端點：
    - `{{endpoint type}}`
- 安排理由：{{arrangement rationale}}
- 委派 skill：
    - `{{endpoint type}}` → `{{delegated skill}}`
