---
id: D1-C5b
mode: 实施
wave: D1
depends: [D1-C5a]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  在 `plugins/android/` 内新增**数据类**端点（stats/visits/apk list/delete）+ 登录登出。
  属 `02-backend-node/**` ⇒ 至少 R2。
  ★ 不触碰资金路径、不改契约、不改已验收文件 ⇒ 不上 R3。
  门禁强度自知：判据须含【分页参数真生效】与【删除真生效】的断言。
来源: `09-docs/reports/D1-管理台侧端点契约.md` §1/§2（前端硬契约）
      + `09-docs/analysis/双平台整合复刻方案.md:249-264`
base:
  - path: 02-backend-node\src_restored\plugins\android\index.js
    sha256: d11cca2e2aaed7ea053ee2f442119ca215885980e1a492ce1436ea53d87d63db
    bytes: 1811
    eol: LF
  - path: 02-backend-node\src_restored\plugins\android\admin.js
    sha256: e2e8757bcb10505cb5bc3181f573060e1e11ff2a1fb9ff6a70a3ec1ae8993682
    bytes: 11175
    eol: LF
  - path: 02-backend-node\src_restored\app.js
    sha256: a1b568827febc198f115f5e285e29e368b80f211f121797d1b4da8f59f3c16fb
    bytes: 14992
    eol: LF
  - path: 03-web-admin\static\admin_dashboard.html
    sha256: 9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5
    bytes: 60126
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\plugins\android\**
  - E:\ios漏洞\_integration\_fix_work\verify_d1c5b_admin_data.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\landing.js（已验收）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\visitors.js（★ 既有访问者端点，只读 —— 参照但不得改）"
  - "03-web-admin\\static\\**（前端是契约来源，只读）"
  - "01-backend-go/**、05-ios/**、06-android/**"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d1c5b_admin_data.py    # 动前红 / 动后绿
packages: {}
---

# D1-C5b [R2] 管理台侧**数据端点** + 登录登出

## 目标

实现管理台的**数据类**端点与登录登出。

## ★ 前缀（Owner 裁决 甲）

```js
const ADMIN = '/mgr-admin-8bcde2021d98';   // ★ 逐字符保留
```

| # | 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|---|
| 1 | GET | `${ADMIN}/api/stats` | — | **`{ total, today, clicks, ... }`** |
| 2 | GET | `${ADMIN}/api/visits` | **`?page=&per=`** | **`{ total, rows: [...] }`** |
| 3 | POST | `${ADMIN}/api/visits/clear` | —（**无 body**） | — |
| 4 | GET | `${ADMIN}/api/apk/list` | — | **`{ files: [...] }`** |
| 5 | POST | `${ADMIN}/api/apk/delete` | `{ id }` | — |
| 6 | POST | `${ADMIN}/login` | （表单/JSON） | 建立会话 |
| 7 | GET | `${ADMIN}/logout` | — | 清除会话 |

## ★★ 字段级规格（前端硬证据，逐条来自 `admin_dashboard.html`）

### `/api/stats`
- **前端读取**：`total`、`today`、`clicks`
- 计算（`:724`）：`d.clicks / d.total * 100`
- ⇒ **必须含 `total` 与 `clicks`**（否则前端显示 `NaN`）
- ★ **数据源**：既有 `landing_visits` collection（`LandingVisit` 模型，见 `landing.js:32-50`）

### `/api/visits`
- **查询参数**：`page`、`per`（`:743` 拼接 `${ADMIN}/api/visits?page=${page}&per=${per}`）
- **响应**：`{ total, rows: [...] }`
- **rows 每行 18 字段**（前端渲染 + 已有硬样本）：
  `id, session_id, ip, country, region, city, browser, os, device, ua, lang, url,`
  `referer, dwell_ms, clicked, clicked_at, started_at, last_seen_at`
- ★ **硬样本**：`E:\ios漏洞\_analysis\recon\visits_dump.json`（63,954 B）
  ⇒ `{ ok: true, page: 1, per: 100, total: 178, rows: [100 条] }`
  **★ 执行者应先读它确认字段名与形态**

### `/api/apk/list`
- **响应**：`{ files: [...] }`
- **`files` 元素**（已从 `:793-825` 提取）：

| 字段 | 用途 |
|---|---|
| `id` | **删除主键** |
| `original_name` | 文件名 |
| `size` | 字节数 |
| `uploaded_at` | 上传时间 |
| `tg_file_id` | 可选（Telegram 同步标记） |

- ★★ **`files[0]` = 最新/当前使用**（`:797` `const f = files[0]`；`:821` `i===0 ? '当前使用'`）
  ⇒ **必须按"新→旧"排序返回**

### ★★ APK 的**数据源已查明**：文件系统（非 DB）

`landing.js:154-159` 的既有实现：

```js
const configured = String(process.env.LANDING_APK_PATH || '').trim();
const candidates = [
  configured,
  path.join(process.cwd(), 'templates', 'apk'),
  path.join(process.cwd(), 'public', 'apk'),
].filter(Boolean);
// 然后 readdirSync(dir).filter(f => f.toLowerCase().endsWith('.apk'))
```

**⇒ `apk/list` 应扫描同样的候选目录**（**建议复用该候选逻辑**，避免两处不一致），
`apk/delete` 应**删文件**（★ 须做路径安全校验，防目录穿越）。

★ `id` 字段可用**文件名**（或 `name@mtime` 之类稳定标识）——
**执行者自行设计并说明**，但须保证 `delete` 能唯一定位。

### `/api/apk/delete`
- **请求**：`{ id }`
- ★★ **必须做路径安全校验**：`id` 解析出的路径必须在候选目录内
  （**防 `../` 目录穿越**）

### `${ADMIN}/login` / `logout`
- 前端 401 时跳 `${ADMIN}/login`（`:714` 等）
- ★ **须与既有 `/api/auth/login` 的关系明确**（见停靠点 1）

## ★ 判据要求

| # | 断言 |
|---|---|
| D1 | 7 条路由注册（带 ADMIN 前缀） |
| D2 | ★ **未改** `landing.js`、`visitors.js`、前端 |
| D3 | ★ 分页**真生效**（`per=1` 与 `per=5` 返回**不同条数**） |
| D4 | ★ `stats` 的响应**含 `total` 与 `clicks`** |
| D5 | ★ `apk/list` 的 `files` 按**新→旧**排序（若有多条） |
| D6 | ★ `/api/visits/clear` **真清空**（clear 后 `total` 变化） |
| D7 | `login`/`logout` 可用 |

★ **D3/D5/D6 是"数据端点"的核心** —— 不得只验证"返回 200"。

## 不在范围

- 不含 `theme`/`pixel`/`template`/`download-mode`/`apk-url`（**D1-C5a 已做**）
- 不含 `/api/apk/upload`（**D1-C3**）
- 不改 `landing.js` / `visitors.js` / 前端

## 停靠点

1. ★ **`${ADMIN}/login` 与既有 `/api/auth/login` 的关系不明** ⇒ 停下升级
   （是复用既有登录、还是新建独立登录页？**前端跳转目标是一个页面，不是 API**）
2. `/api/visits/clear` **属破坏性操作** ⇒ 若会清空真实数据 ⇒ 停下升级
   （★ 若在 e2e 库执行，须先备份或确认可重建）
3. `/api/apk/list` 的**数据源不明**（APK 存在哪？文件系统 or DB）⇒ 停下升级
