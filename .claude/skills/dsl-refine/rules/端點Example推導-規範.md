# Rule 1 - 每個端點 Example 都錨定 acceptance 檢查點或 spec 編號 [MUST]
- 每個端點 Example 都只驗某個 acceptance 檢查點中屬於該端的職責段，或依 `rules/規格補充-規範.md` 補出的某條 spec 需求，並以 `@ac:` 或 `@spec:` 追溯 tag 指向它。
- `analysis/` 與 plan.md 只回答「誰負責」與「怎麼落地」；只存在於契約、在 acceptance 與 spec 都找不到對應的項目（如未授權、格式損壞的請求），不寫成 Example，留到回報列出。

## Good Example
- Example 驗的是檢查點 1-1 中後端的那一段，tag 指回該檢查點。

```
@ac:訂單成立與付款:1-1
Example: 購物車有 1 件無線耳機時送出訂單
  Given "小芳" 的購物車中有 "無線耳機" 1 件
  When "小芳" 送出訂單
  Then "小芳" 的訂單為待付款，"無線耳機" 的可售數量剩 9
```

## Bad Example
- openapi.yaml 定義了 401，但 acceptance 與 spec 都沒有寫到未登入，仍被寫成 Example，還硬掛一個不相干的 tag。

```
@ac:訂單成立與付款:1-1
Example: 未登入送出訂單被拒絕
  Given 訪客尚未登入
  When 訪客送出訂單
  Then 訪客的 "送出訂單" 因 "尚未登入" 被拒絕，沒有任何改變
```

# Rule 2 - 預設寫原子 Example，必要時才寫 `@journey` [MUST]
- 預設每個職責段寫一個原子 Example：以 Given 直接準備狀態，接一句 When，再接該端的 Then。
- 只有當該端要驗的行為必須靠該端連續操作累積出的中間狀態才觀察得到，以 Given 直接準備會讓驗證失去意義時，才寫 `@journey`（When／Then 交錯）。
- 不在端點重抄 acceptance 的整條 Journey。

## Good Example
- 要驗的是同一筆訂單真的走過一次失敗付款後，仍能在保留時間內改用另一種方式付款成功；用 Given 直接造出「失敗過一次」的資料，測不到失敗路徑留下的狀態是否允許重試，所以寫成 journey。

```
@ac:訂單成立與付款:2-1 @ac:訂單成立與付款:2-2 @journey
Example: 信用卡付款失敗後改用 LINE Pay 付款成功
  Given "阿哲" 的購物車中有 "無線耳機" 1 件
  When "阿哲" 送出訂單
  And "阿哲" 以 "信用卡" 付款失敗，原因為 "卡片額度不足"
  Then "阿哲" 的訂單為待付款，"無線耳機" 的可售數量剩 9
  When "阿哲" 以 "LINE Pay" 付款成功
  Then "阿哲" 的訂單狀態為 "已付款"
```

## Bad Example
- 後端把 acceptance 第 1 條 Journey 從送出訂單到出貨整條重抄；出貨前的每個狀態都能用 Given 直接準備，應拆成原子 Example。

```
@ac:訂單成立與付款:1-1 @ac:訂單成立與付款:1-2 @ac:訂單成立與付款:1-3 @journey
Example: 從送出訂單到出貨
  Given "小芳" 的購物車中有 "無線耳機" 1 件
  When "小芳" 送出訂單
  Then …
  When "小芳" 以 "信用卡" 付款成功
  Then …
  When 商家將 "小芳" 的訂單出貨
  Then …
```

# Rule 3 - 中途檢查點的前置狀態折疊成 Given [MUST]
- 原子 Example 的 Given 等於該檢查點之前所有步驟（含 Background 與先前的 When）累積出的狀態，以 Given 直接建立，不重播先前的 When。
- 每個狀態元素的值都與 acceptance 推得的值相同。

## Good Example
- 第 3 條 Journey 的檢查點 2 之前，訂單已因逾時取消、可售數量已回到 10，折疊成兩句 Given。

```
@ac:訂單成立與付款:3-2
Example: 已取消的訂單再次付款
  Given "小美" 有一筆狀態為 "已取消" 的訂單
  And "無線耳機" 的可售數量為 10
  When "小美" 對已取消的訂單再次付款
  Then "小美" 的 "付款" 因 "訂單已取消" 被拒絕，沒有任何改變
```

## Bad Example
- 第一組把先前的 When 原樣重播成 Given；第二組折疊後的可售數量寫成 9，與 acceptance 推得的 10 不符。

```
Given "小美" 送出訂單
And "小美" 以 "信用卡" 付款失敗
And 經過 16 分鐘

Given "小美" 有一筆狀態為 "已取消" 的訂單
And "無線耳機" 的可售數量為 9
```

# Rule 4 - When 只取檢查點的 When 段 [MUST]
- When 只寫該檢查點 When 段中屬於該端的動作，行動者、值、先後與同時關係都與 acceptance 相同，不混入前置動作，也不拆出 acceptance 沒有的步驟。
- 檢查點沒有 When 段（Given 後直接接 Then）時，以該角色讀取這個狀態的動作作為 When：前端為開啟對應畫面，後端為讀取該狀態；不新增其他行為。

## Good Example
- When 與 acceptance 的 When 段相同；沒有 When 段的檢查點，前端以開啟畫面作為 When。

```
acceptance：When "小芳" 送出訂單
endpoint ：When "小芳" 送出訂單

acceptance：Given … Then "小芳" 的訂單狀態為 "待付款"（無 When 段）
frontend ：When "小芳" 開啟訂單頁
```

## Bad Example
- When 混入登入與開頁，又把送出訂單拆成「填寫地址」「按下送出」兩步，這些在 acceptance 都沒有。

```
When "小芳" 登入
And "小芳" 開啟結帳頁
And "小芳" 填寫收件地址
And "小芳" 按下送出訂單
```

# Rule 5 - Then 涵蓋職責段的每個 oracle 與維持不變 [MUST]
- 該端 Then 的必查要驗到 Then 段中屬於該端的每個結果，以及每句「仍為／仍有／沒有」的維持不變。
- 屬於其他端點的結果不斷言，寫進該端 Then 的 `不必查`，原因寫「屬 <端點> 職責」。

## Good Example
- 後端驗到拒絕與兩項維持不變；畫面上的拒絕文案屬前端，放進不必查。

```
acceptance：Then 系統拒絕付款，原因為 "訂單已取消"
            And "小美" 的訂單狀態仍為 "已取消"
backend   ：Then "小美" 的 "付款" 因 "訂單已取消" 被拒絕，沒有任何改變
            必查：拒絕回應；訂單仍為已取消；可售數量不變
            不必查：• `呈現結果` 中的畫面文案：屬 frontend 職責
```

## Bad Example
- 後端只驗了拒絕，漏了「訂單狀態仍為已取消」；又斷言了屬於前端的畫面文案。

```
backend：Then "小美" 的付款被拒絕
         必查：拒絕回應；畫面顯示「訂單已取消」
```

# Rule 6 - 要抓的錯誤實作由規則語意推得 [SHOULD]
- 依檢查點背後的規則，推出最可能的錯誤實作（邊界比較方向、漏掉回補、重複扣減、順序顛倒…），寫進該端 Then 的 `抓得到的錯誤實作`，並確保必查真的抓得到它。

## Good Example
- 由「失敗後可售數量仍為 9」推出「失敗時又扣一次」的錯誤實作。

```
@ac:訂單成立與付款:2-1
抓得到的錯誤實作：付款失敗時再扣一次可售數量，變成 8。
```

## Bad Example
- 錯誤實作寫得空泛，推不出必查要比對什麼。

```
抓得到的錯誤實作：付款邏輯有錯。
```

# Rule 7 - acceptance 與上游衝突時以 acceptance 為準 [MUST]
- plan.md、`analysis/`、research.md 或 techstack.md 與 acceptance 不一致時，依 acceptance 撰寫，不修改上游文件，並在回報中列出衝突與應修正的上游檔。
- acceptance 的動作照字面在上游參數下得不到它寫的結果時（例如「重新整理頁面」只需幾百毫秒，觸發不了 6 秒的斷線判定，卻寫了對手看到斷線倒數），採用能讓該檢查點成立的解讀，並在回報中列為待使用者確認的判斷。

## Good Example
- openapi.yaml 的保留時間預設為 30 分鐘，acceptance 寫 15 分鐘；依 acceptance 寫，並回報衝突。

```
dsl.md 預設參數：• `待付款保留時間`：整數；預設為 15。
回報：analysis/openapi.yaml 的保留時間為 30 分鐘，與 acceptance〈訂單成立與付款〉的 15 分鐘衝突，應修正 openapi.yaml。
```

## Bad Example
- 依上游的 30 分鐘撰寫，acceptance 的「經過 16 分鐘後取消」變得不成立；或直接改了 openapi.yaml。

```
dsl.md 預設參數：• `待付款保留時間`：整數；預設為 30。
```

# Rule 8 - 上游缺技術細節時不自行編造 [MUST]
- 撰寫 dsl.md 需要的技術細節（端點、欄位、錯誤碼、畫面元素、資料表）在上游找不到時，不自行編造；該列停下，在回報中列為上游缺口，等使用者補上游或授權暫定值。

## Good Example
- openapi.yaml 沒有「訂單已取消」的錯誤碼，列為上游缺口。

```
回報：上游缺口：analysis/openapi.yaml 沒有付款被拒且原因為「訂單已取消」的錯誤碼；`拒絕原因對照` 待補。
```

## Bad Example
- 自行編了一個錯誤碼寫進預設參數。

```
• `拒絕原因對照`：字串；預設為 訂單已取消＝ORDER_CANCELLED。
```

# Rule 9 - 每個端點 Example 只驗一個面向 [MUST]
- 一個職責段的 Then 若包含兩個以上可以分開觀察的結果（例如「訂單已付款」與「收到確認通知」），每個結果各自成為一條 Rule、各寫一個 Example：Given 與 When 相同，只保留屬於該 Rule 的 Then。
- 同一個結果從不同角度的斷言（例如「付款被拒絕」與「訂單狀態仍為已取消」）屬於同一個面向，可以留在同一個 Example。
- Rule 名稱不用「並」「且」「、」把兩個面向接成一條。

## Good Example
- 檢查點 1-2 的「訂單已付款」與「收到確認通知」可以分開觀察，拆成兩條 Rule，When 都只有同一句。

```
Rule: 付款成功後訂單必須成立

  @ac:訂單成立與付款:1-2
  Example: 小芳以信用卡付款 2990 元
    Given "小芳" 有一筆待付款的訂單，金額為 2990
    When "小芳" 以 "信用卡" 付款成功
    Then "小芳" 的訂單為已付款

Rule: 付款成功後會員必須收到確認通知

  @ac:訂單成立與付款:1-2
  Example: 小芳付款成功後的通知
    Given "小芳" 有一筆待付款的訂單，金額為 2990
    When "小芳" 以 "信用卡" 付款成功
    Then "小芳" 收到訂單確認通知，金額為 2990
```

## Bad Example
- 兩個可分開觀察的結果放在同一條 Rule、同一個 Example，Rule 名稱也用「並」接起來；通知沒寄出時，整個 Example 失敗，看不出訂單是否已成立。

```
Rule: 付款成功後訂單必須成立並通知會員

  @ac:訂單成立與付款:1-2
  Example: 小芳以信用卡付款 2990 元
    Given "小芳" 有一筆待付款的訂單，金額為 2990
    When "小芳" 以 "信用卡" 付款成功
    Then "小芳" 的訂單為已付款
    And "小芳" 收到訂單確認通知，金額為 2990
```
