# 审核 A：契约与拓扑

> **审核域**：域 A —— 前端 ↔ 后端 ↔ 数据库的全链路契约一致性
> **标准**：「可上线」
> **纪律**：只审不改（未修改任何产物文件；本报告与 `_fix_work/` 下探针脚本为唯一写操作）
> **审核时间**：2026-10-02
> **树中核实**：所有结论均在当前代码树 + 当前运行进程上实测复现

---

## 0 · 结论摘要

- **[Blocker] 3 / [Major] 4 / [Minor] 3 / [Info] 3**

**一句话结论**：契约层（C-1…C-5、Node→Go 桥、T22 合并）**代码实现基本正确且可复现**，
但**上线拓扑不成立** —— 唯一让前端「能用」的 `_gva_proxy.cjs:8080` **不在产物树内、无部署方案、且其 token 桥接把 Node 侧鉴权完全旁路（匿名可取业务数据）**；
同时 `08-infra/nginx` 的正式配置**没有任何 `/api/dashboard/*` 路由**，一旦按正式方案部署，T19/T22 三个看板端点**全部 404**。
**⇒ 当前「能跑」依赖一个树外的测试设施，正式部署路径未闭环。**

---

## 1 · 问题清单（表）

| # | 严重度 | 问题 | 证据（命令/文件:行号） | 影响 | 修复建议 |
|---|---|---|---|---|---|
| 1 | **[Blocker]** | `_gva_proxy.cjs` 的 token 桥接**完全旁路 Node 鉴权**：**无需任何凭证**即可取到 Node 侧业务数据 | `_gva_proxy.cjs:189-196` + 实测 `GET :8080/api/dashboard/collect-summary`（无 Cookie）⇒ `{"code":0,"data":{"total":39,...}}` | 任意匿名者可读归集汇总/设备版本/TTL 状态 | 桥接改为**透传调用方凭证**或**取消桥接**（见问题 5 的正解）；**不得**用服务端固定凭证代签 |
| 2 | **[Blocker]** **正式部署方案（nginx）没有任何 `/api/dashboard/*` 路由** —— 三个看板端点在正式拓扑下全 404 | `08-infra/nginx/default.conf.template:41-49`（`location /api/` **只** proxy 到 `go_server`）；实测 `curl :8888/dashboard/collect-summary` ⇒ **404** | 按 `08-infra` 正式部署后，T19/T22 看板**整体不可用** | nginx 增补 `/api/dashboard/` → `app_server`(Node)；或按 F1-C6 停靠点 1 由 Owner 裁决分流 |
| 3 | **[Blocker]** **8080 代理是树外测试设施，却是当前唯一的可用拓扑**；其存在**未登记**在 R-01…R-12 | `Get-CimInstance`：`PID 17896 CMD=node X:\_integration\_fix_work\_gva_proxy.cjs 8080 ...`；`09-docs/reports/残余暴露面登记.md` **无 8080/gva_proxy 条目**（grep 命中 0） | 上线后无 8080 ⇒ 前端的 Node 三端点全断；且问题 1 的暴露面**未登记即不可追踪** | 二选一：**(a)** 把桥接能力**落进 08-infra（nginx + Node 内路由）**并删代理；**(b)** 若保留，**必须登记为 R-13** 并明确其非生产定位 |
| 4 | **[Major]** **两套登录体系并存，前端页面**（Go 体系）**的凭证无法访问 Node 端点** —— 逐页核对不通过 | 前端登录走 Go：`pinia/modules/user.js:58-61`（`/base/login` + `setToken(res.data.token)`，token 存 `localStorage`）；Node 鉴权要 **cookie `accessToken`**：`plugins/api/middleware/auth.js:29`。实测：**用 Go 签发的合法 JWT 打 Node 直连 ⇒ 401**；经代理 ⇒ 200（**靠桥接强行换票**） | 任一端点从 Node 侧迁到直连/换域名即失效；且掩盖了「前端无 Node 会话」这一事实 | 前端补 Node 登录态，或**收敛为单一登录体系**；若坚持双体系，须把「代理代换票」改为**受控的服务端代持**并登记 |
| 5 | **[Major]** `QIANKE_SERVICE_TOKEN` **只存在于树外运行工作区**，产物树内**无任何配置来源** | `02-backend-node/src_restored/plugins/api/routes/dashboard-versions.js:24` 读 `process.env.QIANKE_SERVICE_TOKEN`；实测该变量**仅**在 `E:\ios漏洞\_integration\_fix_work\_i1c3_ws\.env` 定义 | 正式部署若未注入 ⇒ **静默降级**为「仅 gasleak 侧」（`sources.qianke=null`），T22 的跨库合并**在生产失效但不报错** | 在 `08-infra` 明确该变量的**生产注入路径**并加入部署检查清单；或加启动期**显式告警** |
| 6 | **[Major]** Node→Go 调用的**失败降级为静默**（仅返回 `limitation` 字符串），看板**不显红** | `dashboard-versions.js:113-115`（`limitation` 文案）+ `:48-56`（各种失败均 `total:null`） | 生产上 Go 不可达 ⇒ 看板显示 `total` **偏小且无强提示**（仅一行 warning alert） | 在 `collectSummary.vue` 对 `sources.qianke===null` 加重级告警；或后端加 `degraded:true` 机器可读标志 |
| 7 | **[Major]** C-2 契约宣称的 **`collect-lock` 冲突 ⇒ HTTP 409** 在**真实可冲突路径上未经端到端验证** | `api/v1/app/collect_lock.go:47` 确有 `StatusConflict`（**代码锚点成立**，count=1）；但实测两次连续 `POST :8888/app/collect-lock`（同一 device/chain/address）**均返回 200 + `code:7`（未匹配到 wallet）** —— 因测试数据无对应 wallet，**409 分支未被触达** | 409 契约**代码存在但无运行证据**；调用方 `collect-bridge.js:131` 依赖 `r.status===409` 判定冲突 | 补一条**有真实 wallet 的**冲突用例，取得 409 实测证据；否则该分支标注「未验证」 |
| 8 | **[Minor]** `GET /base/captcha` **404**（方法不匹配），易误判为缺陷 | `sys_base.go:15` 为 `POST("captcha")`（**POST**）；前端 `api/user.js:18-24` 亦为 `post` | **无实际缺陷**（前后端一致）；但按 REST 直觉用 GET 探测会得到 404，干扰排障 | 在 `contracts.md`/README 注明 captcha 为 **POST**；保持不变 |
| 9 | **[Minor]** 前端 `dashboard.js` **缺少 `ttl-status` 封装**，而代理 `NODE_ROUTES` **含**该路由 | `api/dashboard.js` 仅导出 `getDeviceVersions`/`getCollectSummary`（全文 25 行）；`_gva_proxy.cjs:31-35` 的 `NODE_ROUTES` 含 `'/dashboard/ttl-status'` | 代理多一条**无前端消费者**的路由（死代码/多余暴露面） | 删除该路由，或补前端消费；二者取一 |
| 10 | **[Minor]** `.env.development` / `.env.production` **注释为 GBK 乱码**，且 `VITE_SERVER_PORT=8888` 与「前端经 8080 访问」的实际拓扑**不符** | `Get-Content .env.development` ⇒ `// 濡傛灉浣跨敤docker-compose寮€鍙戞ā寮?..`（乱码）；`VITE_SERVER_PORT = 8888` | 误导排障：按该值直连 8888 会因**缺 `/api` 剥离**而全 404 | 修正注释编码；把端口语义写清（前端入口是代理端口，非 8888） |
| 11 | **[Info]** C-1…C-5 **五条契约与当前代码全部一致**（逐条实测，见 §3） | 见 §3 各行 | 无 | 维持冻结；变更须走停靠点 |
| 12 | **[Info]** T22 的跨库合并**已真实落地并可与生产同构复现** | 实测 `/app/bill-list` 带 token ⇒ `code:0 total:33`；经代理 `collect-summary` ⇒ `sources:{gasleak:6,qianke:33}`、`scope:"gasleak+qianke"`、`limitation:null` | 无 | 维持；注意问题 2/5 的部署前提 |
| 13 | **[Info]** `router/system/sys_qianke.go` 的 30 条 `/device/*` 路由与前端 29 处调用**完全对齐**（无 404 风险） | 实测脚本比对：**前端缺失 0 条**；Go 侧 `wallet_list` 无前端调用（冗余） | 无 | 可选：清理 `wallet_list` 冗余路由 |

---

## 2 · 逐条详述

### 问题 1：8080 代理的 token 桥接**完全旁路 Node 鉴权**（匿名可读业务数据）[Blocker]

**现象**
Node 侧三个看板端点**自身鉴权是好的**（匿名直连 3000 ⇒ **401**）。
但只要经 **8080 代理**访问，**不带任何 Cookie / token**，即返回 **200 + 真实业务数据**。

**复现（确切命令 + 实际输出）**

```powershell
# ① 直连 Node：鉴权正常（这是 Node 自己的 authMiddleware 在起作用）
E:\CTF\runtime\python\python.exe -X utf8 -c "
import urllib.request,urllib.error
r=urllib.request.urlopen('http://127.0.0.1:3000/api/dashboard/collect-summary',timeout=20)
"
# 实际输出：-> 401 {"error":"未授权"}      （三个端点全部 401）

# ② 经 8080 代理：完全匿名 ⇒ 200 + 业务数据
#    请求头无 Cookie、无任何 token
GET http://127.0.0.1:8080/api/dashboard/collect-summary
# 实际输出（HTTP 200）：
# {"code":0,"data":{"total":39,"confirmed":4,"pending":2,
#  "chains":{"btc":2,"eth":2,"tron":2},
#  "sources":{"gasleak":6,"qianke":33},
#  "scope":"gasleak+qianke","limitation":null},"msg":"ok"}

GET http://127.0.0.1:8080/api/dashboard/device-versions  # => 200, len 324
GET http://127.0.0.1:8080/api/dashboard/ttl-status       # => 200, len 596
```

**根因**
`_gva_proxy.cjs` 在把请求转发给 Node **之前**，用**服务端写死的凭证**自行登录取票并注入 Cookie：

```js
// _gva_proxy.cjs:37-38
const NODE_USER = process.env.GVA_NODE_USER || 'admin';
const NODE_PASS = process.env.GVA_NODE_PASS || 'i1c3-e2e-admin';
// _gva_proxy.cjs:189-196
if (isNodeRoute) {
    const tok = await nodeToken();          // ← 服务端自己去 /api/auth/login 换票
    if (tok) {
        const existing = req.headers.cookie ? req.headers.cookie + '; ' : '';
        req.headers.cookie = existing + 'accessToken=' + tok;   // ← 注入！
    }
}
```

`nodeToken()`（`:42-88`）调用 `POST /api/auth/login`（`NODE_USER`/`NODE_PASS`），
从 `Set-Cookie` 或响应体取 `accessToken`，**缓存 10 分钟**（`:84`），然后**无条件注入**。

**交叉验证（决定性）**：
用 Go 的 `signing-key` 自签一枚**合法 Go JWT**（证明「Go 体系凭证」确实有效但**对 Node 无效**）：

```
T1: 直连 8888 /user/getUserInfo + x-token(Go JWT) => 200 {"code":7,...,"msg":"获取失败"}
    ↑ code:7 = 「获取失败(无此用户ID)」而【非】"未登录或非法访问" ⇒ JWT 已被接受，鉴权通过
T2: 直连 3000 /api/dashboard/device-versions + 同一 Go JWT => 401 {"error":"未授权"}
    ↑ ★ 证明：Go 凭证【无法】通过 Node 鉴权（两套体系确实互不相通）
T3: 经 8080 /api/dashboard/device-versions + 同一 Go JWT => 200（有数据）
    ↑ ★ 证明：代理的 200 与调用方凭证【无关】，是桥接代签的结果
T4: 经 8080 /api/user/getUserInfo + 同一 Go JWT => 200 code:7（Go 侧正常）
```

**影响**
- 任意能访问 8080 的人（未认证）可读取归集汇总、设备版本分布、TTL 状态等**业务聚合数据**；
- `total:39 / confirmed:4 / chains / sources` 属**经营数据**，非静态资源；
- 该暴露面**未登记**在 `残余暴露面登记.md`（grep `8080|_gva_proxy` 命中 0）。

**建议**
1. **取消桥接**，改为**透传调用方 Cookie**（客户端自己持有 Node 会话）；
2. 若确需服务端代持，须**落进 product tree** 且**登记为残余暴露面**，并**限定为只读最小权限**；
3. **不得**保留 `GVA_NODE_PASS` 默认值这种「开箱即用」的提权路径。

---

### 问题 2：正式部署方案（nginx）**没有任何 `/api/dashboard/*` 路由** [Blocker]

**现象**
`08-infra/nginx/default.conf.template` 是**唯一的正式部署配置**。其 `ADMIN_DOMAIN` server 中，
`location /api/` **只**转发到 `go_server`（Go:8888），`location /` 走静态 + SPA fallback。

**复现**

```powershell
# ① nginx 配置里没有 dashboard 相关路由
Select-String -Path 08-infra\nginx\default.conf.template -Pattern "dashboard"   # 实际：无匹配
# location 全清单：/assets/ /api/ /base/ /user/ /  (无 /api/dashboard/)

# ② 按 nginx 规则（/api/X -> Go:8888/X），看板端点在 Go 侧并不存在
GET http://127.0.0.1:8888/dashboard/device-versions   # => HTTP 404 404 page not found
GET http://127.0.0.1:8888/dashboard/collect-summary   # => HTTP 404 404 page not found
```

**根因链**

```nginx
# 08-infra/nginx/default.conf.template:41-49
location /api/ {
    rewrite ^/api/(.*)$ /$1 break;      # ★ 无条件剥 /api
    proxy_pass http://go_server;        # ★ 只到 Go，无按路径再分流
}
```
前端 axios `baseURL=/api`（`.env.production:VITE_BASE_API = /api`），
故浏览器发 `GET /api/dashboard/collect-summary` → nginx 剥成 `/dashboard/collect-summary` → **Go 8888 → 404**。

**对照**：`_gva_proxy.cjs` 用 `NODE_ROUTES`（`:31-35`）**恰好补上了这个分流**——
这正是「代理是当前唯一可用拓扑」的直接原因。

**影响**
按 `08-infra` 正式部署 ⇒ **T19/T22 三个看板端点全 404**，看板页空白/报错。
`08-infra/README.md:17` 也自认「**这是本目录当前最重要的未决事项**」。

**建议**
- 在 `ADMIN_DOMAIN` server 中，于 `location /api/` **之前**加精确路由：
  ```nginx
  location /api/dashboard/ { proxy_pass http://app_server; }   # ★ 落 Node:3000
  ```
- 或按 **F1-C6 停靠点 1** 由 Owner 裁决（该卡明确要求 a1–a4 四选一，未裁决不得开工）；
- 无论哪种，**必须同步删除 8080 代理**，否则「树外设施」与「树内部署」双轨并存。

---

### 问题 3：8080 代理是**树外测试设施**，却是当前唯一可用拓扑，且未登记 [Blocker]

**现象**
产品树（`E:\USDT项目\`）内**不存在**该代理文件；它位于**同级另一棵树**。

**复现**

```powershell
Get-CimInstance Win32_Process -Filter "ProcessId=17896" | Select CommandLine
# 实际输出：
#   "E:\CTF\runtime\node\node.exe" "X:\_integration\_fix_work\_gva_proxy.cjs" 8080
#   "E:\USDT项目\03-web-admin\dist" "http://127.0.0.1:8888" "http://127.0.0.1:3000"

subst
# 实际输出： X:\: => E:\ios漏洞        （★ subst 映射，真实路径 = E:\ios漏洞\_integration\_fix_work\_gva_proxy.cjs）

Get-ChildItem -Path E:\USDT项目 -Recurse -Filter "_gva_proxy*"    # 实际：无
```

其源码自述亦确认为测试设施：
```
_gva_proxy.cjs:28  本代理在【测试期】用已知凭证自动向 Node 换取 accessToken 并注入 Cookie。
_gva_proxy.cjs:29  ★ 这是测试桥梁，不改任何产物代码。
```

**根因**
T19 的**临时处置**：当时代理承担了①路由分流 ②token 桥接 ③`code:0` 包装三件事，
但**只以「不改产物代码」为由留在树外**，未回流为正式部署件。

**影响**
- 上线后**无 8080** ⇒ Node 三端点既无路由（问题 2）也无会话（问题 4）；
- 该文件**不受 `_manifest.sha256` 覆盖** ⇒ 其行为变化**不触发任何完整性门禁**；
- 未登记 ⇒ 问题 1 的匿名暴露面**不可追踪、不可审计**。

**建议**
按问题 1/2 的结论**回流并销毁树外设施**：把「分流」（nginx）+「会话」（前端持 Node 登录态）分别落到正式位置。

---

### 问题 4：两套登录体系并存，前端凭证**无法访问 Node 端点** [Major]

**答「系统里有几套登录体系？」**

| # | 体系 | 端点 | 鉴权方式 | token 存放位置 | 载体 |
|---|---|---|---|---|---|
| **1** | **Go / gin-vue-admin（管理台）** | `POST /base/login`（`sys_base.go:14`） | 请求头 **`x-token`**（`request.js:41`）；服务端 `middleware.JWTAuth()` | 前端 **`localStorage['token']`**（`pinia/modules/user.js:21,126`） | 8888 |
| **2** | **Node / gasleak（落地页+数据 API）** | `POST /api/auth/login`（`routes/auth.js:125`） | **Cookie `accessToken`**（JWT，`session.js:51`）；`middleware/auth.js:29` 读取 | **HttpOnly Cookie**（`auth.js:368`） | 3000 |
| **3** | **服务间令牌**（非「登录」，但同属鉴权面） | `/app/*` 写读端点 | Header **`X-Service-Token`**（`middleware/service_token.go:25`） | 配置 `app-jwt.service-token` | 8888 |

**★ 前端页面调用的 API，与它登录时用的体系【不一致】：**

- 前端**只登录体系 1**（`login/index.vue:118` → `api/user.js:6` → `pinia/modules/user.js:58-61`；token 存 `localStorage`）；
- 但它有两个页面（`deviceVersions.vue`、`collectSummary.vue`）**调用体系 2 的端点**（`api/dashboard.js:12-24`）。

**★ 逐页核对结果**（用 Go 体系凭证，逐类访问）：

| 页面/模块 | 调用的 API 落在 | 用 Go 凭证直连目标后端 | 经 8080 |
|---|---|---|---|
| 资源管理/地址管理/财务/系统配置（**Go 侧 29 个 `/device/*`**） | Go:8888 | ✅ 通过（`x-token` 有效） | ✅ 通过 |
| 超级管理员（`/api/*`、`/user/*`、`/menu/*`、`/casbin/*`…） | Go:8888 | ✅ 通过 | ✅ 通过 |
| **`dashboard/deviceVersions`** | **Node:3000** | ❌ **401 未授权** | ⚠️ **200（桥接代签，非本人凭证）** |
| **`dashboard/collectSummary`** | **Node:3000** | ❌ **401 未授权** | ⚠️ **200（桥接代签）** |
| 登录页 `captcha`（POST `/base/captcha`） | Go:8888 | ✅ 通过（`code:0` 返回 captchaId/picPath） | ✅ 通过 |

**根因**：`/_gva_proxy.cjs` 的第 191–195 行用**服务端自己的 admin 凭证**补齐了 Node 会话，
使「前端用 Go 凭证访问 Node 端点」这一个**契约不一致**在**当前拓扑下被掩盖**。

**影响**：任何绕过 8080 的直连、换域名、或代理下线的动作，都会立即让两个看板页 401。

**建议**：前端补 Node 登录态（或在 Go 侧实现这三个端点），使**调用方凭证 == 被调方体系**。

---

### 问题 5：`QIANKE_SERVICE_TOKEN` 只存在于树外运行工作区 [Major]

**复现**

```powershell
# 代码侧的读取点
02-backend-node/src_restored/plugins/api/routes/dashboard-versions.js:24
    const QIANKE_SERVICE_TOKEN = process.env.QIANKE_SERVICE_TOKEN || '';

# 该变量在产物树内的定义点：无。实际只在树外运行工作区：
E:\ios漏洞\_integration\_fix_work\_i1c3_ws\.env
    QIANKE_API_BASE=http://127.0.0.1:8888
    QIANKE_SERVICE_TOKEN=i2c1-e2e-token
```

**根因**：运行中的 Node 进程以 `--env-file-if-exists=X:\_integration\_fix_work\_i1c3_ws\.env` 启动，
故**当前运行态是「恰好配上了」**，而**产物树内没有这个配置的出处**。

**影响**：`dashboard-versions.js:36-38` —— 变量缺失即 `return { total:null, error:'QIANKE_SERVICE_TOKEN 未配置' }`，
前端 `sources.qianke` 显示「不可达」，**看板静默降级**，T22 的跨库合并在生产上形同未做。

**建议**：在 `08-infra`（`.env` / compose environment）明确注入，并纳入部署检查清单。

---

### 问题 6：Node→Go 失败降级为**静默** [Major]

**证据**：`dashboard-versions.js:48-56`（各类失败一律 `total:null`）、`:113-115`（仅返回 `limitation` 文案）。

实测**未降级**（Go 可达）：`{"sources":{"gasleak":6,"qianke":33},"scope":"gasleak+qianke","limitation":null}`。

**风险**：生产上若 Go 不可达，前端只显示一行 `el-alert` warning（`collectSummary.vue:6-14`），
`total` 会**静默变小**（39 → 6），**无机器可读的降级标志**。

**建议**：后端加 `degraded: true`；前端对 `sources.qianke === null` 升为 error 级提示。

---

### 问题 7：C-2 的 `collect-lock` **409 契约无运行证据** [Major]

**代码锚点成立**：`api/v1/app/collect_lock.go:47` ⇒ `c.JSON(http.StatusConflict, ...)`（`StatusConflict` count=1）。

**但实测未触达该分支**：

```powershell
POST http://127.0.0.1:8888/app/collect-lock   X-Service-Token: i2c1-e2e-token
  body {"device_id":"x","chain":"tron","address":"y"}
# lock#1 => 200 {"code":7,"data":{},"msg":"未匹配到 wallet: device_id=x chain=trx address=y"}
# lock#2 => 200 {"code":7,"data":{},"msg":"未匹配到 wallet: device_id=x chain=trx address=y"}
```
两次调用均在 **wallet 解析阶段**失败（无该 wallet），**未进入占位冲突判定**，故 **409 从未发生**。

**影响**：`collect-bridge.js:131` 依赖 `r.status === 409` 区分「他处正在归集」与「参数错误」——
该分支**在真实环境从未被验证**。属**未验证**，非已证伪。

**建议**：用一条**真实存在 wallet** 的用例补齐 409 实测证据。

---

### 问题 8：`GET /base/captcha` 返回 404（**非缺陷**，易误判）[Minor]

```powershell
GET http://127.0.0.1:8888/base/captcha   # => HTTP 404
GET http://127.0.0.1:8080/api/base/captcha  (GET)  # => 404
POST http://127.0.0.1:8080/api/base/captcha # => 200 {"code":0,"data":{"captchaId":"sHjc...","picPath":"data:image/png;base64,..."}}
```

`sys_base.go:15` = `baseRouter.POST("captcha", ...)`；前端 `api/user.js:20` 亦为 `method: 'post'`。
**前后端一致，无缺陷**；但 GET 探测得 404 会误导排障，建议在文档中显式标注。

---

### 问题 9：代理 `NODE_ROUTES` 含 `ttl-status`，前端却无对应封装 [Minor]

- 代理：`_gva_proxy.cjs:31-35` ⇒ `['/dashboard/device-versions','/dashboard/collect-summary','/dashboard/ttl-status']`
- 前端：`api/dashboard.js` **全文 25 行**，仅 `getDeviceVersions` / `getCollectSummary`，**无 ttl-status**

⇒ 代理多出一条**无消费者**的 Node 路由（多余暴露面）。实测该端点确实可匿名取数（596 字节）。

---

### 问题 10：`VITE_SERVER_PORT=8888` 与实际拓扑不符 + 注释乱码 [Minor]

```
.env.development:  VITE_CLI_PORT = 8888 / VITE_SERVER_PORT = 8888 / VITE_BASE_API = /api
                   // 濡傛灉浣跨敤docker-compose寮€鍙戞ā寮?..   ← GBK 被当 UTF-8 读，乱码
.env.production:   VITE_SERVER_PORT = 8888 / VITE_BASE_API = /api
```
`VITE_SERVER_PORT=8888` 暗示「直连 Go」，但 Go 路由是**裸路径**，而 axios 发的是 `/api/*`
⇒ **直连 8888 必然全 404**，**必须**经 8080 剥离 `/api`。该变量语义误导。

---

## 3 · 已验证正常的项（表）

| 项 | 验证方式 | 结果 |
|---|---|---|
| **C-1** chain 词表 | 实测 `/app/wallet-status?chain=btc` ⇒ `code:7 "未匹配到 wallet... chain=btc"`；`chain=zzz` ⇒ `code:7 "不支持的 chain: \"zzz\""`；`chain=tron` ⇒ 消息中显示 **`chain=trx`**（归一已发生） | ✅ **一致**（`eth` 不归一、`tron→trx`、`btc`/词表外显式失败） |
| **C-1** `normalizeChain` 实现 | `service/app/collect_result.go:319-329`（`tron→trx`、`btc→error`、default→error）；`collect_lock.go:51` 复用同一实现 | ✅ **一致**（单一事实来源） |
| **C-2** `/app/*` 端点集 | `router/app/public.go:31-35`：`wallet-status` / **`bill-list`** / `collect-lock` / `collect-release` / `collect-result`（后 4 者在 `InitAuthRouter`，带 `ServiceTokenAuth()`） | ✅ **一致**（含 T22 新增） |
| **C-2** 鉴权 Header | `middleware/service_token.go:24-25` ⇒ `global.GVA_CONFIG.AppJwt.ServiceToken` + `c.GetHeader("X-Service-Token")` | ✅ **一致** |
| **C-2** 恒 200 + body `code` | `api/v1/response/response.go:34` ⇒ `c.JSON(http.StatusOK, ...)`；实测 Go 业务失败均为 **HTTP 200 + code:7** | ✅ **一致** |
| **C-2** 同名文件陷阱 | `api/v1/app/collect_lock.go` `StatusConflict` **count=1**（位于 `:47`）；契约要求写全路径 | ✅ **锚点成立** |
| **C-3** `entries` 项数 | 本次域 A 未覆盖（属产物侧静态断言，见 §4） | ⏸ **未验证** |
| **C-4** `srcDir` 指向 (b) | 本次域 A 未覆盖（构建期议题） | ⏸ **未验证** |
| **C-5** 副本 sha256/bytes | 实测 `build/services/chain-router.js` = `cbdd2813…` / **9131** ✅；另两份 = `5714611b…` / **6087** ✅ | ✅ **与契约逐字一致** |
| `contracts.md` 自身 | `sha256 = f80a2ead6736d5f5aff70e72e3aa7de1c7cc63f93a604fb6eeb4a163059f925c` / **7624** bytes | ✅ 与 T19 报告所记 `f80a2ead…` **一致**（未被改动） |
| **T22** Go 端点 | `GET :8888/app/bill-list?limit=1` 带 token ⇒ `code:0 total:33 list_len=1`；不带 token ⇒ **401** | ✅ **真合并、不裸奔** |
| **T22** Node 合并逻辑 | `dashboard-versions.js:71-118`：`merged = gasleakTotal + qiankeTotal`，`sources`/`scope` 按实际切换；实测 `total:39, gasleak:6, qianke:33, scope:"gasleak+qianke"` | ✅ **真合并（非仅声明）** |
| **T22** 降级分支 | `:113-115` `limitation` 仅在 `qiankeTotal===null` 时非 null；实测双侧齐备 ⇒ `limitation:null` | ✅ 逻辑正确 |
| **Node 自身鉴权** | 直连 `:3000` 三端点无 Cookie ⇒ **401 `{"error":"未授权"}`** | ✅ **Node 侧未裸露** |
| **前端↔Go 路由对齐** | 29 处 `/device/*` 调用 vs Go 30 条路由 ⇒ **缺失 0 条** | ✅ 无 404 风险 |
| **前端 dist 已含 T22** | `dist/js/gin-vue-admin-collectSummary.*.js` 内含 `collect-summary`/`sources`/`潜客` | ✅ **构建产物与源码一致** |
| **`/api/api/*` 双前缀** | `api/api.js` url=`/api/getApiList` + baseURL `/api` ⇒ `/api/api/getApiList`；代理剥一层 ⇒ `/api/getApiList` ⇒ Go `sys_api.go:24` | ✅ **链路自洽** |
| 六端口全在线 | `Get-NetTCPConnection`：3000/8080/8888/13306/16379/27018 全部 Listen | ✅ |

---

## 4 · 未覆盖 / 未验证（**必须写**）

| # | 未覆盖项 | 原因 | 需要的证据 |
|---|---|---|---|
| 1 | **C-3 `entries` 恰 15 / darksword 恰 5** | 属**产物侧静态断言**（`chain-router.js` 的链模块计数），非 HTTP 契约；本次域 A 聚焦运行链路 | `verify_entries_coruna.mjs` / `verify_i1c2_darksword_entries.mjs` 的真实退出码与计数输出 |
| 2 | **C-4 `srcDir` 指向 (b)** | 属**构建期**议题（`build_unified.ps1` 同源产出两处），无运行时可观测点 | 两处副本的 sha256 是否相等 + 构建脚本改动落点 |
| 3 | **`collect-lock` 冲突 ⇒ HTTP 409** | 测试库中无匹配 wallet，**409 分支代码存在但从未被触达**（见问题 7） | 一条**真实 wallet** 的冲突用例实测 409 |
| 4 | **Go 管理台的完整登录链路** | captcha 使用 `base64Captcha.DefaultMemStore`（`sys_captcha.go:14`，**进程内内存**），验证码答案**无法从外部读取**（Redis 仅 1 个 `blacklist:jti:*` 键，实测） | 浏览器端交互式登录截图/录屏，或改用可复现的 captcha 旁路 |
| 5 | **Node 登录后的 RBAC 分支** | 本次仅验证「无 token ⇒ 401」；`auth.js:69-82` 的 menuKey 权限判定**未覆盖**（需非 admin 账号） | 普通角色账号的 403/放行矩阵 |
| 6 | **真实 docker 环境部署验证** | `08-infra/README.md:65-66` 明确「push/部署一律未授权」；本地**未起 docker** | 真实 compose up 后按 nginx 规则的路由断言 |
| 7 | **`etcd`/多实例下的 captcha 与 session 一致性** | `sys_captcha.go:12-13` 注释即指出多服务器需换 Redis 存储，当前为内存 ⇒ **多实例不可用**；未实测多实例 | 多副本部署下的登录一致性测试 |
| 8 | **AI 复核 / 未审区域的端点** | 本次仅核对 `03-web-admin/src/api/*` 与两个后端路由；`04-landing`、`05-ios`、`11-payment` 的调用面**未纳入** | 分域审核 B/C |
| 9 | **问题 1 的真实可达性边界** | 8080 监听 `0.0.0.0`（`_gva_proxy.cjs:202`），但**未验证**从其他主机/防护规则后的实际可达性 | 网络层探测（是否被防火墙/WAF 收敛） |

---

## 5 · ★ 我这一路为什么可能漏（本审核方法的局限）

1. **「能跑」与「可上线」被运行态掩盖**。
   六个端口全在线、端到端返回真实数据，**极易让人得出「链路通了」的结论**。
   本次若不**主动直连 3000 与 8888 做对照**，就**永远发现不了**问题 1（桥接旁路）与问题 4（双体系不通）——
   因为经 8080 的一切请求**都恰好是 200**。**是「对照实验」而非「正向验证」暴露了缺陷。**

2. **我审的是「当前进程」，不是「部署产物」**。
   运行中的 Node 加载的是 `X:\_integration\_fix_work\_i1c3_ws\.env`（树外），
   Go 二进制位于 `X:\_integration\_fix_work\_i2c1_server.exe`（树外，mtime 2026-10-02 14:03）。
   ⇒ **「树内源码 → 树外运行态」的对应关系我无法完全证明**：
   树内 `01-backend-go/router/app/public.go` 有 `bill-list`，且运行态确实响应 `bill-list`，
   这是**强证据**但**非编译溯源**。若树外二进制与树内源码有未提交差异，**本次审核不会发现**。

3. **C-1…C-5 的「一致」是**抽样**一致，不是穷举一致**。
   C-1 我验了 `tron/btc/zzz` 三个值，但**未穷举**全部词表边界（如大小写、空白、`eth,bsc` 混合串）。
   C-5 我核对了 3 个副本的 sha256，但**未验证**「运行时实际加载的是哪一份」。

4. **409 这类「分支契约」天然难以被无状态探测覆盖**。
   我的探针无法构造出「真实存在的 wallet + 并发占位」这一前置条件，
   ⇒ **只能标注「未验证」而非「已证伪」**。这是**方法的天花板**，不是被测对象的缺陷。

5. **「未登记」类的发现依赖穷举比对，容易漏**。
   问题 3（8080 未登记）是通过**主动 grep `残余暴露面登记.md`** 得到的。
   若某设施的名称与文档用词不一致（例如文档写作「测试用静态服务」），**同样的 grep 就会漏掉**。

6. **域名/Host 维度几乎未覆盖**。
   nginx 的 `ADMIN_DOMAIN` 按 Host 分流，而我的全部探测都基于 `127.0.0.1 + 端口`，
   **绕过了 Host 判定**。⇒ 真实域名下的行为（含证书、CORS、`X-Forwarded-*`）**本次未验证**。

7. **我只看了「读」路径的契约，写路径只做了浅探**。
   `collect-lock`/`collect-result` 的**写副作用**（占位泄漏、幂等键、分账落库）属域 A 边界之外，
   本次仅验证了「鉴权与响应形态」，**未验证数据正确性**。

---

## 6 · 建议的下一步（按优先级）

1. **[Blocker-1]** 立即处理 8080 的 token 桥接：改为透传凭证，或下线该路由；若短期无法改，**登记为 R-13 并限制来源 IP**。
2. **[Blocker-2]** 按 F1-C6 停靠点 1 取得 Owner 裁决，在 nginx 补 `/api/dashboard/` → Node 或选定 a1–a4 方案。
3. **[Major-4]** 决定登录体系归属：**收敛为一套**，或明确前端需双会话。
4. **[Major-5]** 把 `QIANKE_SERVICE_TOKEN`/`QIANKE_API_BASE` 落进 `08-infra` 部署配置。
5. **[Major-7]** 补 `collect-lock` 409 的真实冲突用例证据。
6. 其余 Minor/Info 随版本迭代清理。

---

*本报告未修改任何产物文件。所有探针脚本位于 `_fix_work/`：`a_scan_api.py`、`a_node_probe.py`、`a_go_probe.py`、`a_proxy_probe.py`、`a_e2e_probe.py`、`a_jwt_matrix.py`、`a_real_login.py`。*
