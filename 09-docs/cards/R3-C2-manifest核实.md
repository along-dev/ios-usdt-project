---
id: R3-C2
mode: 实施
wave: R3
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  ★ 源卡 `R3-C2` **自己给出档位**：
    「触碰跨卡共享文件 `_manifest.sha256` ⇒ 属停靠点类别；
      但本卡只【核实】不重算 ⇒ **R2**」。
  门禁强度自知：**`_manifest.sha256` 只读** ⇒ 本卡**绝不重算**。
来源: ★ **`后续剩余工作策划_卡片化.md:581-630`**（`R3-C2` 完整规格）
      + `L009 §6.2`（前轮自认遗留）
      + ★★ **调度摸底**（见下，**已实测出 48 条不符**）
base:
  - path: _manifest.sha256
    sha256: b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2
    bytes: 133131
    eol: CRLF（1299 行，含 UTF-8 BOM）
allowed_paths:
  - E:\ios漏洞\_integration\_fix_work\verify_manifest_scope.py
forbidden_paths:
  - "_manifest.sha256（★ 本卡只【核实】，不重算 —— 重算须 Owner 授权）"
  - "09-docs\\spec\\contracts.md"
  - "★ 全部产物代码（本卡只读不写）"
verify:
  - python _fix_work\verify_manifest_scope.py    # 须退出码 0
packages: {}
---

# R3-C2 [R2] `_manifest.sha256` 其余 1125 条核实

## ★★★ 调度摸底（**已完成，结果如实**）

### manifest 的实际格式（**关键**）

```
bytes = 133,131  行数 = 1,299  CRLF  含 UTF-8 BOM
格式：<64 位大写 hex><两空格><相对路径>
```

**样例**：
```
00ECF604944545B4E0A1601088D4CEA0EE679D4EAFD951AE12690DE512769099  a159973efdd00dd988fec1d707338545d9487b6a.min.js
0137BA58D53566EBAE40B08A86DB10ABC53A3B56CB01EAEEE832D9A0F20113FC  server_win.go
013F024550E865008E876427D04952F9938C32B7381DBC61661BFACFDEF0DAA6  upload\local.go
015C20B8E118D467D13286140290704445E0350C91ABF04BFAB41059394B766B  landing-pages__dptvlx__static__css__css2.css
```

### ★★★ 路径**无唯一根** —— 规格第 1 条**技术上不可直接实现**

| manifest 条目 | **实际磁盘位置** |
|---|---|
| `a159973e…min.js` | `02-backend-node\templates\exploit\…` **和** `04-landing\ios-templates\exploit\…`（**两个！**）|
| `server_win.go` | `01-backend-go\core\server_win.go` |
| `upload\local.go` | `01-backend-go\utils\upload\local.go` |
| `landing-pages__dptvlx__…css2.css` | `04-landing\assets\…`（**`__` 是路径分隔符的扁平化**）|
| `auto_code.go` | `01-backend-go\config\auto_code.go` |

**⇒ 三个问题**：
1. **同一 basename 可能对应多个文件**
2. **部分路径被扁平化**（`__` 代替 `/`）
3. **相对路径不完整**（`upload\local.go` 缺 `utils/`）

**⇒ 且**路径映射表本身不存在**。**

### ★★ 可替代方案：**按 basename 全树搜索 + 内容比对**

**调度实测结果**（跳过 `node_modules` 等；现树 2,500 文件）：

| 分类 | 数量 |
|---|---|
| **唯一匹配** | **753** |
| ├ **一致** | ✅ **705** |
| └ **★ 不符** | 🔴 **48** |
| **多义（basename 在树中多次出现）** | **546** |
| **现树中缺失** | ✅ **0** |

### ★★ 48 条不符的**归因**（**调度已抽样确认**）

| 归因 | 样本 | 说明 |
|---|---|---|
| **本会话的卡** | `sys_initdb_mysql.go` / `sys_initdb_pgsql.go`（**R2-C4**）、`app\wallet.go`（**D3-C1**）、`trc_test.go` | ✅ **已知改动** |
| **前序会话** | `09-docs/analysis/*.md`（`问题登记册.md`、`需求文档.md`、`审核提示词.md`、`阶段1执行报告.md`、`Filza高版本可用性.md`、`整合复刻方案.md`）| ⚠️ **前序漂移** |
| **`app_dist_*`** | `app_dist_plugins_c2_routes_config.js`、`app_dist_plugins_api_index.js` 等 | ⚠️ |
| **`payloads\manifest.json`** | `05-ios\coruna\payloads\manifest.json` | ⚠️ |

**⇒ 这正是 R3-C2 要查明的，结果**可交付**。**

## ★★ 规格（**基于摸底修正**）

写 `verify_manifest_scope.py`：

1. ★ **按 basename 全树搜索**（**不假设唯一根** —— 因路径无唯一根）
2. **输出四类**（**比卡里的三类多"多义"**）：
   - **一致**
   - **不符**（列出 manifest 值 / 实际值 / 归因）
   - **文件缺失**
   - ★ **多义**（basename 出现多次 ⇒ **SKIP，不判 PASS/FAIL** —— **P-29**）
3. ★ **只报告，不重算**
4. ★ **不把 `_manifest.sha256` 自身纳入比对**（自指）
5. ★ **跳过 `node_modules` / `.git` / `_toolchain` 等**（否则极慢且误报）

### ★ 判据的**预期结果**（**调度摸底值**）

| 项 | 预期 |
|---|---|
| **唯一匹配** | **753** |
| **一致** | **705** |
| **不符** | **48** |
| **多义** | **546** |
| **缺失** | **0** |

★ **执行者须复现这些数字**（若差异大 ⇒ 说明口径不同，须说明）。

## ★★ 判据要求

| # | 断言 |
|---|---|
| **V1** | ★ **四类统计输出存在**（一致/不符/多义/缺失）|
| **V2** | ★ **不符项**逐条**列出**（manifest 值 / 实际值 / 归因）|
| **V3** | ★ **多义项标 SKIP**（**不判 PASS** —— **P-29**） |
| **V4** | ★ **`_manifest.sha256` 未被修改**（sha256 与 base 一致）|
| **V5** | ★ **未改任何产物文件**（只读） |
| **V6** | ★ **脚本自带 `--selftest`**（**P-5**） |
| **V7** | 守护：`contracts.md` 未改 |

★ **V4 是本卡核心** —— **"只核实不重算"的证据**。

## ★ 证据要求

- 脚本**真实退出码**（含 `--selftest`）
- ★ **四类统计**
- ★ **不符项的完整清单**（**48 条**）与**归因**
- ★ **多义项的数量与说明**（546 条）
- ★ **明确声明：本卡未重算 `_manifest.sha256`**
- ★ **V4 的证据**

## 停止点

1. ★★ **若发现大量不符（远超 48）** ⇒ **停下升级**（可能是更大范围漂移）
2. ★★ **若要重算** ⇒ **停下升级**（**触跨卡共享文件，须 Owner 授权**）
3. ★ **若 manifest 格式与摸底不符** ⇒ 停下报告

## ★ 不在范围

- ★ **不重算** `_manifest.sha256`
- **不改** 任何产物
- **不修**任何不符项（**那是各卡的事**）

---

## ★★ 附：本卡的**交付价值**

**它把"1125 条未核实"变成"48 条明确不符 + 546 条多义 + 705 条一致"**
⇒ **这是可行动的结论**（**48 条可归因、可派卡**）。
