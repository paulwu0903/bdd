# Clarify Report：公司內部請假系統

- 已問且已回答：5 / 5
- 更新的 spec：`specs/plans/003-leave-request-system/spec.md`
- spec_lint：OK: no violations
- 既有需求異動：新增 #2 MODIFY `001/FR-004`（使用者於 2026-10-28 確認）；#1 未變
- requirements 同步：ADD 5、MODIFY 1、DELETE 0

## 問答與回寫

| # | Taxonomy | 總結之提問 | 使用者選擇 | 回寫區塊 |
|---|---|---|---|---|
| 1 | Functional Scope & Behavior | 誰能查看他人的請假紀錄？ | 2（直屬主管與 HR） | US2 FR-009、US2 Acceptance Scenarios、Assumptions |
| 2 | Domain & Data Model | 同一員工日期重疊的申請是否允許？ | 1（送出時拒絕） | US1 FR-007、US1 Acceptance Scenarios、Key Entities、Assumptions |
| 3 | Non-Functional Quality Attributes | 主管審核頁的最新申請要多快出現？ | Others：30 秒內 | Global NFR-002、Success Criteria SC-003、Assumptions |
| 4 | Edge Cases & Failure Handling | 主管逾期未審核時，系統要在幾天後提醒？（原 AI 推定：7 天） | 2（3 個工作日） | US1 Edge Cases、Global NFR-004、Assumptions（AI 推定改寫為使用者釐清） |
| 5 | Current Requirements Consistency | 新的查看權限與 001/FR-004「只有本人能查看請假紀錄」衝突，要怎麼處理？ | 2（MODIFY 001/FR-004） | 既有需求異動 #2、Assumptions |

## 覆蓋總結

| 類別 | 狀態 | 說明 |
|---|---|---|
| Functional Scope & Behavior | Resolved | 查看權限已拍板；out-of-scope 原本即明確 |
| Domain & Data Model | Resolved | 重疊申請規則已寫入 FR-007 與 Key Entities |
| Interaction & UX Flow | Outstanding | 空白狀態文案未定，低影響，可於 ui-plan 處理 |
| Non-Functional Quality Attributes | Resolved | 「即時」已量化為 30 秒內（SC-003） |
| Integration & External Dependencies | Deferred | Email 服務選型 → technical-research；屬 tech stack，不影響需求行為 |
| Edge Cases & Failure Handling | Resolved | 逾期提醒天數由 AI 推定「7 天」改為使用者拍板「3 個工作日」；斷線、退回、撤回原本即完整 |
| Constraints & Tradeoffs | Clear | 已明示不做排班與補卡 |
| Terminology & Consistency | Resolved | 「主管 / 審核者」統一為「審核人」 |
| Completion Signals | Clear | 每個 User Story 均有可測的 Acceptance Scenarios |
| Misc / Placeholders | Deferred | 「報表要好看」未量化，但超出本次 5 題預算且影響低；下次 clarify-over-specs 再處理 |
| Current Requirements Consistency | Resolved | 查看權限與 001/FR-004 的衝突改寫為既有需求異動 #2；#1 原已由使用者確認 |

## 建議下一步

進入 /spec-by-example；Interaction & UX Flow 的 Outstanding 項交由 ui-plan 處理，Integration 的 Deferred 項交由 /technical-research，Misc / Placeholders 的 Deferred 項於 plan 後再跑一次 /clarify-over-specs。
