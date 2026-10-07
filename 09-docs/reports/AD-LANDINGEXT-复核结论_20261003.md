# AD-LANDINGEXT — 终端 B 三条匿名端点（`landing-ext.js`）复核结论

> **卡**：复核并验证终端 B 的 `landing-ext.js`（先取证，**不落码**）
> **执行**：广告线 `local_9d5c6899-a95a-421a-8d9b-26f485cd5ea6` · ⌛2026-10-03
> **边界**：**未改 B 的 `landing-ext.js`**；本件只读＋实跑探针。写范围仅 `09-docs/reports/**`。
> **方法**：静态实读（`file:line` 级）＋ 在 **3001 隔离实例**上跑真实探针（脚本在仓库外 `X:\_integration\_fix_work\_ad_landingext_probe.mjs`）。**结论均有当场读数，未采信任何转述。**

---

## 0 · 结论摘要

| 面 | 结论 | 定级 |
|---|---|---|
| 动作① **字段/语义是否对得上** | `/api/settings` **对得上**（逐条实证）；**但 `/api/track` 对不上** —— 模板**从不发 `sid`** ⇒ 该端点对**唯一真实调用方一条都不写** | ★ **P1（功能空转）** |
| 动作② **接线完整性** | **完整**：`import`（`plugins/api/index.js:31`）＋ `register`（`:68`）**都在** | ✅ PASS |
| 风险① **`/api/settings` 泄露** | **未泄露**结算地址/密钥/渠道内参（敏感词 **0 命中**）；但 `download.*` 是**匿名可枚举的载荷 URL 下发点**（本 env 为空），请裁量 | ⚠️ **P3（需裁量）** |
| 风险② **`/api/stats` 与管理台串味** | **确实串味**：匿名 `total`/`clicks` 与管理台**逐值相同**；且 **B 的注释与代码不符**；另有"匿名端点把整集合读进内存"的可放大性 | ★ **P2** |
| 风险③ **`/api/track` 冲突** | 与既有三条子路由**无冲突**；但它是**新增匿名写入点**（可被刷量注水），且注水结果**可被匿名读到**（与风险②叠加） | ★ **P2** |

**⇒ 一句话**：**接线没问题、`settings` 形状也对**；问题集中在 **`track` 的契约不匹配（P1）** 与 **匿名 stats 的两处（值暴露 + 可放大）**。

---

## 1 · 动作面

### 1.1 `/api/settings` —— 字段对得上（实证）

B 的三处契约引用，**逐字核对成立**（`04-landing/assets/landing-pages__prtvxx__static__js__main.js`，共 290 行）：

| B 的引用 | 实读原文 | 判定 |
|---|---|---|
| `:282` 读 `data.data`（嵌套） | `if (data && data.data) renderConfig(data.data);` | ✅ |
| `:242` 读 `data.count` | `var count = data && data.count ? data.count : ((settings.socialProof \|\| {}).baseCount \|\| 500000);` | ✅ |
| `:72` fire-and-forget | `fetch("/api/track", {…, keepalive: true }).catch(function () {});` | ✅ |

**消费面逐条对位**（模板读什么 ↔ B 给什么）：

| 模板消费点 | 读的字段 | B 的 `buildLandingSettings()` | 判定 |
|---|---|---|---|
| `applyAccess()` | `access.{allowAndroid,allowIos,allowDesktop,blockInApp,blockedRedirectUrl}` | 全部提供 | ✅ |
| `realDownloadUrl()` | `download.{androidUrl,androidUrl2,androidUrl3,iosUrl,autoUrl}` | 全部提供 | ✅ |
| `applyMaintenance()` | `maintenance.enabled` | 提供 | ✅ |
| `renderConfig()` | `theme.{primary,secondary,accent,background}` · `seo.{title,description}` · `announce.{text,enabled}` · `download.autoDownload.{enabled,delaySeconds}` | 全部提供 | ✅ |
| `loadStats()` | `data.count` | `count` | ✅ |
| `renderCopy/renderImages/renderDynamic/renderContact` | `copy` / `images` / `language` / `contact` | 提供（`copy.es`、`images` 为空对象） | ✅ |

★ 另注：模板对 `/api/settings` 是**增强而非硬依赖**（`:283` 的 `.catch(function () { renderConfig(settings); loadStats(); })` 会回退到内置默认）⇒ 端点挂了不会白屏。

### 1.2 `/api/track` —— **契约对不上**（★ P1）

**模板侧**：`track(type, target, extra)` 组装的 payload 是 `{ type, target, ...extra }`（`main.js:62-63`）。
**全文 `sid` 出现次数 ＝ 0**（`rg -n "sid" main.js` → 无命中）；6 处调用（`:145,146,168,196,254,268`）传的都是 `("click"|"download", "<target>"[, {eventId}])`。

**端点侧**：B 的实现以 `body.sid` 为**写库前提**，缺失即 `return { ok:false, reason:'sid_missing' }`（**不写任何东西**）。

**实测（匿名，用模板真实 payload）**：
```
POST /api/track  {"type":"click","target":"download_android"}
  → HTTP 200  {"ok":false,"reason":"sid_missing"}
  landing_visits: 23 → 23    写入量 = 0
对照：POST /api/track  {"sid":"ad-review-probe-1","type":"click",…}
  → HTTP 200  {"ok":true}    写入量 = 1
```
**⇒ 端点实现是活的，但契约不匹配：对唯一的真实调用方，它一条数据都不写。**
且前端 `fire-and-forget`（不校验响应）⇒ **不报错、不告警、看起来"通了"** —— 正是本项目反复强调的 **P-1 形态**。

---

## 2 · 风险面（逐条结论 + 证据）

### 2.1 风险① `/api/settings` 是否泄露匿名不该看的字段

**结论：未泄露。** 实测（匿名 `GET /api/settings` → HTTP 200）：
- 顶层键 15 组：`download, access, language, copy, images, socialProof, maintenance, contact, footer, brand, theme, seo, announce, postback, _pixelIds`；
- **敏感词扫描 0 命中**（扫 `address/key/secret/token/private/mnemonic/wallet/settlement/channel/packet/agent/password/cookie/jwt` 于整个响应体）。

**为什么**：该端点是**字段白名单**（逐字段从 `LANDING_*` 环境变量取值），**不是配置转储** ⇒ 环境里即便有别的 `LANDING_*` 也不会漏出。

⚠️ **仍要点名一处供裁量**：`download.{androidUrl,androidUrl2,androidUrl3,iosUrl,autoUrl}` 是**载荷投递 URL** —— 匿名访客可从中**枚举到下载目标**。本 env 下为空；但**生产 env 若配置了真实 URL，它就是一个匿名可读的载荷下发点**。（这与落地页"下载按钮必须能用"是同一件事，但**"匿名可枚举"这一点应被显式登记**。）

### 2.2 风险② `/api/stats` 与管理台是否串味 —— **串味**

- **路径不同名**：匿名 `/api/stats` 与 `${ADMIN}/api/stats`（`plugins/android/admin.js:738`，前缀 `/mgr-admin-8bcde2021d98`）**不冲突**。
- **但读同一集合**：两处都调各自的 `landingVisitModel()`，`collection: 'landing_visits'`（`admin.js:143` / `landing-ext.js:181` / `landing.js:56`）。
- **实测逐值比对**（同一次查询）：

| | 匿名 `/api/stats` | 管理台 `/mgr-admin-…/api/stats` |
|---|---|---|
| 响应体 | `{"count":500023,"total":23,"clicks":23}` | `{total, today, clicks, unique_ips, avg_dwell_ms, top_countries, top_devices}` |
| total | **23** | **23** ← **相同** |
| clicks | **23** | **23** ← **相同** |

⇒ **匿名侧确实读到了管理台的两个计数。**

★ **B 的文件注释与代码不符**：`landing-ext.js:162-163` 写「本端点**只回最小信息**（count），不泄露管理台的完整统计面（**total/clicks**/top_countries 等仍只在 `${ADMIN}/api/stats`）」—— **但代码 `:214` 就返回了 `total` 与 `clicks`**。

★ **另一处**：匿名 `/api/stats` 用 `LV.find({}, {sid:1, clicked:1})` **把整个集合读进内存**再在 JS 里 `.length`/`.filter()` 计数；管理台侧用的是 `countDocuments` / `aggregate`（服务端聚合）。⇒ **匿名端点上的无上限内存读**，随 `landing_visits` 增长可被放大。

### 2.3 风险③ `POST /api/track`（裸路径）是否冲突 / 未登记写入点

- **无路由冲突**：`/api/track` 与 `/api/track/{start,heartbeat,click}` 都是**静态段**，find-my-way 精确匹配；注册顺序（`index.js:65` landing → `:68` landing-ext）不影响。**实测三条子路由仍各自 200**：
  ```
  POST /api/track/start      HTTP 200 {"code":0,"data":{"sid":"probe-start"}}
  POST /api/track/heartbeat  HTTP 200 {"code":0,"data":{"sid":"probe-heartbeat"}}
  POST /api/track/click      HTTP 200 {"code":0,"data":{"sid":"probe-click"}}
  ```
- **但确实是新增的匿名写入点**：任意人可对 `landing_visits` 按 `sid` **upsert**（实测带 sid 即写入 1 行）⇒ **可刷量注水**；而注水结果又经风险②的 `total/clicks` **被匿名读回** ⇒ **两个问题叠加**：可匿名刷、且能立刻看到自己刷的读数。
- 与既有 `/api/track/click` 的**语义重叠**：两者都会把 `clicked` 置真（`landing-ext.js:238` 对 `type==='click'|'download'`）。⇒ **同一语义有两条匿名入口**。

---

## 3 · 反向断言（可复跑）

脚本：`X:\_integration\_fix_work\_ad_landingext_probe.mjs`（`AD_PORT=3001`）。

| # | 断言 | 当前读数 | 判定 |
|---|---|---|---|
| A1 | 匿名 `GET /api/settings` 响应体**不得含** `address/key/secret/token/private/mnemonic/wallet/settlement/channel/packet/agent/password/cookie/jwt` | **0 命中** | ✅ **通过** |
| A2 | 匿名 `GET /api/stats` 的 `total`/`clicks` **不得等于**管理台同名值 | **两者都相等**（23/23） | ❌ **不通过** |
| A3 | 匿名 `POST /api/track` 用**模板真实 payload**（`{type,target}`）后，`landing_visits` **应增加** | **写入量 0** | ❌ **不通过** |
| A4 | 既有 `/api/track/{start,heartbeat,click}` **不得**因裸 `/api/track` 注册而失效 | 三条均 200 | ✅ **通过** |

> ★ **A2 的措辞是有意收紧的**：若写成"匿名响应不得等于管理台响应"，会因管理台多 5 个键而**平凡通过**（实测正是如此）—— 那会把真问题藏起来。**判据必须落在同名量上。**

---

## 4 · 证据局限（如实）

1. **本 env 未配置任何 `LANDING_*`** ⇒ 风险① 的"载荷 URL 可枚举"**未在真实取值下验证**（只验证了"无敏感字段"这一条）。
2. **未在浏览器里跑 `prtvxx.html`** ⇒ §1.1 的"字段对得上"是**静态对位**（模板读的字段 ↔ 端点给的字段），**未做端到端渲染验证**。
3. **未做压测** ⇒ §2.2 的"可放大"是从**代码形态**（整集合读入内存）推出的，**未给实测放大倍数**。
4. **`sid` 结论的范围**：只针对 `04-landing/assets/` 的这一份 `main.js`（即 B 引用的那份）。`03-web-admin/static/landing-pages/prtvxx/` 与 `04-landing/reference/**` 另有副本，**未逐份核对是否同版**。

---

## 5 · 待裁（本件不改码）

| 问题 | 可选处置（供裁，非建议） |
|---|---|
| **P1 `track` 契约不匹配** | ① 让端点接受无 sid（按别的键落库，如 sid 缺省时用 `type+target` 记账）；② 或认下"该端点对 prtvxx 无实际作用"，**登记为已知空转**并在 README/清单标注；③ 或与 B 对齐由模板补 sid |
| **P2 匿名 `stats` 值暴露** | ① 只回 `count`（去掉 `total`/`clicks`）并**同步改注释**；② 或用 `countDocuments` 替代整集合读入内存 |
| **P2 匿名写入点可刷量** | ① 加限频（与 `landing.js` 的 `TOUCH_THROTTLE_MS` 同法）；② 或把 `landing-ext` 的 track 与既有 `/api/track/click` **合并语义**，不留两条入口 |
| **P3 载荷 URL 匿名可枚举** | 登记为已知面（或改用短期签名 URL），由总调度定 |

---
*本件由广告线产出 · ⌛2026-10-03 · **未改任何码** · 全部读数为当场实读*
