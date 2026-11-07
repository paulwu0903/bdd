---
name: skill-engineering
description: 要從零建立新 skill，或要把既有 skill（含非模組化的舊 skill）改寫、優化成 SOP + rules/ + templates/ + scripts/ 的模組化結構時，必須使用此 skill。它只編排 skill-form-* 與 skill-derive-*，不自行撰寫部件。
compatibility: Requires Python >=3.11 and uv
---

# SOP

## Phase 1 -- 回推根因（優化既有模組化 skill 時；新建或改寫則略過，目標 SKILL.md 無 Phase 與步驟者一律視為改寫）
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/analyze_skill_references.py --skill <目標 skill 目錄> [--skill <對話中出現的其他 skill 目錄> ...]`，取得涉事 skill 鏈、各 skill 的步驟與部件指向、孤兒與缺失檔案的盤點。
2. READ 讀取使用者描述的問題與發生問題的對話，依盤點結果讀取演練會經過的 skill 與部件；無具體失敗案例時改讀使用者的要求與目標 skill 的全部部件。
3. THINK 依 `rules/根因-規範.md` 寫出預期結果，以實際輸入演練整條鏈，定出落差的根因；無具體失敗案例時預期取自使用者的要求與目標 skill 自身的規範，改以假想輸入演練。
4. WRITE 複製 `templates/gap-analysis.md` 並參照 `templates/gap-analysis.example.md` 改寫填位符號，寫入 `.claude/proposals/<skill 名稱>/gap-analysis.md` 並在對話中向使用者提出根因分析；未獲明確確認前停止，不進入編排。

## Phase 2 -- 盤點來源
1. READ 為每一句可能成為步驟、判斷、格式或機械動作的原文編上來源編號；新建取自使用者的需求描述與對話，改寫取自舊 SKILL.md 全文與對話，優化只取根因範圍內、被改寫步驟點名與新增的來源，其餘部件以一列「原樣保留」概括。

## Phase 3 -- 起草脊椎
1. THINK 依 `rules/Frontmatter-規範.md` 定出目標 skill 的 frontmatter，並以來源清單起草 SOP。

## Phase 4 -- 編排提案
1. THINK 依 `rules/編排-規範.md` 判定每一步與剩餘來源的去向，排成施工表。
2. WRITE 複製 `templates/derivation-plan.md` 並參照 `templates/derivation-plan.example.md` 改寫填位符號，寫入 `.claude/proposals/<skill 名稱>/derivation-plan.md` 並在對話中向使用者提出編排提案；未獲明確確認前停止，不改任何 skill 檔案。

## Phase 5 -- 按表施工
1. WRITE 依編排提案中已確認的預覽寫入目標 skill 的 frontmatter；與現有相同則不改。
2. DELEGATE 預覽與目標 skill 現有 SOP 不同時，交給 skill-form-sop 依已確認的預覽寫入 SOP section。
3. DELEGATE 依施工表逐列、依 pass 順序交給該列的 Deriver（skill-derive-script、skill-derive-rule、skill-derive-template 或 skill-form-rule），以該列的目標步驟、萃取內容與來源作為其使用者指定步驟與補充。

## Phase 6 -- 整體回檢
1. DELEGATE 以 uv run 執行 `${CLAUDE_SKILL_DIR}/scripts/skill_lint.py --skill <目標 skill 目錄>`，取得格式與指向的違規清單；有違規即修正後重跑。
2. READ 比對施工後的目標 skill 全部部件與已確認的編排提案，確認每個來源都已落地、沒有來源之外的新增內容。
3. DELEGATE 優化時以子代理用施工後的 skill 重跑原問題的輸入，比對產出與預期確認落差已消失；原輸入無法重現則改以 THINK 演練；新建或改寫則略過。
