---
id: D1-C1
mode: 实施
wave: D1
depends: [D1-C0]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  新建 `02-backend-node/src_restored/plugins/android/` —— 属 `02-backend-node/**`
  （路径清单定「至少 R2」，与 `plugins/c2/**` 同类）。
  ★ 不触碰资金路径、不改已验收的 `landing.js`、不改契约 ⇒ 不上 R3。
  门禁强度自知：判据须含【真 HTTP 多例】（200/401/302 覆盖），不得只做结构断言。
  ★★ 本卡规格经【前端源码三级验证】（admin_dashboard.html 的真实 fetch 调用），
     非纸面设计 ⇒ 精度高，但仍须运行时确认。
来源: `09-docs/reports/D1C0-Android端点权威规格.md` §4
      + `09-docs/analysis/双平台整合复刻方案.md:236-264`（含实现代码）
      + `03-web-admin/static/admin_dashboard.html:660,698-1055`（前端硬契约）
      + ★ Owner 裁决 (甲)：**两侧分前缀**
base:
  - path: 02-backend-node\src_restored\app.js
    sha256: 53ca2ad1332a631545c3e8b619775b9144397c3c43e1a4da5e7f3a12160acbf3
    bytes: 14010
    eol: LF
  - path: 02-backend-node\src_restored\plugins\api\middleware\auth.js
    sha256: 834e4772649adacf2e4ce51bc68d8afa3a8a061ba4d0f4808aa28ec077e046f7
    bytes: 4579
    eol: LF
  - path: 03-web-admin\static\admin_dashboard.html
    sha256: 9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5
    bytes: 60126
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\plugins\android\**（★ 新建目录）
  - 02-backend-node\src_restored\app.js
  - 02-backend-node\src_restored\plugins\api\middleware\auth.js
  - E:\ios漏洞\_integration\_fix_work\verify_d1c1_android_landing.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\landing.js（★ 已验收 F1-C5，本卡【不得】改）"
  - "02-backend-node\\src_restored\\plugins\\c2\\**"
  - "03-web-admin\\static\\**（★ 前端只读 —— 它是【契约来源】，不是本卡产物）"
  - "01-backend-go/**、04-landing/**、05-ios/**、06-android/**"
  - "E:\\ios漏洞\\_integration\\build_unified.ps1（单一写者 W1-C1）"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d1c1_android_landing.py    # ①动前：须【红】
  - python _fix_work\verify_d1c1_android_landing.py    # ②动后：须【绿】
  - node --check <每个新增 .js>（逐个）
  - python _fix_work\verify_f1c5_landing_api.mjs       # ★ 全链回归
packages: {}
---

# D1-C1 [R2] 新建 `plugins/android/` + **落地页侧**端点

## 目标

新建 `plugins/android/`，实现 **落地页侧**端点（裸 `/api/` 前缀）。

## ★★★ 本卡最重要的事：**两侧分前缀**（Owner 裁决 甲）

**D1 的端点分两侧，前缀【不同】。** 三级证据：

| 证据源 | 内容 |
|---|---|
| `双平台整合复刻方案.md:235-247` | 注释「**--- 落地页侧 ---**」⇒ 裸 `/api/` |
| `双平台整合复刻方案.md:249-264` | 注释「**--- 管理台侧（沿用 pjuyr 的隐蔽前缀）---**」⇒ `${A}/api/` |
| `admin_dashboard.html:660` | **`const ADMIN = "/mgr-admin-8bcde2021d98";`**（真实文件） |
| `landing.js`（实测） | 裸 `/api/track/*`、`/api/pixel-config`、`/api/apk/download` ✅ |

### 本卡（落地页侧）的端点范围

| # | 方法+路径 | 状态 | 调用方（前端硬证据） |
|---|---|---|---|
| 1 | **`GET /api/template`** | ★ **本卡实现** | `04-landing/runtime/index_root.html:12`（**匿名**） |
| 2 | **`GET /vodex.html`** | ★ **本卡实现** | `index_root.html:16` fallback（**匿名**） |
| — | `GET /api/pixel-config` | ✅ 已存在 | 各落地页 |
| — | `GET /api/apk/download` | ✅ 已存在 | 各落地页 |
| — | `POST /api/track/{start,heartbeat,click}` | ✅ 已存在 | 各落地页 |

★ **`POST /api/template` 【不在本卡】** —— 前端证据显示它**只被管理台调用**
（`admin_dashboard.html:1055` 用 `${ADMIN}/api/template`），
**无任何前端调用裸 `POST /api/template`** ⇒ 归 **D1-C5（管理台侧）**。

★ **`/api/theme`、`/api/pixel`、`/api/stats` 等【不在本卡】** —— 同属管理台侧。

## ★★ 前端硬契约（从真实源码提取 · 已三级验证）

### `GET /api/template`（**裸路径**，`04-landing/runtime/index_root.html:12-16`）

```js
fetch('/api/template').then(r=>r.json()).then(d=>{
  var t = d.template || 'vodex';                    // ★ 响应含 template 字段
  var imported = ['gplayx','lovely','paradx', ... ]; // ★ 40+ 个模板名
  window.location.replace('/' + t + '.html');        // ★ 用模板名拼路径
}).catch(function(){ window.location.replace('/vodex.html'); });
```

**⇒ 契约**：`GET /api/template` 返回 **`{ template: "<name>" }`**
- **不是 302**（我早前卡里写 302 是错的，**已更正**）
- **默认值 `'vodex'`**（前端有 `|| 'vodex'` 兜底）
- ★ **模板名清单**（`index_root.html:14` 列了 **40 个**）：
  `gplayx, lovely, paradx, phubxx, premhd, chatee, secure, reelsh, xvides, dptvlx,`
  `hztvlx, cosply, fizzio, velocx, lustyl, kyssap, promox, reelen, meetic, prtvxx,`
  `shortv, nightm, livesp, vidion, xvidep, cosern, minidr, kuaibo, ultrap, qiyoux,`
  `nightp, soccer, bokepx, apumex, xhamst, japapp, noxxxt, smartr, stkval, igniti`
  ⇒ **成功返回的 `template` 值应在这个集合内**（否则前端会跳 404 页）

### `GET /vodex.html`

返回 `vodex` 模板页（`index_root.html` 的 fallback 目标）。
★ 模板文件**实测存在**：`E:\USDT项目\04-landing\templates\vodex.html`（**31,008 B**）。
★ **读取路径须执行者确认**（见停靠点 3）。

## ★ 两个已查实的陷阱

### 陷阱 1：`SKIP_AUTH_PATHS` 是唯一放行机制

`plugins/api/middleware/auth.js`：

```js
const SKIP_AUTH_PATHS = [...];                    // ★ 数组
fastify.addHook('preHandler', async (request, reply) => {   // ★ 全局
    const urlPath = request.url.split('?')[0];    // ★ 整路径比较
    if (SKIP_AUTH_PATHS.includes(urlPath)) return;
    ...
    reply.code(401).send({ error: '未授权' });
```

**⇒ 不在白名单的端点一律 401**（`landing.js:14-16` 原话："路由写了也等于没写"）。

### ★ 陷阱 2：`/vodex.html` **非 `/api/` 前缀，同样会被 401**

中间件按 `request.url` **整路径**比较 ⇒ **`/vodex.html` 若需匿名可达，必须加入白名单**。

★ **执行者须先实读 `auth.js` 确认**，不得假定"非 `/api/` 就免检"。

## 规格

### (a) 新建 `plugins/android/index.js`

参照 `plugins/c2/index.js:15` 与 `plugins/api/index.js:26` 的写法：

```js
import { landingRoute } from './landing.js';
export async function androidPlugin(fastify) {
    await fastify.register(landingRoute);
}
```

### (b) 新建 `plugins/android/landing.js`

实现 `GET/POST /api/template` + `GET /vodex.html`。

**模板名的存储**：★ **须先实读 `04-landing/templates/` 下有哪些模板**
（实测至少含 `vodex.html`、`index.html`），再决定：
- 用**环境变量**（如 `LANDING_TEMPLATE`，默认 `vodex`）？
- 还是用**配置文件/DB**？

★ **若无法确定** ⇒ 停下升级（停靠点 1）。

### (c) 注册到 `app.js`

在 `app.js` 的插件注册区加入 `androidPlugin`（★ **先实读 `:47-75` 既有写法**）。

### (d) 更新 `SKIP_AUTH_PATHS`

把**需匿名可达**的端点加入白名单。
★ **执行者须逐条判断并说明理由**：
- `GET /api/template`：落地页（`index_root.html`）**匿名调用** ⇒ **须匿名** ✓
- `GET /vodex.html`：设备访客访问 ⇒ **须匿名** ✓
- `POST /api/template`：管理台调用（`admin_dashboard.html`，**带 ADMIN 前缀**）
  ⇒ ⚠️ **注意：前端用的是 `${ADMIN}/api/template`，而本卡实现的是裸 `/api/template`**
  ⇒ **须确认两者关系**（见停靠点 4）

## ★ 判据（先写、先跑到红）

`verify_d1c1_android_landing.py`：

| # | 断言 | 红态 |
|---|---|---|
| A1 | `plugins/android/index.js` 与 `landing.js` 存在 | 缺 ⇒ 红 |
| A2 | `GET /api/template` 在 `plugins/android/**` 中注册 | 缺 ⇒ 红 |
| A3 | `POST /api/template` 已注册 | 缺 ⇒ 红 |
| A4 | `GET /vodex.html` 已注册 | 缺 ⇒ 红 |
| A5 | `app.js` 挂载 `androidPlugin` | 缺 ⇒ 红 |
| A6 | `SKIP_AUTH_PATHS` 含 `/api/template` 与 `/vodex.html` | 缺 ⇒ 红 |
| A7 | ★ **未新增 `/api/track/*` 注册**（复用已裁） | 有 ⇒ 红 |
| A8 | ★ **未新增 `/api/pixel-config`、`/api/apk/download` 注册**（已存在） | 有 ⇒ 红 |
| A9 | ★ `landing.js` **sha256 与 base 一致**（未改） | 变 ⇒ 红 |
| A10 | ★ `admin_dashboard.html` **sha256 与 base 一致**（前端只读） | 变 ⇒ 红 |
| A11 | 防越界：`contracts.md`、`_manifest.sha256` 未改 | 变 ⇒ 红 |

**★ 真 HTTP 断言（R2 要求）**：

| 例 | 请求 | 期望 |
|---|---|---|
| H1 | `GET /api/template` | **200**，body 含 `template` 字段 |
| H2 | `GET /vodex.html` | **200**（返回模板内容） |
| H3 | `GET /api/theme`（**未实现**，且在 A 前缀） | **401**（证明白名单未误开） |
| H4 | `POST /api/track/start` | **仍走既有实现**（复用生效） |
| H5 | ★ `GET /api/template` 的响应体**与 `admin_dashboard.html` 期望的形态一致** | 含 `template` |

## 不在范围

- 不改 `landing.js`（已验收）
- 不实现管理台侧（`${A}/api/*`）—— 属 D1-C4/C5
- 不实现 `/login`（Owner 裁 2a）
- 不实现安全扫描路径
- 不改前端（`03-web-admin/static/**` **是契约来源，只读**）

## 证据要求

- 判据改前红 / 改后绿两次真实退出码
- 新增文件 sha256 与 bytes
- `node --check` 每个新增 `.js`
- **H1–H5 的真 HTTP 响应原文**
- `verify_f1c5_landing_api.mjs` 退出码（全链回归）
- ★ 声明：**未改 `landing.js` / 未改前端**

## 停靠点

1. **模板名的存储方式**无法确定 ⇒ 停下升级
2. 若 `POST /api/template` 的 body/响应形态**无法从前端确认** ⇒ 停下升级
3. `vodex.html` 的运行时读取路径无法确定 ⇒ 停下升级
4. ★ **若"裸 `/api/template`"与"`${ADMIN}/api/template`"的关系不明** ⇒ 停下升级
   （前端两处都用，但前缀不同 ⇒ 可能需**两条路由**或**一条 + 前端改动**）
5. 若需改 `landing.js` 或前端 ⇒ **停下升级**
