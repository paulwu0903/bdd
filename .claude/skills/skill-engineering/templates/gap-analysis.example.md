# changelog 根因分析

## 預期
給定 2026-10-01 至 2026-10-21 的 git log（12 筆 commit），changelog 每一條都能對回其中一筆 commit，不出現 log 以外的項目。

## 現況
changelog 有 12 條，其中「支援深色模式」「修正登入逾時」兩條在 git log 中找不到對應 commit。

## 演練軌跡

| Skill | 步驟 | 該步輸入 | 實際產出 | 偏離 |
|---|---|---|---|---|
| changelog | Phase 1 第 1 步 | 使用者給的日期區間 | 交給 commit-reader | 否 |
| commit-reader | Phase 1 第 1 步 | 日期區間 | 最近 10 筆 commit，區間未被使用 | 首次偏離 |
| changelog | Phase 2 第 1 步 | 10 筆 commit、需求「列出本期全部變更」 | 12 條 changelog，2 條無對應 | 承襲上游 |

## 根因

| # | 部件 | 類型 | 缺什麼或多什麼 | 為何必然導致現況 |
|---|---|---|---|---|
| 1 | commit-reader/scripts/git_log.py | script 錯誤 | 缺 --since / --until，寫死 -n 10 | 區間內超過 10 筆時必少讀，下游拿到不完整輸入只能補寫 |

## 改動方向
- 根因 1：重寫 commit-reader 的 git_log.py，以 --since / --until 取區間內全部 commit；changelog 的 Rule 3「不得編造」是為此補償而加，一併刪除。
