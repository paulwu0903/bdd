# Rule 1 - 動詞改為 DELEGATE [MUST]
- 接回後該步動詞一律是 DELEGATE；原本的 READ / WRITE / THINK 動作已由 script 承接。

## Good Example
- THINK 改為 DELEGATE，動作從「AI 自己算」變成「委派 script 算」。

```
Before: 2. THINK 掃 specs/plan/ 取最大兩位數編號加一，定出 NN。
After:  2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --root specs/plan`，取得下一個 NN。
```

## Bad Example
- 動詞沒換，字彙表定義委派給 script 的動詞是 DELEGATE。

```
Before: 2. THINK 掃 specs/plan/ 取最大兩位數編號加一，定出 NN。
After:  2. THINK 執行 scripts/next_plan_dir.py 取得 NN。
```

# Rule 2 - 步驟寫明執行指令、參數與產出 [MUST]
- 指令固定為 ``uv run `${CLAUDE_SKILL_DIR}/scripts/<name>.py <args>` ``，後接這一步拿到什麼結果。

## Good Example
- 有 `uv run`、完整路徑、參數與產出。

```
After:  2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --root specs/plan`，取得下一個 NN。
```

## Bad Example
- 沒有 `uv run`、沒有路徑前綴、沒有參數、沒說拿到什麼。

```
After:  2. DELEGATE 執行 next_plan_dir.py。
```

# Rule 3 - DELEGATE 步驟不點名 rules/ 與 templates/ [MUST]
- 執行 script 不需要載入規則或樣板，該步原有的 rules/、templates/ 路徑依萃取時標記的去向移到承接的步驟或移除。

## Good Example
- 樣板已進 script，路徑移除；規則檔留給拆出的 WRITE 步驟。

```
Before: 1. WRITE 依 `rules/Report-規範.md` 複製 `templates/report.md` 並參照 `templates/report.example.md` 改寫填位符號，產出週報。
After:  1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/build_report.py --data metrics.json`，產出週報草稿。
        2. WRITE 依 `rules/Report-規範.md` 補寫週報的結論與風險段。
```

## Bad Example
- DELEGATE 步驟仍點名規則檔，script 不會讀它，路徑白載。

```
Before: 1. WRITE 依 `rules/Report-規範.md` 複製 `templates/report.md` 並參照 `templates/report.example.md` 改寫填位符號，產出週報。
After:  1. DELEGATE 依 `rules/Report-規範.md` 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/build_report.py --data metrics.json`，產出週報草稿。
```

# Rule 4 - 被 script 接手的細節從描述移除 [SHOULD]
- 已由 script 實作的做法不再留在步驟描述中，步驟只留 DELEGATE、指令與產出。
- 步驟描述與 script 講同一件事，之後改 script 時步驟會跟不上。

## Good Example
- 「取最大兩位數編號加一」已是 script 邏輯，After 整句移除。

```
Before: 2. THINK 掃 specs/plan/ 取最大兩位數編號加一，定出 NN。
After:  2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --root specs/plan`，取得下一個 NN。
```

## Bad Example
- 加了指令，但 script 已接手的演算法仍整句留在步驟中。

```
Before: 2. THINK 掃 specs/plan/ 取最大兩位數編號加一，定出 NN。
After:  2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --root specs/plan`，掃 specs/plan/ 取最大兩位數編號加一，取得下一個 NN。
```

# Rule 5 - 該步已指定 script 則不改 [MUST]
- 再次展開同一步時，只改 script，步驟描述一字不動。
- 判準：步驟描述中已有該 script 的路徑。

## Good Example
- Before 已有路徑，第二次展開後步驟與 Before 完全相同，變化只在 script 多了一個選項。

```
Before: 2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --root specs/plan`，取得下一個 NN。
After:  2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --root specs/plan`，取得下一個 NN。
script：新增 --width 選項
```

## Bad Example
- Before 已有路徑，第二次展開又在步驟裡把新選項與路徑再寫一次。

```
Before: 2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --root specs/plan`，取得下一個 NN。
After:  2. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --root specs/plan`，取得下一個 NN，並以 `${CLAUDE_SKILL_DIR}/scripts/next_plan_dir.py --width 3` 支援三位數。
```
