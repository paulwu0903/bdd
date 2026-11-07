# Rule 1 - 只以 PEP 723 區塊宣告 [MUST]
- 相依只寫在 script 檔頭的 `# /// script` 區塊；skill 目錄內不得出現 requirements.txt、pyproject.toml 或任何 venv。

## Good Example
- 相依隨 script 走，`uv run` 直接讀取。

```
scripts/yaml_to_json.py        # 檔頭區塊內 dependencies = ["pyyaml>=6,<7"]
```

## Bad Example
- 相依寫在另一個檔，`uv run` 不會讀，script 與宣告也會各自漂移。

```
scripts/yaml_to_json.py
scripts/requirements.txt       # pyyaml
```

# Rule 2 - 必填欄位 [MUST]
- 區塊內必有 `requires-python = ">=3.11"` 與 `dependencies`；沒有第三方相依時寫 `dependencies = []`，不省略。

## Good Example
- 無第三方相依仍寫出空的 `dependencies`。

```
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
```

## Bad Example
- Python 下限低於 3.11 時守衛用的 `tomllib` 不存在；缺 `dependencies` 欄位 uv 會報錯。

```
# /// script
# requires-python = ">=3.8"
# ///
```

# Rule 3 - 每個相依給版本範圍 [SHOULD]
- 每個 dependency specifier 都帶版本範圍，不寫裸套件名，讓不同機器、不同時間解析到相近版本。

## Good Example
- 兩個相依都有上下界。

```
# dependencies = ["pyyaml>=6,<7", "orjson>=3,<4"]
```

## Bad Example
- 裸套件名，一年後解析到的大版本可能已不相容。

```
# dependencies = ["pyyaml", "orjson"]
```

# Rule 4 - 守衛涵蓋全部第三方模組 [MUST]
- `_require(...)` 列出 script 會 import 的每一個第三方模組名（import 名，不是套件名）。
- 區塊內每個套件都要對應到至少一個被 `_require` 的模組，反之亦然。

## Good Example
- `pyyaml` 套件對應 `yaml` 模組，`orjson` 同名，兩者都列。

```
# dependencies = ["pyyaml>=6,<7", "orjson>=3,<4"]
_require("yaml", "orjson")
```

## Bad Example
- 寫成套件名 `pyyaml` 永遠 ImportError；`orjson` 漏列，缺它時守衛不會攔。

```
# dependencies = ["pyyaml>=6,<7", "orjson>=3,<4"]
_require("pyyaml")
```

# Rule 5 - 鎖定版本 [MAY]
- 需要跨時間可重現時，可用 `uv lock --script <script>` 產生同名 `.lock`，或在區塊內加 `[tool.uv] exclude-newer`。

## Good Example
- 用 `exclude-newer` 鎖住解析時間點，各平台仍可各取可用 wheel。

```
# [tool.uv]
# exclude-newer = "2026-10-21T00:00:00Z"
```

## Bad Example
- 在 `dependencies` 以 `==` 釘死單一版本，某平台沒有該版 wheel 時整支 script 跑不起來。

```
# dependencies = ["pyyaml==6.0.1"]
```
