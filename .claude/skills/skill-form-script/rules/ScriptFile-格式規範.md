# Rule 1 - 單檔自足 [MUST]
- 一支 script 就是一個 `.py` 檔，所需邏輯都在檔內，不 import 同目錄的其他模組，也不依賴套件以外的本地檔案。
- 判準：把這個檔單獨複製到任何目錄，`uv run` 仍能執行。

## Good Example
- 守衛與邏輯都在同一檔，單獨複製即可執行。

```
scripts/yaml_to_json.py        # 自帶 PEP 723 區塊與守衛
```

## Bad Example
- 守衛抽到共用模組，單獨複製 `yaml_to_json.py` 就找不到 `_common`。

```
scripts/yaml_to_json.py        # from _common import require
scripts/_common.py
```

# Rule 2 - 檔頭順序 [MUST]
- 檔案由上而下固定為：PEP 723 區塊、module docstring（用途與 `uv run` 用法）、stdlib import、守衛函式、守衛呼叫、第三方 import、其餘程式。
- 第三方 import 一律放在守衛呼叫之後，否則守衛來不及攔截 ImportError。

## Good Example
- 第三方 `yaml` 在 `_require("yaml")` 之後才 import。

```python
import sys
import tomllib
from pathlib import Path

_require("yaml")

import yaml  # noqa: E402
```

## Bad Example
- `yaml` 在守衛之前就 import，缺套件時直接 Traceback，守衛形同虛設。

```python
import sys
import yaml

_require("yaml")
```

# Rule 3 - CLI 契約 [MUST]
- 參數一律由 argparse 接收，不讀互動輸入。
- 結果寫 stdout，診斷與錯誤寫 stderr；成功 exit 0，失敗 exit 非零。

## Good Example
- 參數走 argparse，結果走 stdout，錯誤走 stderr 並回非零。

```python
parser.add_argument("source", help="Path to the YAML file")
if not source.is_file():
    sys.stderr.write(f"error: '{source}' is not a file\n")
    return 2
sys.stdout.write(orjson.dumps(data).decode() + "\n")
return 0
```

## Bad Example
- 互動輸入會讓執行的 AI 卡住；錯誤混進 stdout 且照常 exit 0，呼叫端無法分辨成敗。

```python
path = input("YAML path: ")
print("error: file not found")
return 0
```

# Rule 4 - 跨平台 [MUST]
- 路徑用 pathlib，文字 I/O 明寫 `encoding="utf-8"`，不用 `shell=True` 呼叫 OS 專屬指令，不寫死 `python` / `python3` 直譯器名。

## Good Example
- pathlib 讀檔並明寫編碼；子程序用 `sys.executable`。

```python
text = Path(args.source).read_text(encoding="utf-8")
subprocess.run([sys.executable, "-m", "pip", "--version"], check=True)
```

## Bad Example
- 不寫編碼在 Windows 預設 cp950 下遇非 ASCII 即炸；`ls` 與 `grep` 在 Windows 不存在；Windows 多半沒有 `python3`。

```python
text = open(args.source).read()
subprocess.run("ls -la | grep yml", shell=True)
subprocess.run(["python3", "other.py"])
```

# Rule 5 - 錯誤訊息指出修法 [SHOULD]
- 可預期的失敗（檔案不存在、格式錯誤、參數不合）由 script 自己攔截，訊息寫明是什麼錯與下一步怎麼做，不把 Traceback 丟給執行者推理。

## Good Example
- 一行說清楚錯在哪、怎麼修。

```
error: 'specs/plan' does not exist; create it or pass --root <dir>
```

## Bad Example
- 同一個錯誤直接讓例外冒出，執行者得自己讀 Traceback 推理。

```
Traceback (most recent call last):
  ...
FileNotFoundError: [Errno 2] No such file or directory: 'specs/plan'
```

# Rule 6 - 單一自動化目的 [MUST]
- 一支 script 只做一件事，docstring 第一句一句話就能說完它的目的。
- 不用子指令或模式參數把多個不相干的功能綁在同一支 script；多個目的就拆成多支。

## Good Example
- 兩個目的各自一支，步驟點名時一看就知道拿到什麼。

```
scripts/next_plan_dir.py      # 算下一個 NN
scripts/yaml_to_json.py       # YAML 轉 JSON
```

## Bad Example
- 一支 script 用 `--mode` 切換三種不相干的事，docstring 一句話說不完。

```
scripts/plan_tools.py --mode next-nn
scripts/plan_tools.py --mode yaml2json
scripts/plan_tools.py --mode validate
```
