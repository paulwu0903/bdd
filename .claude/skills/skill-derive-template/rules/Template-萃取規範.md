# Rule 1 - 只抽產出檔案的內容格式 [MUST]
- 該步驟約束的必須是「產出檔案長什麼樣」，才抽成樣板。
- 約束的是判斷、時機或流程的步驟不抽樣板，改走 skill-derive-rule。

## Good Example
- 步驟要求產出一份 classDiagram 檔案，約束的是檔案內容格式，抽成樣板。

```
步驟：WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。
→ 抽成 templates/class-diagram.mmd 與 templates/class-diagram.example.mmd
```

## Bad Example
- 步驟約束的是「何時停止」這個判斷，沒有檔案格式可抽，卻硬做成樣板。

```
步驟：WRITE 詢問使用者是否同意此設計並進入開發；未獲明確確認前停止，不寫程式。
→ 抽成 templates/confirm-design.md
```

# Rule 2 - 骨架內容必須有來源 [MUST]
- 骨架的每個固定段落與每個填位符號，都要能指回步驟描述中的某個字眼，或使用者在對話中的某句補充。
- 指不回來源的段落不寫進骨架，改為向使用者提出。

## Good Example
- 骨架每一行都標出來自步驟描述的哪個字眼。

```
步驟：WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。

classDiagram                        ← 「Mermaid classDiagram」
    class {{ClassName}} {           ← 「類別名稱」
        {{+attribute: Type}}        ← 「關鍵屬性」
        {{+method(): ReturnType}}   ← 「方法」
    }
    {{ClassA}} --> {{ClassB}}       ← 「類別間關係」
```

## Bad Example
- 骨架多出 `<<interface>>` 註記與 note 行，步驟描述與使用者補充都找不到來源。

```
步驟：WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。

classDiagram
    class {{ClassName}} {
        <<interface>>               ← （無）
        {{+attribute: Type}}
        {{+method(): ReturnType}}
    }
    note for {{ClassName}} "{{note}}"   ← （無）
    {{ClassA}} --> {{ClassB}}
```

# Rule 3 - 固定處保留原文、可變處才做填位符號 [SHOULD]
- 每次產出都相同的內容直接寫死在骨架；只有會隨任務變動的內容或參數才做成填位符號。
- 判準：若這個位置換成任何別的值產出就不成立，它是固定處。

## Good Example
- `classDiagram` 關鍵字每次都相同，寫死；類別名稱隨任務變動，做成填位符號。

```
classDiagram
    class {{ClassName}} {
```

## Bad Example
- `classDiagram` 關鍵字被做成填位符號，改寫者可能填成別的圖種。

```
{{diagramType}}
    class {{ClassName}} {
```
