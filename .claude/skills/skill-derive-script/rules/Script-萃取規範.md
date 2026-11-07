# Rule 1 - 抽取判準 [MUST]
- 該步動作能寫成可決定性的程式、輸入輸出能明確定義、交給 script 能加速執行，且不影響執行的準確與效用，才抽成 script。
- 需要 LLM 理解、生成或權衡的部分不進 script；該步同時含機械與判斷時，先拆成兩步，再抽機械的那一步。
- 該步含多個自動化目的時，每個目的各一支 script、各一步 DELEGATE；目的的判準是一句話說得完，動作數多寡不算。

## Good Example
- 「NN 接續既有編號」是掃目錄取最大值加一，可決定性且每次手算都慢，抽成 script；「寫入提案」要 LLM 產生內容，留在 WRITE。

```
步驟：WRITE 寫入 specs/plan/<NN>-<計劃名稱>/class-diagram-proposal.md，NN 接續既有的兩位數編號。
→ 拆出：DELEGATE 取得下一個 NN（scripts/next_plan_dir.py）
→ 保留：WRITE 寫入提案
```

## Bad Example
- 類別收斂是權衡與判斷，寫成程式會犧牲準確，不該抽。

```
步驟：THINK 拆解待開發功能，收斂類別與類別間關係。
→ 抽成 scripts/design_classes.py
```

# Rule 2 - 介面必須有來源 [MUST]
- script 的每個輸入參數、每項輸出與每個副作用，都要能指回步驟描述中的某個字眼，或使用者在對話中的某句補充。
- 指不回來源的不寫進 script，改為向使用者提出。

## Good Example
- 輸入與輸出各自標出來自步驟描述的哪個字眼。

```
步驟：... NN 接續 `specs/plan/` 下既有的兩位數編號。
輸入 --root specs/plan   ← 「specs/plan/ 下」
輸出 下一個 NN           ← 「NN 接續」
```

## Bad Example
- 副作用「建目錄並寫空白檔」在步驟描述與使用者補充中都找不到來源。

```
步驟：... NN 接續 `specs/plan/` 下既有的兩位數編號。
輸入 --root specs/plan   ← 「specs/plan/ 下」
輸出 下一個 NN           ← 「NN 接續」
副作用 mkdir 並寫入空白提案檔   ← （無）
```

# Rule 3 - 原有約束逐條標去向 [MUST]
- 該步已點名的 rules/ 與 templates/，其中每條 Rule 與每個格式要求都要標記去向：進 script、留在其他步驟，或隨被取代的動作消失。
- 標不出去向的不得靜默省略，改為向使用者提出。

## Good Example
- 樣板格式與小數位規則進 script，需要 LLM 的結論段留在拆出的 WRITE 步驟，每條都有去向。

```
步驟原點名：rules/Report-規範.md、templates/report.md
樣板固定段落              → 進 script（build_report.py 直接輸出）
Rule 1 數字保留兩位小數   → 進 script
Rule 2 結論段須說明風險   → 留在拆出的 WRITE 步驟
```

## Bad Example
- Rule 2 沒有去向，接回時路徑一刪，這條約束就無聲消失。

```
步驟原點名：rules/Report-規範.md、templates/report.md
樣板固定段落              → 進 script
Rule 1 數字保留兩位小數   → 進 script
Rule 2 結論段須說明風險   → （未標）
```
