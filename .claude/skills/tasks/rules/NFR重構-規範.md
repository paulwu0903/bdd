# Rule 1 - 判定表逐條列出 spec.md 全部 NFR [MUST]
- NFR 重構 Phase 以 `| NFR | 驗證來源 | 判定 |` 表格逐條列出 spec.md 的每個 NFR 編號，一列一個，不漏列。
- 判定只用三種寫法：「已由 feature 驗證」、「不需任務：<理由>」、「列 Txxx」。
- 驗證來源寫出驗證它的 feature 檔；不是靠 `@spec` tag 而是靠 Rule 內容判定的，寫出是哪個 Rule；沒有 feature 覆蓋寫「無 feature 覆蓋」並說明原因。

## Good Example
- NFR-007 沒有 `@spec` tag，但靜音 feature 的 Rule 明確驗證它，寫出 Rule 名稱。

```
| NFR | 驗證來源 | 判定 |
| --- | --- | --- |
| NFR-001 | 無 feature 覆蓋（`research.md` R19 的量測未落到 feature） | 列 T070 |
| NFR-005 | `specs/truth/features/backend/聊天訊息/發送者身分.feature` | 已由 feature 驗證 |
| NFR-007 | `specs/truth/features/backend/聊天訊息/靜音.feature` 的「被靜音者不得察覺」Rule | 已由 feature 驗證 |
```

## Bad Example
- 只列需要任務的 NFR，其餘 NFR 是否被驗證無從查核；判定欄用了自訂的寫法。

```
| NFR | 驗證來源 | 判定 |
| --- | --- | --- |
| NFR-001 | 無 | 要做 |
```

# Rule 2 - 只為沒有 feature 覆蓋、且無法確認達標的 NFR 列重構任務 [MUST]
- 已由 feature 驗證的 NFR 不列任務；沒有 feature 覆蓋、但能從既有程式與文件確認已達標的，判「不需任務」並寫依據。
- 沒有 feature 覆蓋、且須量測或改動才能確認達標的，列 `重構` 任務：路徑含量測程式與可能需要重構的產品程式；Why 寫出量測方式；Checkpoint 寫出門檻與「兩端全套 feature 仍全綠」。
- 共用同一種量測的多個 NFR 合併成一個任務，判定欄都指向同一個任務編號。

## Good Example
- NFR-001 與 NFR-002 都靠同一個聊天負載量測，合併一個任務；Checkpoint 寫出門檻。

```
| NFR-001 | 無 feature 覆蓋（`research.md` R19 的量測未落到 feature） | 列 T070 |
| NFR-002 | 無 feature 覆蓋（`research.md` R19 的量測未落到 feature） | 列 T070 |

- [ ] T070 `重構` 在 `@nfr` 量測加入 500 個房間的聊天負載，量測 NFR-001 與 NFR-002，未達門檻時重構送出與長輪詢喚醒路徑於 `backend/tests/bdd/modules/非功能品質/measure.ts`、`backend/src/services/chat-service.ts`

**Checkpoint**: `npm run bdd:nfr` 的聊天負載量測中，送出到雙方收到的 p95 不超過 1 秒；兩端全套 feature 仍全綠
```

## Bad Example
- 已由 feature 驗證的 NFR-003 也列了重構任務，造成空轉；量測任務沒有寫門檻，無從判定完成。

```
| NFR-003 | `specs/truth/features/backend/聊天訊息/送出訊息與對局.feature` | 列 T071 |

- [ ] T071 `重構` 檢查並優化重送去重於 `backend/src/services/chat-service.ts`

**Checkpoint**: 效能有改善
```

# Rule 3 - 只能人工量測的 NFR 判不需任務並列入完成回報 [MUST]
- 只能以真人可用性測試、問卷等人工方式量測的 NFR，無法以重構程式達成，判「不需任務」並寫明需要的量測方式。
- 若其前提已由 feature 驗證，在理由中寫出驗證前提的 feature 檔；這類 NFR 列入完成回報。

## Good Example
- 首次送出的時間與成功率只能找真人測，前提由兩個前端 feature 驗證。

```
| NFR-012 | 無 feature 覆蓋 | 不需任務：首次送出的時間與成功率只能以真人可用性測試量測，無法以重構程式達成；其前提（進房即見輸入框、Enter 送出）已由 `specs/truth/features/frontend/聊天訊息/訊息收發.feature`、`specs/truth/features/frontend/聊天訊息/鍵盤與輔助技術.feature` 驗證，列入完成回報 |
```

## Bad Example
- 為可用性指標列了重構任務，執行者無法以程式量測，任務永遠無法判定完成。

```
- [ ] T072 `重構` 讓玩家在 15 秒內送出第一則訊息於 `frontend/src/components/ChatInput.tsx`
```
