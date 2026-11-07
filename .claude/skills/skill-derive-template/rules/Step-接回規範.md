# Rule 1 - 骨架與範例兩個路徑都寫進該步並寫明用途 [MUST]
- 骨架與範例的相對路徑都直接寫在被展開的那一步描述中，不能只寫骨架，也不另開步驟載入。
- 路徑後接用途：複製骨架、參照範例改寫填位符號，讓執行的 AI 知道兩個檔各拿來做什麼。

## Good Example
- After 兩個路徑都在原步驟中，各自寫明用途，步驟數不變。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案。
```

## Bad Example
- After 只點名骨架，執行的 AI 不知道有範例可參照。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 依 `templates/class-diagram.mmd` 產出 Mermaid classDiagram 向使用者提案。
```

- After 兩個路徑都有，但沒說複製哪個、參照哪個，另開一步載入也把一步變兩步。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. READ 讀取 `templates/class-diagram.mmd` 與 `templates/class-diagram.example.mmd`。
        2. WRITE 產出 Mermaid classDiagram 向使用者提案。
```

# Rule 2 - 原有規則檔路徑保留 [MUST]
- 該步展開前已點名的規則檔，接回後原樣保留；規則檔管判斷，樣板管格式，兩者並存。
- 不因加入樣板而移除規則檔路徑，也不改規則檔內容。

## Good Example
- After 保留 `rules/ClassDiagram-繪製規範.md`，再加上兩個樣板路徑。

```
Before: 1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案。
After:  1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案。
```

## Bad Example
- After 用樣板路徑換掉了規則檔路徑，該步的判斷依據消失。

```
Before: 1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案。
After:  1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案。
```

# Rule 3 - 動詞維持原動作 [MUST]
- 展開前該步是什麼動詞，展開後仍是什麼動詞。
- 樣板的加入不改變這一步在做的事，只改變做事的依據。

## Good Example
- 展開前後都是 WRITE。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案。
```

## Bad Example
- 為了放樣板把 WRITE 改成 READ，原本的產出動作消失。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. READ 讀取 `templates/class-diagram.mmd` 與 `templates/class-diagram.example.mmd`，改寫填位符號產出 Mermaid classDiagram。
```

# Rule 4 - 被樣板接手的格式細節從描述移除 [SHOULD]
- 已寫進骨架的格式要求不再留在步驟描述中，步驟只留動作與樣板指向。
- 步驟描述與骨架講同一件事，之後改樣板時步驟會跟不上。

## Good Example
- 「類別名稱、關鍵屬性與方法、類別間關係」已進骨架，After 整句移除。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案。
```

## Bad Example
- After 加了樣板路徑，但骨架已接手的格式細節仍整句留在步驟中。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
```

# Rule 5 - 該步已指定樣板則不改 [MUST]
- 再次展開同一步時，只改骨架與範例兩個檔，步驟描述一字不動。
- 判準：步驟描述中已有該樣板的骨架與範例路徑。

## Good Example
- Before 已有兩個路徑，第二次展開後步驟與 Before 完全相同，變化只在骨架多了一行與範例跟著補齊。

```
Before: 1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案。
After:  1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案。
骨架：追加 note for {{ClassName}} "{{responsibility}}"
```

## Bad Example
- Before 已有兩個路徑，第二次展開又在步驟裡再點名一次同一份樣板。

```
Before: 1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案。
After:  1. WRITE 複製 `templates/class-diagram.mmd` 並參照 `templates/class-diagram.example.mmd` 改寫填位符號，產出 Mermaid classDiagram 向使用者提案，並依 `templates/class-diagram.mmd` 為每個類別附一句職責。
```
