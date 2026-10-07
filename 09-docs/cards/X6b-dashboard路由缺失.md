---
id: X6b
mode: 实施
wave: X
depends: [D1-C5b]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  ★★ **X6 判据实测发现的真实功能缺口**（非判据问题）：
    · 登录成功 ⇒ 302 到 `${ADMIN}/dashboard` ⇒ **404**（`UNMATCHED`）
    · 且**无人提供 `admin_dashboard.html`**（60,126 B 的管理台 UI）
  ★ 涉及**新增路由**（提供管理台 UI）⇒ 属 `02-backend-node/**` ⇒ **R2**。
  门禁强度自知：须**真登录 → 跟随 302 → 拿到 UI 页面**，端到端。
来源: ★ **X6 判据实测发现**（`verify_admin_login.py` 的 W2b）
      + Node 日志实证：`UNMATCHED GET /mgr-admin-8bcde2021d98/dashboard`
      + `admin.js` 的 `DASHBOARD_PATH` 定义与 `reply.redirect(DASHBOARD_PATH, 302)`
base:
  - path: 02-backend-node\src_restored\plugins\android\admin.js
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
  - path: 03-web-admin\static\admin_dashboard.html
    sha256: 9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5
    bytes: 60126
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\plugins\android\**（★ 新增 dashboard 路由）
  - E:\ios漏洞\_integration\_fix_work\verify_x6b_dashboard.py
forbidden_paths:
  - "03-web-admin\\static\\**（★ 契约来源，只读 —— 本卡只【读取】它作为响应体）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\landing.js（已验收）"
  - "02-backend-node\\src_restored\\app.js（D1-C1b 刚更正过）"
  - "05-ios/**、01-backend-go/**、04-landing/**、06-android/**"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_x6b_dashboard.py    # 动前红 / 动后绿
packages: {}
---

# X6b [R2] `${ADMIN}/dashboard` 无路由（登录成功后 404）

## ★★ 缺陷事实（X6 判据实测 + Node 日志确证）

### 现象

```
POST ${ADMIN}/login（正确凭据）  ⇒ 302
Location: /mgr-admin-8bcde2021d98/dashboard
GET  /mgr-admin-8bcde2021d98/dashboard  ⇒ 🔴 404 {"error":"未找到"}
```

**Node 日志**：
```
23:59:32.809  D1-C5b 管理台登录成功   {"ip":"127.0.0.1"}
23:59:32.826  UNMATCHED GET /mgr-admin-8bcde2021d98/dashboard 127.0.0.1
```

### 根因

**`admin.js` 定义了跳转目标，但**无人提供该路由**：

```js
const DASHBOARD_PATH = '/mgr-admin-8bcde2021d98/dashboard';
...
return reply.redirect(DASHBOARD_PATH, 302);   // :975
```

**全仓搜索 `admin_dashboard`：**
- ✅ 命中 `03-web-admin/static/admin_dashboard.html`（**60,126 B**）
- ❌ **无任何 JS 提供它**（`admin.js` 里的命中**全是注释**）

**⇒ 两个连带后果**：
1. **登录后落 404**（用户看不到任何界面）
2. **`admin_dashboard.html`（整个管理台 UI）完全不可达**

### ★ 这意味着什么

**验收项 1.8「后台可登录并完成核心操作」**：
- ✅ **可登录**（302 + cookie 已签发）
- ❌ **"完成核心操作"** ⇒ **无 UI 可用**（虽然 API 全绿 —— 见 X6 的 W5）

**⇒ 1.8 只满足了「API 层」，未满足「用户可用」层。**

## ★ 规格

### 新增 `GET ${ADMIN}/dashboard` 路由

**行为**：返回 `03-web-admin/static/admin_dashboard.html` 的内容（`text/html; charset=utf-8`）。

**位置**：应加在 **`adminAuthRoute`（公开域）还是 `adminRoute`（受保护域）？**

★ **须执行者分析并选择**：
| 方案 | 行为 | 评价 |
|---|---|---|
| (i) **受保护域**（`adminRoute`，需登录）| 未登录访问 ⇒ **401** | ★ **推荐**（后台 UI 应需登录）|
| (ii) 公开域（`adminAuthRoute`）| 匿名可访问 | ❌ 后台 UI 不应匿名可达 |

★ **但注意**：**(i) 有 UX 问题** —— 未登录用户访问 `/dashboard` 会看到 401 而非登录页。
**若选 (i)，须考虑**是否对 401 做重定向到登录页**（但那会改变 authMiddleware 行为 ⇒ 不在本卡范围）。

**⇒ 建议**：**(i) 受保护 + 401**（与既有 16 条管理台端点一致），
**并在报告中说明 UX 影响**。

### ★ 读取路径

**`admin_dashboard.html` 的定位**（参照 `resolveLoginHtmlPath()` 的既有做法）：
- 从**文件位置向上定位 repoRoot**（**不依赖 cwd**）
- 候选：`<repo>/03-web-admin/static/admin_dashboard.html`

★ **须复用 `resolveLoginHtmlPath()` 的模式**（`admin.js` 内已有）。

## ★ 判据要求

| # | 断言 |
|---|---|
| **Y1** | `GET ${ADMIN}/dashboard` **无 token ⇒ 401**（若选受保护域）|
| **Y2** | ★ **带 token ⇒ 200 + `text/html`** |
| **Y3** | ★ **响应体含 `admin_dashboard.html` 的关键特征**（如 `const ADMIN`） |
| **Y4** | ★ **端到端**：登录 → 302 → **跟随 Location → 200** |
| **Y5** | ★ **`admin_dashboard.html` 本体未被改**（sha256 与 base 一致） |
| **Y6** | 既有 16 条管理台端点仍正常（不回归）|
| **Y7** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **Y4 是本卡核心** —— 证明"登录后**真的**能到 UI"。
★ **Y5 是防改过头** —— `admin_dashboard.html` 是**契约来源**，**只读**。

## 不在范围

- **不改** `admin_dashboard.html`（契约来源）
- **不改** `app.js`
- **不实现**管理台 UI 的功能（本卡只**提供**静态页）

## 证据要求

- 判据动前红 / 动后绿两次真实退出码
- ★ **Y4 的端到端输出**（登录 → Location → 跟随 → 状态码 + 响应体前 200 字节）
- ★ **所选方案（公开域/受保护域）与理由**
- ★ **Y5 的证据**（`admin_dashboard.html` 未改）
- ★ 明确说明 **UX 影响**（未登录访问 `/dashboard` 的行为）

## 停靠点

1. ★ **若 `admin_dashboard.html` 的定位方式无法确定** ⇒ 停下升级
2. ★ **若需改 `app.js` 或 `authMiddleware`** ⇒ 停下升级
3. ★ **若发现 `admin_dashboard.html` 本身依赖不存在的资源** ⇒ 登记（不在本卡范围）
