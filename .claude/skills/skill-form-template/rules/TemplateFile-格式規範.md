# Rule 1 - 骨架與範例成對 [MUST]
- 一份樣板由兩個檔案組成：骨架 `<名字>.<格式>` 與範例 `<名字>.example.<格式>`，兩者缺一不可。
- 兩檔同名、同副檔名，只差 `.example` 這一段。

## Good Example
- 骨架與範例成對，命名只差 `.example`。

```
templates/class-diagram.mmd
templates/class-diagram.example.mmd
```

## Bad Example
- 範例檔名沒有照 `.example` 的位置與寫法，步驟點名的路徑會找不到檔。

```
templates/class-diagram.mmd
templates/class-diagram-範例.mmd
```

- 只有骨架沒有範例。

```
templates/class-diagram.mmd
```

# Rule 2 - 骨架只含固定結構與填位符號 [MUST]
- 骨架整份就是可直接複製的樣板，內容只有固定結構與填位符號。
- 不放給改寫者看的說明、條列規則或指引；判斷類內容屬於 rules/。
- 判準：複製進產出後應該留著的才寫進骨架；改寫者讀完就該刪的不寫。產出物本身的格式若包含註解（如 Python script 的 PEP 723 區塊、程式碼內的英文註解），該註解屬於固定結構。

## Good Example
- 整份都是固定結構與填位符號，複製後只需改寫填位符號。

```
classDiagram
    class {{ClassName}} {
        {{+attribute: Type}}
        {{+method(): ReturnType}}
    }
    {{ClassA}} --> {{ClassB}} : {{relation}}
```

## Bad Example
- 骨架開頭夾了一行說明，複製後這行會跟著進到產出。

```
%% 每個類別只列關鍵屬性與方法，不列 getter / setter
classDiagram
    class {{ClassName}} {
        {{+attribute: Type}}
        {{+method(): ReturnType}}
    }
    {{ClassA}} --> {{ClassB}} : {{relation}}
```

# Rule 3 - 填位符號格式 [MUST]
- 填位符號一律寫成 `{{name}}`，name 直接說明要填什麼。
- 骨架內所有要改寫的位置都用這個格式，不混用其他符號。

## Good Example
- 每個要改寫的位置都是 `{{name}}`，name 說明要填的內容。

```
class {{ClassName}} {
    {{+attribute: Type}}
}
```

## Bad Example
- 同一骨架混用 `<...>` 與 `__...__`，讀者分不出哪些是要改寫的位置。

```
class <ClassName> {
    __ATTRIBUTE__
}
```

# Rule 4 - 可重複區段骨架寫一份、範例寫多份 [MUST]
- 產出中會重複出現的區段，骨架只寫一份，範例寫兩份以上示範重複。
- 骨架不以重複寫出多份來表示數量。

## Good Example
- 骨架只有一個類別區塊，範例寫了兩個類別示範可重複。

```
骨架：
classDiagram
    class {{ClassName}} {
        {{+attribute: Type}}
    }

範例：
classDiagram
    class Order {
        +id: String
    }
    class LineItem {
        +qty: Int
    }
```

## Bad Example
- 骨架自己寫了兩個類別區塊，讀者分不出兩個是固定數量還是可重複。

```
骨架：
classDiagram
    class {{ClassA}} {
        {{+attribute: Type}}
    }
    class {{ClassB}} {
        {{+attribute: Type}}
    }
```

# Rule 5 - 範例與骨架結構一致 [MUST]
- 範例是骨架填完填位符號的結果，固定結構與骨架一字不差。
- 範例不新增骨架沒有的結構；可重複區段依 Rule 4 多份。

## Good Example
- 範例的每一行都能對回骨架的某一行，差異只在填位符號處。

```
骨架：
    {{ClassA}} --> {{ClassB}} : {{relation}}

範例：
    Order --> LineItem : contains
```

## Bad Example
- 範例多出骨架沒有的 note 行，讀者會以為產出也該有 note。

```
骨架：
    {{ClassA}} --> {{ClassB}} : {{relation}}

範例：
    Order --> LineItem : contains
    note for Order "聚合根"
```

# Rule 6 - 範例不殘留填位符號 [MUST]
- 範例中每個 `{{name}}` 都已換成具體內容。

## Good Example
- 填位符號全部換成具體內容。

```
    Order --> LineItem : contains
```

## Bad Example
- 關係名稱沒填，範例留著 `{{relation}}`。

```
    Order --> LineItem : {{relation}}
```
