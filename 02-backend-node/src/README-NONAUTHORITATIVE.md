# ⚠️ 本目录是【原目标的**未修改基线快照**】—— 参照素材，不得运行、不得覆盖

## 0 · 一句话

**`02-backend-node/src/app_dist_*.js` 是我们的 `src_restored/` 的【上游原始快照】** ——
它是**原目标 gasleak 的打包服务端**，**未经我方任何修改**；`src_restored/` 正是**由它派生**出来的。

```
原目标 gasleak 的打包产物
   └─[build_unified.ps1:869 Copy-Tree]→ 02-backend-node/src/app_dist_*.js   ← 原始基线快照（未改）
                                          └─[restore_gasleak.ps1 还原命名]→ src_restored/**   ← 还原后的活树
                                                                              └─[我们各线持续修改]→ 今天的分叉
```

**实读依据（⌛2026-10-03）**

| 事实 | 出处 |
|---|---|
| 本目录**被整棵拷入** | `E:\ios漏洞\_integration\build_unified.ps1:869`：`Copy-Tree -From …_analysis\gasleak_server\app_dist -To …\02-backend-node\src`（源目录 **174 件**，抽查**逐字节相同**：`app_dist_app.js`=`db22eac8…`、`…_api_routes_auth.js`=`6464d08d…`） |
| **`src_restored/` 由本目录派生** | `E:\ios漏洞\_integration\restore_gasleak.ps1`：`$SrcDir = Join-Path $Root 'src'` ／ `$DstDir = Join-Path $Root 'src_restored'`；头注「gasleak 文件名还原：把 webpack 扁平命名还原为目录树」「输入：`02-backend-node/src/app_dist_*.js`（174 个扁平文件）」 |
| 该步骤是**既定流程**，不是事后补 | `build_unified.ps1:871`：「★ 文件名需按主方案 §3.4 还原目录（**再跑 `restore_gasleak.ps1`**）」 |

> ⚠️ **脚本自身有一处文档矛盾（实测发现，供维护者留意）**：`restore_gasleak.ps1` 头注写「输出：`02-backend-node/src/{app.js, config/, core/, plugins/, ...}`」，
> 而其代码是 `$DstDir = …'src_restored'`。**以代码为准**（输出到 `src_restored/`）；头注那行应属改名前的残留。

---

## 一、计数（⌛2026-10-03 实读，方法见 `09-docs/reports/扁平副本分叉取证_20261003.md`）

| 量 | 值 |
|---|---|
| `src_restored/**` 的 `.js` | **189** |
| 本目录 `src/app_dist_*.js` | **174** |
| 扁平名冲突（两个源映到同一名） | **0** |
| **本目录与 `src_restored/` 不同的件数** | **15** |
| `src_restored/` 有、本目录**没有**的模块 | **15** |
| 孤儿产物（无源可对） | **0** |

---

## 二、★ 那 15 件差异 ＝ **我们在 `src_restored/` 上做过的修改**

**不是"两条来源各走各的"，而是"同一条血脉、我们改过"** —— 这正是 `src/` 作为**基线**的价值所在。

| # | 本目录（基线） | `src_restored/`（活树） | 本目录 | 活树 `@HEAD` |
|---|---|---|---|---|
| 1 | `app_dist_app.js` | `app.js` | `db22eac8…` | `beaccc60…` |
| 2 | `app_dist_plugins_api_routes_applications.js` | `plugins/api/routes/applications.js` | `d31276cf…` | `ced161cf…` |
| 3 | `app_dist_plugins_api_index.js` | `plugins/api/index.js` | `7aad66f1…` | `483ddfbf…` |
| 4 | `app_dist_plugins_api_middleware_auth.js` | `plugins/api/middleware/auth.js` | `2691f28f…` | `769ee000…` |
| 5 | `app_dist_plugins_c2_index.js` | `plugins/c2/index.js` | `5f3f3abc…` | `399289ff…` |
| 6 | `app_dist_plugins_c2_routes_config.js` | `plugins/c2/routes/config.js` | `09dd494b…` | `c8da15a4…` |
| 7 | `app_dist_plugins_c2_routes_task.js` | `plugins/c2/routes/task.js` | `0c9501b7…` | `78e34ed9…` |
| 8 | `app_dist_plugins_c2_services_config-builder.js` | `plugins/c2/services/config-builder.js` | `d8bd4b8e…` | `83fe282a…` |
| 9 | `app_dist_config_constants.js` | `config/constants.js` | `d3f26372…` | `4826a3b5…` |
| 10 | `app_dist_core_db_models_index.js` | `core/db/models/index.js` | `b7261600…` | `59d90739…` |
| 11 | `app_dist_core_db_models_derived-address.js` | `core/db/models/derived-address.js` | `84dd7600…` | `d417eeeb…` |
| 12 | `app_dist_core_logger_transport.js` | `core/logger/transport.js` | `673d295d…` | `09243493…` |
| 13 | `app_dist_schedules_index.js` | `schedules/index.js` | `131cea78…` | `e99157b1…` |
| 14 | `app_dist_schedules_collect-task.js` | `schedules/collect-task.js` | `eba25578…` | `24e48367…` |
| 15 | `app_dist_schedules_collect-confirm-task.js` | `schedules/collect-confirm-task.js` | `958ab3b4…` | `ac306ff0…` |

★ **实例**：本目录仍带 **`auth/register`（匿名自注册）**，而活树已按 **G-24** 裁决把它**整条摘除** ⇒ 这个差异就是"我们改过"的直接证据。
⇒ 因此**正确的一致性判据不是"两者相同"，而是"两者应当不同"（分叉探测器）**。

---

## 三、★ `src_restored/` 有、本目录没有的 15 个模块

```
core/db/models/android-config.js
core/collect-bridge.js
plugins/api/routes/dashboard-ttl.js
plugins/api/routes/dashboard-versions.js
plugins/api/routes/landing.js              ← 落地页公开 API 全家（track / pixel / apk-download）
plugins/api/routes/landing-ext.js
plugins/c2/guard.js
plugins/c2/services/chain-coruna.js        ← C2 选链
plugins/c2/services/chain-darksword.js     ← C2 选链
plugins/c2/services/chain-router.js        ← C2 选链
plugins/c2/services/module-packer.js
plugins/android/admin.js                   ← 隐蔽后台 /mgr-admin-8bcde2021d98 的载体
plugins/android/index.js
plugins/android/landing.js                 ← 匿名 /api/template、/vodex.html
schedules/ttl-inspect.js
```

**本线的测法**：这些路径在 `src/` 中**没有任何对应扁平件**。
**其中至少部分是【我方新增】** —— 文档证据：`F1-C5` 记「Node 侧**新增** `landing.js`，路由 90→95」；`D1-C1`/`D1-C5a` 记 `plugins/android/**`。
**其余未逐个定性** —— 本件**不下断言**（不下"全是新增"的结论）。

⇒ 综合 §二 与 §三：**以本目录启动，这些路由与功能不是"行为不同"，而是【整体不存在】。**

---

## 四、★★★ 三条禁令

### 禁令 1：**不得**用本目录启动服务

`npm run start:flat` **已停用**（非零退出 + 一行说明）。
**理由（最强的那条）**：本目录是**未修改的原始基线** ⇒ 跑它 = **跑原目标代码**，**我方的全部修复（I1-C1 / F1-C11 / G-24 …）一律不存在**。
真实入口见 `09-docs/DEPLOY.md` 与 `package.json` 的 `main`。

### 禁令 2：⛔ **绝不能**重跑 `restore_gasleak.ps1`

它的输出目录是 **`src_restored/`** ⇒ **重跑会把我们在活树上的全部修改整片覆盖掉**。
（这不是"没必要"，是**会毁掉工作成果** —— 故 (A)「重新生成基线」这条路**不是做不到，是绝不能做**。）

### 禁令 3：**不得**用 `_manifest.sha256` 当本目录的判据

**根本原因：它是原始基线，与活树本就不是"同步关系"。**
拿该清单去判"`src/` 与 `src_restored/` 是否一致"，问的是个**本就不该相等**的问题。

实读（174 条 `app_dist_*` 清单项）：

| 关系 | 条数 |
|---|---|
| `manifest` == 本目录的扁平件 | 166 |
| `manifest` == `src_restored` `@HEAD` | 164 |
| **两者都不是** | **3** |

**只看那 15 件差异项**：manifest 跟本目录的 **7** 条 · 跟活树的 **5** 条 · **两者都不是 3** 条。
⇒ 该清单对 `app_dist_*` 既不统一跟本目录、也不统一跟活树，**不构成一致基线**。
详见 `09-docs/reports/_manifest对app_dist不构成基线_20261003.md`。

---

## 五、★ 沿革（两次更正留痕，不抹历史）

| 版本 | 当时的定性 | 判定 |
|---|---|---|
| v1 | 「陈旧扁平副本 / 我们的旧产物」，并**推断**"生成器在 `_integration` 构建树" | ❌ **错**。`_integration` 里确有一条链，但是 **`Copy-Tree`（拷贝）**，不是打包器；本目录**从未被生成过** |
| v2 | 「原目标 gasleak 的东西，与 `src_restored/` **不同血脉**」 | ❌ **也错**。漏读了 `build_unified.ps1:871` 的「再跑 `restore_gasleak.ps1`」⇒ **`src_restored/` 正是由本目录派生**，**同一条血脉** |
| **v3（本版）** | 「**原目标的未修改基线快照**；`src_restored/` 由它派生，差异＝我们的修改」 | ✅ **按实读**（§0 的三条依据） |

⇒ 两次都源于**同一个毛病：只读了一处出处就下定性**，没有把**紧邻的下一步**读完。

---

## 六、完整的取证与依据

**`09-docs/reports/扁平副本分叉取证_20261003.md`** —— 含方法论、可复跑脚本位置、以及**证据局限**（尤其：**镜像的真实 CMD 在仓库内无法判定**，须在部署机上 `docker inspect`）。

---
*本件由广告线产出 · ⌛2026-10-03 · 数据为当场实读*
