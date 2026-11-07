# Rule 1 - 推導而來的實體標明推導來源 [SHOULD]
- Key Entity 或其屬性若是由其他實體推導而來，要在描述中寫明推導自哪個實體的哪個屬性。

## Good Example
- 日期分組寫明由相簿日期的年月推導。

```
- **DateGroup（日期分組）**: 由相簿日期的「年-月」推導出的分組；包含該月份所有相簿及其顯示順序。
```

## Bad Example
- 沒有寫出推導來源，讀者會以為年、月是要另外維護的屬性。

```
- **DateGroup（日期分組）**: 屬性：年、月、所含相簿、顯示順序。
```

# Rule 2 - Key Entity 不寫儲存方式 [SHOULD]
- 描述只寫實體的意義、屬性與關係；要不要存、怎麼存，留給技術設計決定。

## Good Example
- 只寫屬性與關係，沒有談儲存。

```
- **Album（相簿）**: 一組照片的具名容器。屬性：名稱、相簿日期、日期是否為手動設定、…。相簿之間 MUST NOT 存在父子關係。
```

## Bad Example
- 替技術設計決定了儲存方式。

```
- **DateGroup（日期分組）**: 由相簿日期推導，不建資料表，以 SQL GROUP BY 即時計算。
```

# Rule 3 - 功能不涉及任何領域實體時省略 Key Entities [MUST]
- Key Entity 指使用者與需求會提到、會操作的「東西」，不等於資料庫要存的資料。
- 功能沒有任何這類實體時，整個 Key Entities 章節（含標題）省略。

## Good Example
- 純畫面調整的功能沒有領域實體，spec 從需求章節直接接到 Success Criteria。

```
## Success Criteria
```

## Bad Example
- 沒有領域實體，卻仍留下空章節。

```
## Key Entities

（無）
```
