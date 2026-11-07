# Rule 1 - 候選 Rule 必須有來源 [MUST]
- 每條候選 Rule 都要能指回步驟描述中的某個字眼，或使用者在對話中的某句補充。
- 指不回來源的判斷，即使看起來合理，也不列為候選，改為向使用者提出。

## Good Example
- 每條候選 Rule 都標出它來自步驟描述的哪個字眼。

```
步驟：WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。

候選 Rule 1 ← 「Mermaid classDiagram」：圖種必須是 classDiagram
候選 Rule 2 ← 「類別名稱、關鍵屬性與方法、類別間關係」：提案須呈現最小必要設計資訊
候選 Rule 3 ← 「關鍵」：不塞入實作雜訊
```

## Bad Example
- 候選 Rule 4 與 5 在步驟描述和使用者補充中都找不到來源，是撰寫者自行加上的。

```
步驟：WRITE 產出 Mermaid classDiagram，呈現類別名稱、關鍵屬性與方法、類別間關係。

候選 Rule 4 ← （無）：未獲使用者明確確認前不寫程式
候選 Rule 5 ← （無）：偏離類別圖須先說明
```

# Rule 2 - 一條 Rule 只裝一個判斷 [SHOULD]
- 一個判斷對應一條候選 Rule；同一個字眼若含多個判斷，拆成多條。
- 判準：Bad Example 若需要示範兩種以上不同的錯誤，就代表裝了兩個判斷。

## Good Example
- 「關鍵屬性與方法」含「要有什麼」與「不要有什麼」兩個判斷，拆成兩條，各自只需一個 Bad Example。

```
候選 Rule 2：提案須呈現最小必要設計資訊（Bad：只有類別名稱）
候選 Rule 3：不塞入實作雜訊（Bad：混入 private 欄位與 getter / setter）
```

## Bad Example
- 一條 Rule 同時管圖種、必要資訊與雜訊，Bad Example 得示範三種錯誤才說得完。

```
候選 Rule 1：類別圖須用 classDiagram、呈現關鍵方法與關係，且不列 private 欄位與 getter / setter
```

# Rule 3 - 已被既有 Rule 涵蓋者剔除 [MUST]
- 涵蓋的判準：既有 Rule 的描述或 Bad Example 已能抓到同一種錯誤。
- 被涵蓋的候選不新增 Rule；若既有 Rule 的描述漏了這個情況，改為在既有 Rule 補一個 bullet。

## Good Example
- 既有 Rule 3 已列「不列日誌、快取、指標等橫切成員」，候選「不列 logger」被它涵蓋，剔除。

```
既有 Rule 3：不塞入實作雜訊（已含：不列日誌、快取、指標等橫切成員）
候選：不列 logger 欄位 → 剔除
```

## Bad Example
- 既有 Rule 3 已列「不列 getter 與 setter」，仍新增一條 Rule 4 重複管同一件事。

```
既有 Rule 3：不塞入實作雜訊（已含：不列 getter 與 setter）
新增 Rule 4：類別圖不列 getter / setter 方法
```
