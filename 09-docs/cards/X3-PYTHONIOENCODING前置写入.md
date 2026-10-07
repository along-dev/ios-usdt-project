---
id: X3
mode: 实施
wave: X
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R1
定档理由: |
  ★ 方案 `:262` **自己给出档位：`X3 [R1]`**（`PYTHONIOENCODING` 前置写入规则）。
  ★ 改动限于 `_fix_work/` 下的判据脚本（**不触产物**）⇒ R1。
  门禁强度自知：判据须【真跑一个未设编码的脚本】证明其**不再崩**。
来源: `完整版本开发方案_终版.md:262`（X3）
      + `开发规则与调度说明.md:247`（**P-10 已有规则，但未机械化**）
      + ★ 调度实测：**52 个判据脚本中 47 个未提及 `PYTHONIOENCODING`**
base:
  - path: 09-docs\reports\开发规则与调度说明.md
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
allowed_paths:
  - E:\ios漏洞\_integration\_fix_work\verify_*.py（★ 批量加前置编码设置）
  - E:\ios漏洞\_integration\_fix_work\_py_header.txt（★ 新：统一头部模板）
  - E:\ios漏洞\_integration\_fix_work\verify_x3_encoding.py（★ 本卡判据）
  - 09-docs\reports\开发规则与调度说明.md（★ P-10 补落实说明）
forbidden_paths:
  - "★ 全部产物代码（01-backend-go/**、02-backend-node/**、03-web-admin/**、04-landing/**、05-ios/**、06-android/**）"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_x3_encoding.py    # 动前红 / 动后绿
packages: {}
---

# X3 [R1] `PYTHONIOENCODING` 前置写入规则（把 P-10 机械化）

## ★ 现状（调度实测）

| 项 | 值 |
|---|---|
| `_fix_work/verify_*.py` 总数 | **52** |
| **未提及 `PYTHONIOENCODING`** | **47** |
| 规则手册 | ✅ **P-10 已有**（`开发规则与调度说明.md:247`） |

**P-10 原文**：
> 默认 **GBK** 下，判据里的 `✓`/`✗`（`\u2713`）**打印即崩**：
> `UnicodeEncodeError: 'gbk' codec can't encode character '\u2713'`

**⇒ 目前只能靠**调用方**记得设 `$env:PYTHONIOENCODING='utf-8'`（**易漏**）。**

## ★ 规格：**在脚本内部前置设置**，不依赖调用方

### (a) 每个 `verify_*.py` 的头部加统一前置

**在所有 import 之前**（**必须在任何 print 之前**）：

```python
# -*- coding: utf-8 -*-
"""..."""
import os
import sys

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
```

★ **关键点**：
1. **`os.environ.setdefault`** —— 不覆盖调用方已设的值
2. **`sys.stdout.reconfigure`** —— **仅设环境变量不够**（Python 启动时已锁定 stdout 编码）
3. **`try/except`** —— 兼容旧版 Python

### (b) 统一头部模板

**新建** `_fix_work/_py_header.txt`，内容是上述片段，
供后续新脚本**直接复制**（**防再次遗漏**）。

### (c) `开发规则与调度说明.md` 的 P-10 补落实说明

在 P-10 后补一句：
> ★ **X3 起**：判据脚本**自带**该设置（`os.environ.setdefault` + `sys.stdout.reconfigure`），
> **不再依赖调用方**。新脚本须复制 `_fix_work/_py_header.txt` 的头部。

## ★★ 判据要求

| # | 断言 |
|---|---|
| **N1** | ★ **`verify_*.py` 中未设编码的脚本数 ≤ 阈值**（建议 ≤ 5，含本卡判据自身） |
| **N2** | ★ **`_py_header.txt` 存在且含 `reconfigure`** |
| **N3** | ★ **真跑验证**：选一个**原本含 `✓`/`✗` 且未设编码**的脚本，在**不设 `PYTHONIOENCODING`** 的环境下跑 ⇒ **不崩**（EXIT 正常） |
| **N4** | 规则手册的 P-10 已补落实说明 |
| **N5** | ★ **未改任何产物代码**（`01`–`06` 目录未被触） |
| **N6** | `_manifest.sha256`、`contracts.md` 未改 |

★ **N3 是本卡核心** —— **必须真跑，证明"不依赖调用方"**。
★ **N1 是覆盖面**（从 47 降到 ≤5）。

## ★ 注意事项

1. **不得改动脚本的业务逻辑**（只加头部）
2. **不得删改已有的 `# -*- coding: utf-8 -*-`**
3. **若某脚本已被 `verify_*.py` 之外的东西 import** ⇒ 加头部**不影响**（只是多设了环境变量）
4. ★ **批量修改后**，须**抽样真跑**若干脚本，确认**未被改坏**

## 不在范围

- 不改任何**产物**代码
- 不改判据的**业务逻辑**（只加头部）
- 不改 `contracts.md`

## 证据要求

- 判据动前红 / 动后绿两次真实退出码
- ★ **改造前后的"未设编码脚本数"**（47 → ?）
- ★ **N3 的真跑输出**（**不设 `PYTHONIOENCODING`** 的环境下，脚本正常完成）
- ★ **抽样回归**：至少 3 个改造后的脚本真跑通过
- ★ 声明：**未改任何产物代码**

## 停靠点

1. ★ **若某脚本的 `reconfigure` 与其他逻辑冲突** ⇒ 记录并跳过该脚本
2. ★ **若改造导致某脚本行为变化** ⇒ **停下升级**
3. 若发现**其他语言**（PS/Go）也有同类编码问题 ⇒ 登记（不在本卡范围）
