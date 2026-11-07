# Tasks: {{plan directory name}}

**Plan**: `specs/plans/{{plan directory name}}`
**Truth**: `specs/truth`

---

## Phase 1: Setup

{{phase description}}

### {{endpoint section name}}

- [ ] T{{task id}} {{[P] 或空}} `環境` {{動作與套件內容}}於 `{{file path}}`
  - Must Read:
    - `{{document}}` -> `{{part}}`
  - Why: {{why this task must bind these references}}

**Checkpoint**: {{checkpoint}}

---

## Phase 2: Foundational

{{phase description}}

**Phase Must Read**:
- `{{document}}` -> `{{part}}`

- [ ] T{{task id}} {{[P] 或空}} `基礎` {{動作與內容}}於 `{{file path}}`
  - Must Read:
    - `{{document}}` -> `{{part}}`
  - Why: {{why this task must bind these references}}

**Checkpoint**: {{checkpoint}}

---

## Phase {{phase number}}: Truth Impact Audit

**Phase Must Read**:
- `specs/plans/{{plan directory name}}/truth-delta.md` -> `{{truth-delta MODIFY 或 DELETE 列的部位}}`

- [ ] T{{task id}} `盤點` 盤點 {{endpoint}} 受 truth 異動影響的 feature、step、helper、fixture 與產品行為於 `specs/plans/{{plan directory name}}/impact-audit.md`
  - Why: {{why this task must bind these references}}

**Checkpoint**: `impact-audit.md` 涵蓋 truth-delta 的全部 MODIFY、DELETE 列，且沒有 tasks.md 未涵蓋的影響

---

## Phase {{phase number}}: MODIFY {{最初依據}} › {{endpoint}}

**Phase Must Read**:
- `specs/plans/{{plan directory name}}/truth-delta.md` -> `{{truth-delta part}}`
- `specs/plans/{{plan directory name}}/impact-audit.md` -> `{{endpoint}}`

- [ ] T{{task id}} {{[US<n>] 或空}} `/bdd realign` 對齊 `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature:{{line}}` 的測試碼於 `{{step file path}}`
  - Optional:
    - `{{document}}` -> `{{part}}`
  - Why: {{why this task must bind these references}}
- [ ] T{{task id}} {{[US<n>] 或空}} `/bdd green` 實作 `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature:{{line}}` 的行為於 `{{implementation file path}}`
  - Must Read:
    - `{{document}}` -> `{{part}}`
  - Why: {{why this task must bind these references}}
- [ ] T{{task id}} {{[US<n>] 或空}} `/bdd refactor` 整理 `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature:{{line}}` 的程式碼於 `{{file path}}`
  - Why: {{why this task must bind these references}}

**Checkpoint**: `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature:{{line}}` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠

---

## Phase {{phase number}}: DELETE {{最初依據}} › {{endpoint}}{{（由 Phase <M> 取代）或空}}

**Phase Must Read**:
- `specs/plans/{{plan directory name}}/truth-delta.md` -> `{{truth-delta part}}`
- `specs/plans/{{plan directory name}}/impact-audit.md` -> `{{endpoint}}`

- [ ] T{{task id}} {{[US<n>] 或空}} `移除` 移除 {{被刪除的行為}} 的測試與產品行為於 `{{file path}}`
  - Why: {{why this task must bind these references}}
- [ ] T{{task id}} {{[P] 或空}} `基礎` {{動作與內容}}於 `{{migration file path}}`
  - Why: {{why this task must bind these references}}

**Checkpoint**: `{{被移除的部位}}` 已無殘留的測試與產品行為；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠

---

## Phase {{phase number}}: `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature` ({{US<n> 或 既有需求異動 #n 或 全域 NFR}})

**Phase Must Read**:
- `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature`
- `specs/truth/features/{{endpoint}}/平臺共用/dsl.md` -> `附錄：共通規則`
- `spec.md` -> `{{story section or requirement id}}`
- `plan.md` -> `系統介面的盤點 › {{interface name}}`

- [ ] T{{task id}} {{[US<n>] 或空}} `/bdd red` 撰寫 `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature` 的 step 於 `{{step file path}}`
  - Optional:
    - `{{document}}` -> `{{part}}`
  - Why: {{why this task must bind these references}}
- [ ] T{{task id}} {{[US<n>] 或空}} `/bdd green` 實作 `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature` 的行為於 `{{implementation file path}}`
  - Must Read:
    - `{{document}}` -> `{{part}}`
  - Why: {{why this task must bind these references}}
- [ ] T{{task id}} {{[US<n>] 或空}} `/bdd refactor` 整理 `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature` 的程式碼於 `{{file path}}`
  - Why: {{why this task must bind these references}}

**Checkpoint**: `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature` 全綠；整個 truth 套件除本 plan 尚未處理的異動與已知失敗外全綠{{；Independent Test 引用或空}}

---

## Phase {{phase number}}: NFR 重構

逐條檢視本 plan `spec.md` 的 NFR 與被 MODIFY 的 NFR：已有 feature 檔驗證的不另列任務；沒有 feature 覆蓋的，判定既有程式是否已達標，未達標或須量測才能確認者列 `重構` 任務。

| NFR | 驗證來源 | 判定 |
| --- | --- | --- |
| {{NFR id}} | {{verification source}} | {{verdict}} |

- [ ] T{{task id}} `重構` {{量測與重構內容}}於 `{{file path}}`
  - Must Read:
    - `spec.md` -> `{{NFR id}}`
    - `{{document}}` -> `{{part}}`
  - Optional:
    - `{{document}}` -> `{{part}}`
  - Why: {{why this task must bind these references}}

**Checkpoint**: {{checkpoint}}

---

## Phase {{phase number}}: Acceptance Gates

**Phase Must Read**:
- `{{document}}` -> `{{part}}`

- [ ] T{{task id}} `驗證` 以隨機順序執行 `specs/truth/features/{{endpoint}}` 的全套 feature 並確認全綠
  - Why: {{why this task must bind these references}}
- [ ] T{{task id}} `驗證` 以 /dsl-refine 的 check_trace.py 確認本 plan 前綴的 acceptance 檢查點都有端點 Example 覆蓋
  - Must Read:
    - `features/acceptance/{{topic}}.feature`
  - Why: {{why this task must bind these references}}

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**：無依賴，可立即開始
- **Foundational (Phase 2)**：依賴 Setup；完成前不得開始 Truth Impact Audit 與任何 MODIFY、DELETE、ADD Phase
- **Truth Impact Audit (Phase {{phase number}})**：依賴 Foundational；完成前不得開始任何 MODIFY、DELETE Phase
- **MODIFY Phase (Phase {{first MODIFY phase}}–{{last MODIFY phase}})**：皆依賴 Truth Impact Audit；提供方端點先於使用方端點，彼此的依賴見 Feature Dependencies
- **DELETE Phase (Phase {{first DELETE phase}}–{{last DELETE phase}})**：皆依賴 Truth Impact Audit；使用方端點先於提供方端點，被本 plan 的 ADD 取代者依賴取代它的 ADD Phase，見 Feature Dependencies
- **ADD Phase (Phase {{first ADD phase}}–{{last ADD phase}})**：皆依賴 Foundational；與其他 Phase 的依賴見 Feature Dependencies
- **NFR 重構 (Phase {{phase number}})**：依賴全部 MODIFY、DELETE、ADD Phase
- **Acceptance Gates (Phase {{phase number}})**：依賴 NFR 重構

### Feature Dependencies

| Phase | feature | 依賴 Phase | 依據 |
| --- | --- | --- | --- |
| {{phase number}} | `specs/truth/features/{{endpoint}}/{{module}}/{{feature file}}.feature` | {{dependency phases 或 —}} | {{reason}} |

### Within Each Feature Phase

- MODIFY Phase：`/bdd realign` → `/bdd green` → `/bdd refactor` 依序執行：green 開始前 realign 須完成，refactor 開始前 green 須全綠；接在後面的 `基礎` 排在 refactor 之後
- DELETE Phase：`移除` 依序執行；接在後面的 `基礎` 排在全部 `移除` 之後
- ADD Phase：`/bdd red` → `/bdd green` → `/bdd refactor` 依序執行：green 開始前 red 須完成，refactor 開始前 green 須全綠
- 同一個 Phase 的任務不平行

### Parallel Opportunities

- {{parallel opportunity}}

---

## Parallel Example: {{example title}}

```text
# {{trigger condition}}
{{lane name}}：{{task chain}}（Phase {{phase number}}，{{phase scope}}{{，依賴說明或空}}）
```
