# changelog 編排提案

## 來源與去向

| 編號 | 原文 | 出處 | 去向 |
|---|---|---|---|
| S1 | 以 uv run 執行 scripts/git_log.py -n 10 取得最近 commit | commit-reader/SKILL.md:9 | commit-reader Phase 1 第 1 步 |
| S2 | 交給 commit-reader 取得區間內的 commit | changelog/SKILL.md:9 | changelog Phase 1 第 1 步 |
| S3 | 依 rules/Changelog-規範.md 產出 changelog | changelog/SKILL.md:12 | changelog Phase 2 第 1 步 |
| S4 | Rule 1 每條以動詞開頭 | changelog/rules/Changelog-規範.md:1 | rules/Changelog-規範.md |
| S5 | Rule 3 不得編造 log 以外的項目 | changelog/rules/Changelog-規範.md:40 | 捨棄 ← 根因 1 |
| S6 | git_log.py 以 --since / --until 取區間內全部 commit | 根因分析 根因 1 | scripts/git_log.py |
| S7 | 其餘部件：rules/Changelog-規範.md Rule 1–2、Rule 4 | — | 原樣保留 |

## 施工後 SOP 預覽：commit-reader

```
---
name: commit-reader
description: 要取得 git 區間內的 commit 清單時，必須使用此 skill。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 取得 commit
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/git_log.py --since <起點> --until <終點>`，取得區間內全部 commit。
```

## 施工後 SOP 預覽：changelog

```
---
name: changelog
description: 要依區間內的 commit 產出 changelog 時，必須使用此 skill。
---

# SOP

## Phase 1 -- 取得 commit
1. DELEGATE 交給 commit-reader，取得區間內全部 commit。

## Phase 2 -- 產出 changelog
1. WRITE 依 `rules/Changelog-規範.md` 產出 changelog。
```

## 施工表

| # | Pass | Skill | 目標步驟 | Deriver | 萃取內容 | 來源 |
|---|---|---|---|---|---|---|
| 1 | prune | changelog | — | skill-form-rule（重寫） | 刪 Rule 3 並重新編號 | S5 |
| 2 | script | commit-reader | Phase 1 第 1 步 | skill-derive-script | git_log.py 改以 --since / --until 取區間 | S6 |
