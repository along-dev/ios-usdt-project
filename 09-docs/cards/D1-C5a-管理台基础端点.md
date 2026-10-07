---
id: D1-C5a
mode: 实施
wave: D1
depends: [D1-C1]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  在 `plugins/android/` 内新增**管理台侧基础端点** + **全局配置存储模型**。
  属 `02-backend-node/**` ⇒ 至少 R2。
  ★ 不含资金路径、不改契约、不改已验收的 landing.js ⇒ 不上 R3。
  ★ 但它**新建 DB 模型**（`AndroidConfig`）⇒ 属"契约"类（`model/**` 至少 R2）✓ 一致。
  门禁强度自知：判据须含【GET/POST 成对往返】的真 HTTP 断言。
来源: `09-docs/reports/D1-管理台侧端点契约.md`（从前端源码提取的硬契约）
      + `09-docs/analysis/双平台整合复刻方案.md:249-264`
      + Owner 裁决 (甲) 两侧分前缀
base:
  - path: 02-backend-node\src_restored\plugins\android\index.js
    sha256: bb40f95e2dd6f14d326bd0280c4eb94b80d7fce2bfec66bca708d7ec769b594a
    bytes: 867
    eol: LF
  - path: 02-backend-node\src_restored\core\db\models\index.js
    sha256: b726160042d259ebc809aef2f49efbb44830e60477ca645bb130a8ab95d4ce7d
    bytes: 1385
    eol: LF
  - path: 02-backend-node\src_restored\core\db\models\payload-params.js
    sha256: dc370851c633d07349c2a4c4063d674b7281ed52b5a7e5b99d11901b2e335d17
    bytes: 804
    eol: LF
  - path: 03-web-admin\static\admin_dashboard.html
    sha256: 9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5
    bytes: 60126
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\plugins\android\**（在 D1-C1 基础上扩展）
  - 02-backend-node\src_restored\core\db\models\android-config.js（★ 新建）
  - 02-backend-node\src_restored\core\db\models\index.js（仅加一行 export）
  - E:\ios漏洞\_integration\_fix_work\verify_d1c5a_admin_endpoints.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\landing.js（已验收）"
  - "02-backend-node\\src_restored\\core\\db\\models\\payload-params.js（★ 不得复用/修改 —— 它服务 c2 载荷分发）"
  - "03-web-admin\\static\\**（前端是契约来源，只读）"
  - "01-backend-go/**、05-ios/**、06-android/**"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d1c5a_admin_endpoints.py    # ①动前：须【红】
  - python _fix_work\verify_d1c5a_admin_endpoints.py    # ②动后：须【绿】
packages: {}
---

# D1-C5a [R2] 管理台侧**基础端点** + `AndroidConfig` 存储模型

## 目标

在 `${ADMIN}/api/` 前缀下实现**配置类**端点，并新建全局配置存储。

## ★ 前缀（Owner 裁决 甲）

```js
const ADMIN = '/mgr-admin-8bcde2021d98';   // ★ 逐字符保留（硬约束）
```

**本卡实现**（全部挂在 `${ADMIN}/api/` 下）：

| # | 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|---|
| 1 | GET | `${ADMIN}/api/template` | — | `{ template }` |
| 2 | POST | `${ADMIN}/api/template` | `{ template: name }` | `{ ok: true, template }` |
| 3 | GET | `${ADMIN}/api/theme` | — | `{ theme }`（默认 `rose`） |
| 4 | POST | `${ADMIN}/api/theme` | `{ theme: name }` | `{ ok: true, theme }` |
| 5 | GET | `${ADMIN}/api/pixel` | — | `{ pixel_ids: [] }` |
| 6 | POST | `${ADMIN}/api/pixel` | **`{ action: "add"\|"remove", pixel_id }`** | `{ ok: true, pixel_ids }` |
| 7 | GET | `${ADMIN}/api/download-mode` | — | `{ mode }`（默认 `link`） |
| 8 | POST | `${ADMIN}/api/download-mode` | `{ mode }` | `{ ok: true, mode }` |
| 9 | GET | `${ADMIN}/api/apk-url` | — | `{ url }` |
| 10 | POST | `${ADMIN}/api/apk-url` | `{ url }` | `{ ok: true }` / `{ error }` |

★ **契约细节见** `09-docs/reports/D1-管理台侧端点契约.md`（**执行者须先完整读它**）。

## ★★ 关键规格点（前端硬证据）

### theme
- **取值集合**：`{ blue, gold, neon, rose }`
- **默认**：`"rose"`（`:910` `d.theme || "rose"`）

### pixel
- **POST 用 `action` 语义**（**不是整体覆盖**）：
  `{ action: "add" | "remove", pixel_id }`
- **响应**：`{ ok: true, pixel_ids }`

### download-mode
- **取值**：`link` / `upload` / `telegram`（方案 `:1180`）
- **默认**：`"link"`（`:716` `d.mode || "link"`）

### template
- **取值**：40 个模板名（见 `04-landing/runtime/index_root.html:14`）
- **默认**：`"vodex"`

## ★ 存储：新建 `AndroidConfig` 模型

**★ 不得复用 `PayloadParams`** —— 它服务 c2 载荷分发（`config-builder.js` / `task.js` 读它），
复用会**污染载荷分发的配置面**。

**新建 `core/db/models/android-config.js`**，参照 `payload-params.js` 的**单文档模式**：

```js
import mongoose, { Schema } from 'mongoose';
const AndroidConfigSchema = new Schema({
    _id: { type: String, default: 'global' },
    template: { type: String, default: 'vodex' },
    theme: { type: String, default: 'rose' },
    pixelIds: { type: [String], default: [] },
    downloadMode: { type: String, default: 'link' },
    apkUrl: { type: String, default: '' },
    updatedAt: { type: Date, default: Date.now },
});
export const AndroidConfig = mongoose.model('AndroidConfig', AndroidConfigSchema);
```

★ **参照对象**：`core/db/models/payload-params.js:4`（`_id: { type: String, default: 'global' }`）
与 `core/config/payload-params-cache.js:8`（`findById('global').lean()`）的**读写模式**。

★ **并在 `models/index.js` 加一行 export**（**只加一行，不得动其他行**）。

## ★ 鉴权（前端已明确）

**这些端点【需鉴权】**（前端 `401` 时跳 `${ADMIN}/login`）
⇒ **不得**加入 `SKIP_AUTH_PATHS`。

## ★ 判据（先写、先跑到红）

`verify_d1c5a_admin_endpoints.py`：

| # | 断言 | 红态 |
|---|---|---|
| B1 | `android-config.js` 模型存在且导出 `AndroidConfig` | 缺 ⇒ 红 |
| B2 | `models/index.js` 导出了 `AndroidConfig` | 缺 ⇒ 红 |
| B3 | 10 条路由在 `plugins/android/**` 中注册（含 `${ADMIN}` 前缀） | 缺 ⇒ 红 |
| B4 | ★ **未修改 `payload-params.js`**（sha256 与 base 一致） | 变 ⇒ 红 |
| B5 | ★ 未改 `landing.js`、未改前端 | 变 ⇒ 红 |
| B6 | ★ `${ADMIN}` 前缀**逐字符正确**（`/mgr-admin-8bcde2021d98`） | 错 ⇒ 红 |
| B7 | 这 10 个端点**未被加入 `SKIP_AUTH_PATHS`**（它们需鉴权） | 有 ⇒ 红 |

**★ 真 HTTP 断言（R2 要求 · GET/POST 成对往返）**：

| 例 | 请求 | 期望 |
|---|---|---|
| T1 | `GET ${ADMIN}/api/theme`（**无 token**） | **401** |
| T2 | `GET ${ADMIN}/api/theme`（**带有效 token**） | **200**，`{ theme }` |
| T3 | `POST ${ADMIN}/api/theme {theme:"gold"}` → 再 `GET` | **持久化生效**（返回 `gold`） |
| T4 | `POST ${ADMIN}/api/pixel {action:"add",pixel_id:"1234567890"}` → `GET` | **`pixel_ids` 含该值** |
| T5 | `POST ${ADMIN}/api/pixel {action:"remove",...}` → `GET` | **已移除** |
| T6 | `POST ${ADMIN}/api/template {template:"vodex"}` → `GET` | 往返一致 |
| T7 | `POST ${ADMIN}/api/download-mode {mode:"link"}` → `GET` | 往返一致 |

★ **T3 是对"持久化"的关键验证**（不是只返回请求值）。
★ **token 的获取方式**：须执行者实读既有 `/api/auth/login` 的登录方式
（或复用既有测试 token 机制）。**若无法获取 token ⇒ 如实说明并跳过**，不得编造。

## 不在范围

- **不含** `stats` / `visits` / `visits/clear` / `apk/list` / `apk/delete`（属 **D1-C5b**）
- **不含** `/login` / `/logout`（属 **D1-C5b**，含鉴权）
- 不含 `/api/apk/upload`（属 **D1-C3**）
- 不改 `landing.js`、不改前端、不改 `payload-params.js`

## 证据要求

- 判据改前红 / 改后绿两次真实退出码
- 新增/修改文件的 sha256 与 bytes
- **T1–T7 的真 HTTP 响应原文**
- ★ 声明：**未改 `payload-params.js` / `landing.js` / 前端**

## 停靠点

1. **token 获取方式无法确定** ⇒ 停下升级（T2–T7 无法做）
2. 若 `${ADMIN}` 前缀与既有路由**冲突** ⇒ 停下升级
3. 若需**改契约**（如新增 model 需改 contracts.md）⇒ 停下升级
4. 若 `apk-url` / `download-mode` 需与 **D1-C3（apk 侧）** 共享状态
   ⇒ 停下升级（跨卡协调）
