---
id: F1-C6
mode: 实施
wave: 3
depends: [F1-C5]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  触 08-infra/nginx 与 docker-compose —— 属部署编排，影响【服务可达性】。
  与 F1-C5 共用「前端→后端」这条契约边界（D 线），故 depends 于 F1-C5（同线不并行）。
  门禁强度自知：须有【路由断言】（哪些前缀落到哪个 upstream），不得只看配置语法。
来源: 09-docs/reports/全量审核报告_独立复核版.md §三 P1-F
base:
  - path: 08-infra\nginx\default.conf.template
    sha256: d0e9ad89830de406b01300edb92e6c9cbac8cbd408b90c2e14939d0351398063
    bytes: 2146
    eol: LF
  - path: 08-infra\compose\docker-compose.yml
    sha256: 1c58cb69beb81042af5f6c675d8f5d4933377d3526ba907ddd0cf705f5b33d71
    bytes: 969
    eol: "CRLF=1 LF=44（★ 混合！改动前须确认保留哪一侧，勿整文件改写行尾）"
allowed_paths:
  - 08-infra\nginx\default.conf.template
  - 08-infra\compose\docker-compose.yml
  - E:\ios漏洞\_integration\_fix_work\verify_f1c6_nginx_routes.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "01-backend-go/**、02-backend-node/**（本卡只改编排，不改应用）"
  - "05-ios/**、06-android/**、03-web-admin/**、04-landing/**"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_f1c6_nginx_routes.py    # ①动前：须【红】，退出码 != 0，留证
  - python _fix_work\verify_f1c6_nginx_routes.py    # ②动后：须【绿】，退出码 0
packages: {}
---

# F1-C6 [R2] nginx 只反代 Node → Go 管理台不可达

## 目标

让**管理台（Go:8888）**与**落地页/Node（3000）**的路由在 nginx 上各归其位。

## 缺陷事实（本轮实读）—— ★ 比原报告所述更严重

| 位置 | 现状 |
|---|---|
| `default.conf.template:1-3` | `upstream app_server { server server:3000; }` |
| `:32-33` | `location /api/ { proxy_pass http://app_server; }` |
| `:82-83` | `location / { proxy_pass http://app_server; }`（default_server） |
| `docker-compose.yml` | 仅 `nginx`/`server`/`mongo`/`redis` —— **无 Go 后端服务** |

### ★★ 关键实测：不是"部分路由 404"，而是**管理台整体不可用**

原审核报告 P1-F 称「管理台 `/base/login`、`/user/*` 被转给 3000 → 404」。
**本轮进一步实测，问题范围更大且机理不同**：

1. `03-web-admin/src/utils/request.js:8` → axios `baseURL = import.meta.env.VITE_BASE_API`
2. `03-web-admin/.env.development` / `.env.production` → **`VITE_BASE_API = /api`**
3. `03-web-admin/src/api/*.js` 里的 url **不含 `/api`**，例如：
   - `api/user.js:8` → `url: '/base/login'`
   - `api/index.js:5` → `url: '/device/list'`
   - `api/menu.js:8` → `url: '/menu/getMenu'`

⇒ **浏览器实际发出的请求是 `POST /api/base/login`、`POST /api/device/list`**。

4. 而 nginx `location /api/` **全部转给 Node:3000** ⇒
   **管理台的每一个接口都打到 Node**（Node 无这些路由）⇒ **管理台整体不可用**，
   不只是 `/base/login`。

### ★★★ 更严重的冲突：Go 自己也有 `/api/*`

`01-backend-go/router/system/sys_api.go:12-13`：

```go
apiRouter := Router.Group("api").Use(middleware.OperationRecord())
apiRouterWithoutRecord := Router.Group("api")
```

⇒ Go 侧**真实存在** `/api/createApi`、`/api/getApiList` 等路由，
且前端 `03-web-admin/src/api/api.js:16` 正是调 `url: '/api/getApiList'`
（注意：**这一处 url 自带 `/api`**）。

⇒ **`/api/` 这个前缀被"落地页 → Node"与"管理台 → Go"同时使用**，
**不能简单按前缀二选一**。这是本卡**最核心的决策点**（见停靠点 1）。

★ **与 F1-C5 的关系**：F1-C5 让落地页的 `/api/track/*` 在 Node 侧**有实现**；
本卡要解决的是**同一前缀下两套后端的分流**。两卡都在动"路由归属"，故**必须串行**。

## 规格

### (a) ★★ 第一步是裁决分流规则 —— 不是直接改配置

**已确认的事实**：`/api/` 前缀**被两侧同时使用**：

| 消费者 | 实际请求示例 | 目标后端 |
|---|---|---|
| 落地页（`04-landing/runtime/landing-runtime.js`） | `/api/track/heartbeat`、`/api/pixel-config`、`/api/apk/download` | **Node:3000** |
| 管理台（`03-web-admin`，baseURL=`/api`） | `/api/base/login`、`/api/device/list`、`/api/menu/getMenu`、`/api/getApiList` | **Go:8888** |

⇒ **不能按前缀二分**。必须选一种分流方式：

| 选项 | 做法 | 代价 |
|---|---|---|
| **(a1) 按 Host 分流** | 管理台域名 → Go；落地页域名 → Node | 需两个域名（`ADMIN_DOMAIN` 已有，落地页域名见 `:45`/`:60` 的 `shopig.shop`/`shopind.shop`）★ **看起来最干净** |
| **(a2) 改管理台 baseURL** | 把 `VITE_BASE_API` 从 `/api` 改成一个**不与落地页冲突**的前缀（如 `/mgr-api`），nginx 相应分流 | 需改前端 + 重新构建；★ 但**改 `/api/api.js` 里自带 `/api` 的那 8 处 url** 风险高 |
| **(a3) 落地页改前缀** | 落地页端点改为 `/api/pixel/*` 之类，nginx 按更细规则分流 | 需改前端；且 `apk/download` 等已写死 |
| (a4) 精确 location 白名单 | 逐个列 `/api/track/`、`/api/pixel-config`、`/api/apk/` → Node；其余 `/api/` → Go | 脆弱（新增端点数漏一个就静默错），**不推荐** |

★★ **本卡不预设选项** —— 执行者**不得自行选择**，必须**停下升级 Owner**（见停靠点 1）。
**分配置之前，先拿到裁决编号。**

### (b) 管理台其余前缀（不重叠部分，可独立处理）

以下前缀**不与 `/api/` 冲突**，无论 (a) 选哪个都需要落到 Go：

- `/base/`（登录/验证码）—— `router/system/sys_base.go:11-15`
- `/user/`、`/menu/`、`/system/`、`/casbin/`、`/authority/`、`/jwt/`、`/init/`
  （`PrivateGroup`，`initialize/router.go:78-99`）
- `/device/`（`InitDeviceRouter`，`initialize/router.go:95`）

★ **具体清单必须现场枚举**：实读 `01-backend-go/router/system/*.go` 每个 `Router.Group("<x>")`
的字面量，**逐个列出**并写进证据。**不得凭本卡的示例照抄。**

### (c) `docker-compose.yml` 补 Go 服务

当前 compose **没有 Go 服务** ⇒ 即使 nginx 配了 `go_server` upstream 也**无目标**。
执行者须二选一并在证据里说明：**(c1)** 补 Go 服务进 compose；**(c2)** 明确声明 Go 由 compose 外提供。
★ 若选 (c1) 且需**新增镜像/构建** ⇒ 停下升级（触部署，见停靠点 3）。

### (d) 端口归属不得改

调度表已固定：Go **8888** / Node **3000** / MariaDB **13306** / Redis **16379** / Mongo **27018**。
★ 并注意 **vite dev 也占 8888**（调度表已标注"起前必查"）。

### (e) `docker-compose.yml` 行尾须谨慎

★ 实测该文件为 **1 CRLF + 44 LF（混合）**。
**不得**顺手把整文件统一成 LF 或 CRLF —— 那会制造无意义 diff，
并可能触发 `_manifest.sha256` 与脱敏比对的连锁差异（与 `qianke.sql` 同类陷阱，**P-5**）。

## ★ 判据先于实现（判据 9）

| # | 断言 | 红态（改前） |
|---|---|---|
| R1 | 管理台前缀（`/base/`、`/user/`、`/device/`、`/menu/` 等**枚举所得**）**不**落到 Node upstream | 落地页规则下**全部**落 Node ⇒ 红 |
| R2 | 落地页前缀（`/api/track/`、`/api/pixel-config`、`/api/apk/download`）落到 Node upstream | 绿（防改过头） |
| R3 | `/api/` 的**分流规则与裁决一致**（按裁决方式断言） | 未定义 ⇒ 红 |
| R4 | 每个 upstream 名在 compose 中**有对应服务**（或已声明外部提供） | `go_server` 无对应 ⇒ 红 |
| R5 | 端口与调度表一致 | 绿（防改坏） |
| R6 | `docker-compose.yml` 的**行尾分布未被改动**（仍 1 CRLF + 44 LF） | 绿（防手滑整文件改写） |

★ **R1 必须用「枚举所得清单」而非本卡示例** —— 本卡的 `/base/`、`/user/` 只是示例，
执行者须以自己实读的完整清单为准。

## 不在范围

- 不改应用代码（`01`/`02`）
- **不部署、不起服务**（push / 部署**未授权**）
- 不改证书路径（`ios17.cc.cert` 等保持不动）
- 不改 `_manifest.sha256`
- ★ **不自行决定 `/api/` 的分流方式**（属 Owner 裁决，见停靠点 1）

## 证据要求

- (a) 的**裁决编号**（Owner 选项），必须与配置实际做法一致
- 从 `01-backend-go/router/**` **实读**的管理台前缀**完整清单**（文件:行号 + `Group("<x>")` 字面量）
- `verify_f1c6_nginx_routes.py` 改前红 / 改后绿两次真实退出码
- (c) 的处置选择与理由
- 两个文件的改前 / 改后 sha256 + **行尾分布**
- ★ **明确声明**：本卡**未**在真实 docker 环境起服务验证（部署未授权）

## 停靠点

1. ★★★ **首要停靠点：`/api/` 分流规则必须由 Owner 裁决**（选项 a1–a4，见规格 (a)）。
   - 已实测：`/api/` **被落地页（→Node）与管理台（→Go）同时使用**，
     且 Go 侧 `router/system/sys_api.go:12` 确有 `Group("api")`。
   - **执行者不得自行选择**。未拿到裁决编号前，本卡**不得开工**。
   - ★ 建议调度向 Owner 提交决策时附上规格 (a) 的四个选项与代价。
2. 若补 Go 服务进 compose 需要**新增镜像/构建** ⇒ 停下升级（触部署）
3. 若发现端口需变更 ⇒ **停下升级**（端口已固定，属停靠点）
4. 若实读发现**除 `/api/` 外还有其它前缀重叠** ⇒ 登记上报，并一并提交 Owner
