---
id: D1-C1b
mode: 实施
wave: D1
depends: [D1-C1, D1-C5a]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  ★★ **命中真高危（权限）**：
    缺陷是「管理台侧端点 `${ADMIN}/api/*` **完全无鉴权**」——
    任何人可读写 theme / pixel / template / download-mode / apk-url，
    且**隐蔽后台入口本身被暴露**。
  ★ 路径清单定「触碰权限 ⇒ 停靠点」；且本项是**已上线缺口的修复** ⇒ **R3**。
  门禁强度自知：**必须有运行时否定断言**（无 token ⇒ 401），
  结构断言无法证明鉴权生效（本轮已实证：结构全绿但端点裸奔）。
来源: ★ **D1-C5a 判据 T1 实测发现**（无 token GET `${ADMIN}/api/theme` => **200**）
      + 对照证据：`/api/users` => **401**（既有端点受保护）
      + `app.js:72-73` 的错误注释（执行者写下不成立的 Fastify 作用域假设）
base:
  - path: 02-backend-node\src_restored\app.js
    sha256: ef51256a467be253ee32d3197a49ca0857f89ef555ac0fc3e6a7edf9817f845c
    bytes: 14456
    eol: LF
  - path: 02-backend-node\src_restored\plugins\android\index.js
    sha256: 由 D1-C5a 产出后由调度重取
    bytes: 由 D1-C5a 产出后由调度重取
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\app.js
  - 02-backend-node\src_restored\plugins\android\index.js
  - 02-backend-node\src_restored\plugins\api\middleware\auth.js（★ 仅当确有必要时）
  - E:\ios漏洞\_integration\_fix_work\verify_d1c1b_admin_auth.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\landing.js（已验收）"
  - "03-web-admin\\static\\**（前端契约来源，只读）"
  - "01-backend-go/**、05-ios/**、06-android/**"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d1c1b_admin_auth.py    # 动前红 / 动后绿
packages: {}
---

# D1-C1b [R1] 更正 `app.js` 中不成立的 Fastify 作用域注释

## ★★ 状态更新（2026-09-30，调度核实后降级）

**原判为 R3 的"管理台端点无鉴权"缺口 —— 已由 D1-C5a 执行者自行修复。**

**实测证据**：
```
/mgr-admin-8bcde2021d98/api/theme     => 401  ✓
/mgr-admin-8bcde2021d98/api/template  => 401  ✓
/api/template                         => 200  ✓（落地页未误伤）
```

**修复方式**（`plugins/android/index.js:16-20`）：
```js
export async function androidPlugin(fastify) {
    await fastify.register(authMiddleware);   // ★ 本 scope 内挂鉴权
    await fastify.register(landingRoute);
    await fastify.register(adminRoute);
}
```
**且其注释（`index.js:3-5`）正确描述了 Fastify 封装边界问题** ✓

## ⇒ 本卡**降级为 R1**：仅剩一处**注释更正**

### 残留问题

`app.js:72-73` 仍有**不成立的说明**：

```
// ★ D1-C1：落地页侧端点（GET /api/template、GET /vodex.html）。
//   ★ 必须在 apiPlugin（内含全局 preHandler 鉴权）之后注册仍然生效 ——
//     fastify 的 preHandler 对同 scope 内全部路由生效，与注册先后无关；
//     这两条路径已在 middleware/auth.js 的 SKIP_AUTH_PATHS 中放行。
await fastify.register(androidPlugin);
```

**该假设不成立**（已被 `index.js:3-5` 的正确说明推翻）：
Fastify 的 `addHook` **只在当前 encapsulation context 内生效**，
`apiPlugin` 与 `androidPlugin` 是**并列 plugin** ⇒ 前者的 `preHandler`
**不覆盖**后者（**与注册顺序无关**）。

**⇒ 须更正该注释**，否则会误导后续维护者（且我本人在写 D1-C1 卡时**就被它误导过**）。

## 规格（本卡唯一改动）

把 `app.js` 该段注释改为**与事实一致**的说明，例如：

```js
// ★ D1-C1/D1-C5a：plugins/android 插件承载【两侧】端点 ——
//   落地页侧（裸 /api/template、/vodex.html，已在 SKIP_AUTH_PATHS 放行）
//   管理台侧（${ADMIN}/api/*，需鉴权）。
//   ★ 注意：Fastify 的 addHook 只在【当前 encapsulation context】内生效，
//     apiPlugin 与 androidPlugin 是【并列】plugin ⇒ apiPlugin 内的
//     authMiddleware 不覆盖 androidPlugin。
//     故 androidPlugin 在【自己的 scope 内】显式再挂一次 authMiddleware
//     （见 plugins/android/index.js）。错误地以为"注册在后即自动受保护"
//     会导致管理台端点裸奔（本卡即由此而来）。
await fastify.register(androidPlugin);
```

★ **执行者可自行措辞**，但须满足：
1. **不得再声称"preHandler 对同 scope 内全部路由生效，与注册先后无关"**；
2. **须说明"androidPlugin 在自己的 scope 内显式挂 authMiddleware"**；
3. 保留对落地页侧已放行白名单的说明。

## 判据要求

| # | 断言 |
|---|---|
| E1 | ★ `app.js` **不再含**不成立的表述（`与注册先后无关` 等） |
| E2 | ★ `app.js` 注释**说明了**"在本 scope 显式挂 authMiddleware" |
| E3 | ★ **无 token `${ADMIN}/api/theme` ⇒ 401**（运行时，保证修复仍生效） |
| E4 | ★ **无 token `/api/template` ⇒ 200**（落地页未误伤） |
| E5 | 守护：`landing.js`、前端、`_manifest.sha256` 未改 |
| E6 | `node --check app.js` 退出码 0 |

## 不在范围

- **不改** `plugins/android/index.js`（它已正确）
- 不改 `middleware/auth.js`、`landing.js`、前端

## 停靠点

1. 若发现**其他 plugin 也有同样缺口** ⇒ 停下升级
2. 若更正后 `node --check` 失败 ⇒ 停下升级

## 缺陷事实（实测确证）

### 现象

| 路径 | 无 token | 应有 |
|---|---|---|
| `/api/users`（既有） | **401** ✓ | 401 |
| **`${ADMIN}/api/theme`** | 🔴 **200** `{"theme":"gold"}` | **401** |
| **`${ADMIN}/api/template`** | 🔴 **200** | **401** |
| `/api/template`（落地页侧） | 200 | 200 ✓（**已白名单，正确**） |

**⇒ `plugins/android/` 的**管理台侧**路由**整体不受鉴权保护**。**

### 根因

```js
// app.js
await fastify.register(apiPlugin);       // :71
await fastify.register(androidPlugin);   // :73  ← 并列 plugin，不同 encapsulation context

// plugins/api/index.js:27 内的
await fastify.register(authMiddleware);  // ← preHandler 只在 apiPlugin context 内生效
```

**Fastify 的 `addHook` 只在【当前 encapsulation context】内生效** ⇒
`androidPlugin` 的路由**不受** `apiMiddleware` 的 `preHandler` 约束。

### ★ 错误的注释（须一并更正）

`app.js:72-73` 现有一段注释：

```
// ★ D1-C1：落地页侧端点（GET /api/template、GET /vodex.html）。
//   ★ 必须在 apiPlugin（内含全局 preHandler 鉴权）之后注册仍然生效 ——
//     fastify 的 preHandler 对同 scope 内全部路由生效，与注册先后无关；
//     这两条路径已在 middleware/auth.js 的 SKIP_AUTH_PATHS 中放行。
```

★ **该假设不成立**（见根因）⇒ **须删除/更正该注释**，否则会误导后续维护者。

## 修复方向（执行者选择并说明理由）

| 方案 | 做法 | 评价 |
|---|---|---|
| **(a)** 在 `androidPlugin` 内 `register(authMiddleware)` | 使其管理台路由受同一 preHandler 保护 | ★ **推荐**（最小改动、复用既有鉴权） |
| **(b)** 把 `androidPlugin` 的管理台路由**移入 `apiPlugin`** | 结构性调整 | 改动面大 |
| **(c)** 在 `androidPlugin` 内**自建鉴权** | 新增一套 | 重复实现，不推荐 |

★ **无论选哪个**，必须满足：
1. **`${ADMIN}/api/*` 无 token ⇒ 401**；
2. **落地页侧 `/api/template`、`/vodex.html` 仍匿名可达 200**（不得误伤）；
3. 其他既有端点的鉴权行为**不变**（`/api/users` 等仍 401）。

★ **注意**：若选 (a) 且 `authMiddleware` 依赖 `decorateRequest`，
须确认**重复 register 同一 plugin 两次**是否合法（Fastify 会报 `already registered`？）
⇒ **执行者须实测确认**；若不允许 ⇒ 改选 (b) 或抽取中间件工厂函数。

## ★ 判据要求（**必须有运行时否定断言**）

| # | 断言 |
|---|---|
| E1 | ★ **无 token GET `${ADMIN}/api/theme` ⇒ 401** |
| E2 | ★ **无 token GET `${ADMIN}/api/template` ⇒ 401** |
| E3 | ★ **无 token POST `${ADMIN}/api/theme` ⇒ 401**（写操作同样受保护） |
| E4 | **带 token ⇒ 200**（不得误伤） |
| E5 | ★ **落地页侧 `/api/template` 无 token ⇒ 200**（不得误伤匿名端点） |
| E6 | ★ **`/vodex.html` 无 token ⇒ 200**（同上） |
| E7 | `/api/users` 无 token ⇒ 401（既有行为不变，防改过头） |
| E8 | ★ `app.js` 中**不成立的注释已被更正**（不得残留错误说明） |
| E9 | 守护：`landing.js`、前端、`_manifest.sha256` 未改 |

★ **E1–E3 是本卡的核心** —— 它们直接证明鉴权生效。
★ **E5/E6 是防改过头** —— 避免"一刀切加鉴权"把落地页端点也封了。

## 不在范围

- 不改前端
- 不改 `landing.js`
- 不新增端点（本卡**只修鉴权**）

## 证据要求

- 判据动前红 / 动后绿两次真实退出码
- `app.js` 与 `plugins/android/index.js` 的改前/改后 sha256
- ★ **E1–E7 的真 HTTP 响应原文**（含状态码）
- ★ 明确说明**所选方案与理由**

## 停靠点

1. 若修复需**改 `middleware/auth.js` 的核心逻辑** ⇒ 停下升级
   （它会同时影响所有既有端点）
2. 若 `authMiddleware` **无法重复 register** ⇒ 停下升级（须换方案）
3. 若修复后**落地页端点被误伤**（`/api/template` 变 401）⇒ 停下升级
4. 若发现**其他 plugin 也有同样缺口** ⇒ 停下升级（范围外但须登记）
