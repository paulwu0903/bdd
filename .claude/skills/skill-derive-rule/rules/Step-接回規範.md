# Rule 1 - 規則檔在該步描述中指定並寫明用途 [MUST]
- 規則檔的相對路徑直接寫在被展開的那一步描述中，不另開步驟載入。
- 路徑後接「依規範做什麼」，讓讀者知道這份規則在這一步的用途。

## Good Example
- After 把路徑放進原步驟，後接依規範產出什麼，步驟數不變。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案。
```

## Bad Example
- 第一組 After 只點名路徑沒說用途；第二組 After 另開一步載入，一步變兩步。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 產出 Mermaid classDiagram（見 `rules/ClassDiagram-繪製規範.md`）。

Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. READ 讀取 `rules/ClassDiagram-繪製規範.md`。
        2. WRITE 產出 Mermaid classDiagram 向使用者提案。
```

# Rule 2 - 動詞維持原動作 [MUST]
- 展開前該步是什麼動詞，展開後仍是什麼動詞。
- 規則檔的加入不改變這一步在做的事，只改變做事的依據。

## Good Example
- 展開前後都是 WRITE。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案。
```

## Bad Example
- 為了放規則檔把 WRITE 改成 READ，原本的產出動作消失。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. READ 讀取 `rules/ClassDiagram-繪製規範.md`，依規範產出 Mermaid classDiagram。
```

# Rule 3 - 被規則檔接手的細節從描述移除 [SHOULD]
- 已寫成 Rule 的判斷不再留在步驟描述中，步驟只留動作與規則檔指向。
- 步驟描述與規則檔講同一件事，之後改規則時步驟會跟不上。

## Good Example
- 「類別名稱、關鍵屬性與方法、類別間關係」已成 Rule，After 整句移除。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案。
```

## Bad Example
- After 加了路徑，但規則檔已接手的細節仍整句留在步驟中。

```
Before: 1. WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
After:  1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
```

# Rule 4 - 該步已指定規則檔則不改 [MUST]
- 再次展開同一步時，只往規則檔追加 Rule，步驟描述一字不動。
- 判準：步驟描述中已有該規則檔的路徑。

## Good Example
- Before 已有路徑，第二次展開後步驟與 Before 完全相同，變化只在規則檔多了 Rule 4。

```
Before: 1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案。
After:  1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案。
規則檔：追加 # Rule 4 - 每個類別附一句職責 [SHOULD]
```

## Bad Example
- Before 已有路徑，第二次展開又在步驟裡點名一次同一份規則檔。

```
Before: 1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案。
After:  1. WRITE 依 `rules/ClassDiagram-繪製規範.md` 產出 Mermaid classDiagram 向使用者提案，並依 `rules/ClassDiagram-繪製規範.md` 為每個類別附一句職責。
```
