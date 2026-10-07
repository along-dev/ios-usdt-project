---
id: T24
mode: 实施
wave: 审核修复·S1
depends: []
task_branch: 无
review_level: R2
状态: ★ **Owner 已裁决**：「按建议执行」⇒ C-1 只允许 admin
定档理由: |
  ★★★ **审核 C 的 C-1 [Blocker]**：**Node 管理台端点无 RBAC**。
  ★★ **调度取证（决定性）**：`auth.js:68-72` 的
    `findMenuKeyByPath(urlPath)` 对 `/mgr-admin-*` 返回**空数组**
    ⇒ `:72 return`（**"未注册路径放行"**）⇒ 任意已认证用户可读写管理台。
  ★ 修法：**管理台路径要求 admin 角色**（**最小、最安全**）⇒ **R2**。
来源: ★★★ **审核 C**（C-1）
      + ★★ **Owner 裁决**（**只允许 admin**）
      + ★★★ **调度取证**（**见下**）
base:
  - path: 02-backend-node\src_restored\plugins\api\middleware\auth.js
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\plugins\api\middleware\auth.js（★ 加管理台闸）
  - 02-backend-node\src_restored\config\menus.js（★ 若需补映射）
  - E:\ios漏洞\_integration\_fix_work\verify_t24_mgr_rbac.py
forbidden_paths:
  - "★ 02-backend-node\\src_restored\\plugins\\c2\\**（★ T23 在改）"
  - "01-backend-go/**、03-web-admin/**、05-ios/**、06-android/**"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_t24_mgr_rbac.py    # 动前红 / 动后绿
packages: {}
---

# T24 [R2] C-1 —— Node 管理台的 RBAC 闸

## ★★★★ 调度取证（**决定性**）

### `auth.js` 的现有逻辑

```js
:58  // Admin / channel_admin 直接放行（全量数据范围）
:58  if (isAdminLike(context.role)) { ...; return; }        ← ★ admin 放行

:64  // 普通用户: 设置数据范围过滤
:65  request.channelFilter = ...
:68  // RBAC: 匹配请求路径对应的 menuKey
:69  const matchedKeys = findMenuKeyByPath(urlPath);
:71  // 未注册路径放行（公共接口）
:71  if (matchedKeys.length === 0)
:72      return;                                            ← ★★ 缺口
:74  const hasPermission = matchedKeys.some(k => context.menuKeys.includes(k));
:75  if (!hasPermission) {
:80      reply.code(403).send({ error: '无权限' });
:81      return;
:82  }
```

### ⟹ 缺口

**`findMenuKeyByPath('/mgr-admin-8bcde2021d98/api/template')` ⇒ 空数组**
⇒ **`:72 return` ⇒ 放行**。

**★ 且只对**普通用户**生效**（**admin 在 `:58` 已放行**）
⇒ **解释了"匿名 401、低权 200"**。

### ★ 管理台的真实路径

```js
// plugins/android/admin.js
:46  export const ADMIN = '/mgr-admin-8bcde2021d98';
:51  export const ADMIN_API = '/mgr-admin-8bcde2021d98/api';
```

**21 条路由**：`login`/`logout`/`dashboard` + **14 条 API**
（`template`/`theme`/`pixel`/`download-mode`/`apk-url`/`stats`/`visits`/
`visits/clear`/`apk/list`/`apk/delete`/`apk/upload`）。

---

## ★★ 规格（**Owner 裁决：只允许 admin**）

### (1) 在 `auth.js` 加**管理台闸**

**★ 位置**：**在 `:63`（admin 放行）之后、`:64`（普通用户过滤）之前**。

**逻辑**：
```js
// ★★ T24：管理台（${ADMIN}/**）【仅 admin 角色】可访问。
//   背景：findMenuKeyByPath 只映射 /api/*，对 /mgr-admin-* 返回空数组
//   ⇒ 原 :72 的「未注册路径放行」使任意已认证用户可读写管理台（审核 C 的 C-1）。
//   ★ 公开路径（login/logout）已由 SKIP_AUTH_PATHS 放行，不在此列。
const MGR_PREFIX = '/mgr-admin-8bcde2021d98';
if (urlPath === MGR_PREFIX || urlPath.startsWith(MGR_PREFIX + '/')) {
    if (!isAdminLike(context.role)) {
        logger.info({ url: request.url, username: context.username, role: context.role }, 'RBAC rejected: mgr-admin requires admin');
        reply.code(403).send({ error: '无权限' });
        return;
    }
    request.channelFilter = {};
    request.chainFilter = null;
    request.visibleSocialTypes = null;
    return;
}
```

★ **注意**：
- **`login`/`logout` 必须仍匿名可达** ⇒ **须把它们加入 `SKIP_AUTH_PATHS`**
  （**核实当前是否已在** —— **实测 `/mgr-admin-*/login` GET 200 ⇒ 可能已放行**）
- **不得影响 `/api/*` 的既有 RBAC**

### (2) 核实 `isAdminLike` 的语义

**`core/auth/permissions.js` 的 `isAdminLike(role)`** ——
★ **须确认它是否包含 `channel_admin`**（**若包含 ⇒ 管理台对 `channel_admin` 也开放**，
**须评估是否可接受**）。

---

## ★★ 判据要求

| # | 断言 |
|---|---|
| **V1** | ★★★ **低权用户（`role:user`）访问 `${ADMIN}/api/*` ⇒ 403**（**动前是 200**）|
| **V2** | ★★ **admin 访问 `${ADMIN}/api/*` ⇒ 200**（**不误伤**）|
| **V3** | ★★ **`${ADMIN}/login` 仍匿名可达**（**GET 200**）|
| **V4** | ★ **既有 `/api/*` RBAC 未变**（**低权访问受限、admin 放行**）|
| **V5** | ★ **匿名访问 `${ADMIN}/api/*` ⇒ 401**（**原来就是 401，应保持**）|
| **V6** | ★ **`node --check` 通过** |
| **V7** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **V1 是核心**（**动前 200 → 动后 403**）。
★ **V2/V3 是"未误伤"的证据**。

## ★ 不在范围

- ★ **不改 `findMenuKeyByPath`**（**除非必要**）
- ★ **不改 `admin.js`**（**只读**）
- ★ **不改 Go 侧**

## ★ 证据要求

- ★★ **V1 的前后对照**（**200 → 403**）
- ★ **V2/V3 的证据**
- ★ **`isAdminLike` 的语义说明**
- ★ 判据真实退出码（动前红 / 动后绿）
- ★ 声明：**未改 `c2/**`、`admin.js`**

## 停靠点

1. ★★ **若 `isAdminLike` 包含 `channel_admin`** 且 **Owner 未授权** ⇒ **停下报告**
2. ★★ **若 `${ADMIN}/login` 不在 `SKIP_AUTH_PATHS`** ⇒ **须加**（**否则登录页不可达**）
3. ★★ **若加闸后 admin 也被拒** ⇒ **停下报告**
