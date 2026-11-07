Feature: {{功能名稱}}
  {{一句功能描述}}

  # 來源：{{acceptance 目錄路徑}} 與 {{spec.md 路徑}}；句型定義見同目錄 dsl.md。

  Background:
    Given {{所有 Example 共用的步驟}}
    And {{所有 Example 共用的 Data Table 步驟}}：
      | {{欄位名稱}} |
      | {{欄位值}} |

  Rule: {{一句可驗證的規則陳述}}

    @ac:{{acceptance 主題}}:{{Journey 序}}-{{檢查點序}}
    Example: {{資料情境名稱}}
      Given {{前置狀態步驟}}
      When {{受測操作步驟}}
      # {{預設參數名稱}}={{業務用語的值}}
      Then {{驗證步驟}}

  Rule: {{一句可驗證的規則陳述}}

    @ac:{{acceptance 主題}}:{{Journey 序}}-{{檢查點序}}
    Scenario Outline: {{含 <參數名稱> 的資料情境名稱}}
      Given {{前置狀態步驟}}
      When {{含 <參數名稱> 的受測操作步驟}}
      Then {{含 <參數名稱> 的驗證步驟}}

      Examples:
        | {{參數名稱}} |
        | {{參數值}} |

  Rule: {{一句可驗證的規則陳述}}

    @ac:{{acceptance 主題}}:{{Journey 序}}-{{檢查點序}} @journey
    Example: {{端點 journey 的資料情境名稱}}
      Given {{前置狀態步驟}}
      When {{第一段受測操作步驟}}
      Then {{第一段驗證步驟}}
      When {{下一段受測操作步驟}}
      Then {{下一段驗證步驟}}
