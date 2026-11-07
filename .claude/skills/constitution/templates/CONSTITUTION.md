# 憲法

- 憲法是最高順位：與 skill 的 `rules/` 衝突時，以憲法為準。
- 憲法只約束產出物的內容，不改變 skill 的流程、`templates/` 與 `scripts/`。
- `skills/<skill>/<產出物>.md`：該產出物的規則；沒有這個檔，就是沒有憲法。
- 每個檔開頭以 `- Applies To：` 寫出約束的檔案路徑，需要時再以 `- 引用：` 列出要一併遵守的 `shared/` 檔；`shared/` 只放跨 skill 共用的規則。
- 規則用 `skill-form-rule` 的 RuleFile 格式；只有用 script 驗證的規則才寫 `- 驗證：script checks/<名稱>.py`（exit 0 通過、1 違反、2 不支援此格式），沒寫的規則逐條自檢。
