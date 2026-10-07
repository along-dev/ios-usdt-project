# 审核 D：前端可用性

> **审核角色**：审核 Agent（**只审不改**）
> **审核对象**：`03-web-admin`（gin-vue-admin 后台）· `03-web-admin/static/admin_dashboard.html`（v21998 管理台）
> **审核口径**：**「可上线」** —— 核实**每个页面真的能用**，**不是「能编译」**
> **实测时间**：本轮
> **唯一写入**：本报告 + `_d5e1_work/` 下的临时脚本与实测产物（**未改任何产物文件**）
>
> **★ 审核纪律声明**：本轮**未修改** `01-backend-go/**`、`03-web-admin/**`、`04-landing/**`、
> `02-backend-node/**` 或任何配置；所有结论均来自**运行时实测**或**源码只读**。

---

## 0 · 结论摘要

### 0.1 一句话结论

**34 条菜单的页面组件【全部存在且全部能被路由匹配】（34/34）**，
**首屏数据链路【33/34 通】** ——
**唯一断链的是 `privatewallet` 页（`device/wallet_list` 缺前导斜杠 ⇒ 拿到 HTML ⇒ 页面表格无数据）**。

★ **但**「可上线」口径下另有 **1 条 [Major] 契约缺陷**：
**8080 代理把 Node 侧 401 包装成 `code:0`**，
⇒ 前端拦截器**把「未授权」当成功放行**，
⇒ **T19 两个看板恒显示「暂无数据」**（因两页有 `catch` + 空态兜底，**不崩、不弹错，故属静默失效**）。

**v21998 管理台（`admin_dashboard.html`）本身可用**：
登录 302 + cookie ✅、dashboard 页 200 ✅、**19 张预览图 19/19 真实 PNG ✅**；
**34 个 `/landing-pages/` 内页配图 34/34 全部 404**（**= 已登记的 R-11，非新问题**）。

### 0.2 分档统计（实测）

| 维度 | 结果 |
|---|---|
| **菜单条数**（`sys_base_menus`） | **34**（10 顶层 + 24 子）✅ 与已知事实一致 |
| **component 文件存在** | **34/34** ✅ |
| **`asyncRouter.js` glob 匹配** | **34/34，0 失败** ✅ |
| **首屏 API 实测通过**（`code===0`） | **33/34** |
| **首屏 API 实测失败** | **1**（`privatewallet`）|
| **★ 无任何数据源的页面** | **3**（`customerfinance` / `commissionsettings` / `currencysettings`）|
| **T19 看板数据（经代理）** | **0/2**（401 被包成 `code:0`）|
| **T19 看板数据（直连 Node，带正确 cookie）** | **2/2 ✅**（含 T22 的 `sources:{gasleak:6,qianke:33}`）|
| **管理台 19 张预览图** | **19/19 = 200 image/png** ✅ |
| **管理台 `/landing-pages/` 内页配图** | **0/34 = 404**（**R-11 已登记**）|
| **脚手架残留页面混入业务菜单** | **0**（R-08 预期在 e2e 库不出现，实测确为 0）✅ |
| **未防护的 `res.data.X` 解包** | **42 处**（**可用性风险面**，见 §3.4）|

### 0.3 问题分档

| 严重度 | 数量 | 是否新问题 |
|---|---|---|
| **[Blocker]** | **0** | —— |
| **[Major]** | **3** | 3 新 |
| **[Minor]** | **3** | 部分新 |
| **[Info]** | **3** | —— |

★ **无 [Blocker]** 的依据：**34 条菜单全部可打开**、**34 个 component 全部命中**、
失败项**不导致整页白屏或崩溃**（`privatewallet` 仅表格空；T19 看板有空态兜底）。

★ **但须明确**：「可打开」**≠「可用」**。
**D-02b 的 3 个页面（`customerfinance` / `commissionsettings` / `currencysettings`）
虽能正常打开且不报错，但【没有任何数据源】，是"能跑的空壳"** ——
在**「可上线」口径下应按不可用计**。

---

## 1 · 问题清单（表）

| # | 严重度 | 问题 | 位置（证据） | 影响 | 状态 |
|---|---|---|---|---|---|
| **D-01** | **[Major]** | `device/wallet_list` **缺前导斜杠** ⇒ axios 拼成 `/apidevice/wallet_list` ⇒ 代理按**静态路径**返回 `index.html` | `src/api/index.js:29` | `privatewallet` 页**表格恒空**，且控制台无 4xx（**静默**）| **新** |
| **D-02** | **[Major]** | 代理把 Node 的 **401 包装为 `code:0`** ⇒ 拦截器**当成功放行** | `_gva_proxy.cjs:166` + `request.js:66` | **T19 两个看板恒显示「暂无数据」**，用户**看不到任何错误** | **新** |
| **D-02b** | **[Major]** | **3 个菜单页是「无数据源的原型壳」**（无 `@/api`、无 `onMounted`、硬编码假数据）| §3.5 三处证据 | **页面能开、能渲染，但【完全不可用】**（假地址、假表、按钮无响应）| **新** |
| **D-03** | **[Minor]** | 代理 **token 桥接无重试/无并发去重**（Node 并发 login 会 500）| `_gva_proxy.cjs:42-88` | 两个看板**长时间不可恢复** | **新** |
| **D-04** | **[Minor]** | **42 处** `res.data.X` 无 `?.`/判空防护 | 见 §3.4 清单 | 任一后端形状变化 ⇒ `TypeError` ⇒ 该页**部分渲染中断** | 新（面） |
| **D-05** | **[Minor]** | `dist/` **不含 `static/`**，`favicon.ico` 404 | `dist/` 顶层 = `gva,js,assets,index.html` | `favicon` 破图；**管理台静态资源不在 8080 上** | 新 |
| **D-06** | **[Info]** | 34 个 `/landing-pages/` 内页配图 **404** | `admin_dashboard.html` 引用 | **点进模板内页配图破图** | **= R-11 已登记** |
| **D-07** | **[Info]** | 5 个脚手架管理页（`api`/`menu`/`user`/`dictionary`/`operation`）在业务菜单中 | `sys_base_menus` | **功能正常**，非破损 | **= R-12 已登记** |
| **D-08** | **[Info]** | 22 个 `view/**` 页面未被任何菜单引用 | §5 清单 | 均为 layout/login/error/子组件，**合理** | 非问题 |

---

## 2 · ★ 逐页状态表

> **实测方法**：从 `src/api/*.js` **自动解析**每个函数的 `url`/`method`（**不手填**），
> 再从各 `.vue` 的 `onMounted` **沿调用链下钻**到真实 API 函数，
> 最后**完全复刻 axios 拼接**（`baseURL='/api'` + `url`）打到 **8080 代理**，
> 并按 `request.js:66` 的 `response.data.code === 0` 判定。

### 2.1 顶层 10 菜单 + 子菜单（★ 首屏只读路径）

| # | 菜单 | component | 页面存在 | 它调的 API | 在哪个后端 | 实测结果 | 问题 |
|---|---|---|---|---|---|---|---|
| 1 | `dashboard` | `view/dashboard/index.vue` | ✅ | （首屏无 API，纯静态/子组件）| — | N/A | — |
| 2 | `admin`(superAdmin) | `view/superAdmin/index.vue` | ✅ | （容器页，无 API）| — | N/A | — |
| 3 | `authority` | `view/superAdmin/authority/authority.vue` | ✅ | POST `/authority/getAuthorityList` | Go 8888 | **200 `code=0`** ✅ | — |
| 4 | `menu` | `view/superAdmin/menu/menu.vue` | ✅ | POST `/menu/getMenuList`、`/authorityBtn/canRemoveAuthorityBtn` | Go 8888 | **200 `code=0`** ✅ | — |
| 5 | `api` | `view/superAdmin/api/api.vue` | ✅ | POST `/api/getApiList` | Go 8888 | **200 `code=0`** ✅（`list:[]`）| — |
| 6 | `user` | `view/superAdmin/user/user.vue` | ✅ | POST `/user/getUserList`、`/authority/getAuthorityList` | Go 8888 | **200 `code=0`** ✅ | — |
| 7 | `dictionary` | `view/superAdmin/dictionary/sysDictionary.vue` | ✅ | GET `/sysDictionary/getSysDictionaryList` | Go 8888 | **200 `code=0`** ✅ | — |
| 8 | `dictionaryDetail`(hidden) | `.../sysDictionaryDetail.vue` | ✅ | GET `/sysDictionaryDetail/getSysDictionaryDetailList` | Go 8888 | **200 `code=0`** ✅ | — |
| 9 | `operation` | `.../operation/sysOperationRecord.vue` | ✅ | GET `/sysOperationRecord/getSysOperationRecordList` | Go 8888 | **200 `code=0`** ✅ | — |
| 10 | `resource` | `view/resourceManagement/index.vue` | ✅ | （容器页）| — | N/A | — |
| 11 | `infoList` | `.../infoList/index.vue` | ✅ | POST `/device/agent_device_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 12 | `walletinfo` | `.../CustomerWalletinfo/index.vue` | ✅ | GET `/device/agent_list` + POST `/device/custom_wallet_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 13 | `proxywallet` | `.../ProxyWalletInfo/index.vue` | ✅ | POST `/device/agent_wallet_list` | Go 8888 | **200 `code=0`** ✅ | — |
| **14** | **`privatewallet`** | `.../Privatewallet/Privatewallet.vue` | ✅ | GET `/device/agent_list` ✅ + **POST `device/wallet_list`** | Go 8888 | **★ 失败：返回 HTML** | **D-01 [Major]** |
| 15 | `installation` | `.../InstallationList/InstallationList.vue` | ✅ | POST `/device/list` + GET `/device/agent_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 16 | `walletinformation` | `.../walletinformation/walletinformation.vue` | ✅ | POST `/device/private_wallet_list` + `agent_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 17 | `address` | `view/addressmanagement/index.vue` | ✅ | GET `/device/system_address` + `/device/token_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 18 | `addr-agent` | `view/addressmanagement/agent.vue` | ✅ | GET `/device/agent_payment_address` + `token_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 19 | `addr-manage` | `view/addressmanagement/manage.vue` | ✅ | GET `/device/payment_address` + `token_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 20 | `agent`(代理列表) | `view/agentList/index.vue` | ✅ | POST `/device/agent_tabulation` + GET `/device/get_packet_info` | Go 8888 | **200 `code=0`** ✅ | — |
| 21 | `finance` | `view/financialManagement/index.vue` | ✅ | （容器页）| — | N/A | — |
| 22 | `privatedomain` | `.../Privatedomainaccounts.vue` | ✅ | POST `/device/custom_financial` + `token_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 23 | `agencyincome` | `.../agencyincome.vue` | ✅ | POST `/device/agent_financial` + `token_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 24 | `customerfinance` | `.../customerfinance.vue` | ✅（98 B）| **★ 无任何 API** | — | **N/A：整页只渲染字面量 `111`** | **D-02b [Major]** |
| 25 | `platformrevenue` | `.../platformrevenue.vue` | ✅ | POST `/device/financial` + `token_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 26 | `syscfg` | `view/systemconfiguration/index.vue` | ✅ | （容器页）| — | N/A | — |
| 27 | `commissionsettings` | `.../commissionsettings.vue` | ✅（3.9 KB）| **★ 无任何 API** | — | **N/A：静态原型 + 写死假地址** | **D-02b [Major]** |
| 28 | `currencysettings` | `.../currencysettings.vue` | ✅（1.2 KB）| **★ 无任何 API** | — | **N/A：静态原型，无保存** | **D-02b [Major]** |
| 29 | `projectmanagement` | `.../projectmanagement.vue` | ✅ | GET `/device/packet_list` | Go 8888 | **200 `code=0`** ✅ | — |
| 30 | `state` | `view/system/state.vue` | ✅ | POST `/system/getServerInfo` | Go 8888 | **200 `code=0`** ✅ | — |
| 31 | `about` | `view/about/index.vue` | ✅ | （纯静态页）| — | N/A | — |
| 32 | `person`(hidden) | `view/person/person.vue` | ✅ | PUT `/user/setSelfInfo` | Go 8888 | **200 `code=0`** ✅ | — |
| **33** | `deviceVersions` | `.../deviceVersions/deviceVersions.vue` | ✅ | GET `/dashboard/device-versions` | **Node 3000** | **★ 401→`code:0`** | **D-02 [Major]** |
| **34** | `collectSummary` | `.../collectSummary/collectSummary.vue` | ✅ | GET `/dashboard/collect-summary` | **Node 3000** | **★ 401→`code:0`** | **D-02 [Major]** |

**小计**：**34/34 页面存在且路由可解析**；**33/34 首屏链路可用**；**1 条失败（#14）**；**2 条被 D-02 影响（#33/#34）**。

### 2.2 关键实测原始输出

**（a）#14 `privatewallet` —— D-01 复现**

```
$ # axios: baseURL='/api' + url='device/wallet_list'
GET/POST http://127.0.0.1:8080/apidevice/wallet_list
  => HTTP 200  Content-Type: text/html; charset=utf-8
  => <!DOCTYPE html><html lang="en"><head><meta charset="utf-8">…
$ POST http://127.0.0.1:8080/api/device/wallet_list     （正确写法）
  => HTTP 200  Content-Type: application/json
  => {"code":0,"data":{"list":[],"page":1,"pageSize":10,"total":0,"totalRevenue":"0"},"msg":"success"}
```

**（b）#33/#34 —— D-02 复现（经 8080）**

```
GET http://127.0.0.1:8080/api/dashboard/collect-summary   (x-token=<Go admin JWT>)
  => HTTP 401
  => {"code":0,"data":{"error":"未授权"},"msg":"ok"}      ← ★ 401 被改写成 code:0
```

**（c）同一端点【直连 Node 3000 带正确 cookie】—— 数据完全正常**

```
GET http://127.0.0.1:3000/api/dashboard/collect-summary   (Cookie: accessToken=<Node JWT>)
  => HTTP 200
  => {"data":{"total":39,"confirmed":4,"pending":2,
              "chains":{"btc":2,"eth":2,"tron":2},
              "sources":{"gasleak":6,"qianke":33},     ← ★ T22 双侧合并已生效
              "scope":"gasleak+qianke","limitation":null}}

GET http://127.0.0.1:3000/api/dashboard/device-versions
  => HTTP 200
  => {"data":[{"platform":"android","version":"13","total":3,"success":2,"rate":0.6667},
              {"platform":"ios","version":"18.5","total":3,"success":2,"rate":0.6667}, …]}
```

### 2.3 v21998 管理台（`admin_dashboard.html`）状态表

| 项 | 实测 | 结论 |
|---|---|---|
| `GET /mgr-admin-8bcde2021d98/login` | **200** HTML（3187 B，含 `<form`）| ✅ |
| `POST /mgr-admin-8bcde2021d98/login` | **302** + **2 条 Set-Cookie**（`accessToken` + `refreshToken`）| ✅ |
| `GET /mgr-admin-8bcde2021d98/dashboard`（带 cookie）| **200** HTML（**60 126 B**）| ✅ |
| `GET /mgr-admin-8bcde2021d98/dashboard`（无 cookie）| **401** | ✅ 受保护 |
| **19 张模板预览图** `/images/template-previews/*.png` | **19/19 = 200 · `image/png` · 真实 PNG 魔术字节** | ✅ **T21 成果确认** |
| **34 个 `/landing-pages/` 内页配图** | **34/34 = 404**（磁盘源**不存在**）| **= R-11 已登记** |
| `admin_dashboard.html` 自身（8080 的 `/static/` 下）| **404** | 见 §4 / §5（**非部署路径**）|

---

## 3 · 逐条详述

### D-01 [Major] · `device/wallet_list` 缺前导斜杠 ⇒ `privatewallet` 页静默无数据

**现象**
进入【资源管理 → 私域钱包】（`privatewallet`）后，**表格恒为空**，
且**浏览器控制台没有任何 4xx/5xx**（**因服务端返回的是 200**）。

**复现**

```powershell
# 1) 看源码（缺前导斜杠）
Select-String -Path "E:\USDT项目\03-web-admin\src\api\index.js" -Pattern "wallet_list"
#  01-backend-go 对应 src/api/index.js:28  url: 'device/wallet_list'   ← 无 "/"

# 2) 复刻 axios 拼接（baseURL='/api' + url 直接相加）
Invoke-WebRequest -Uri "http://127.0.0.1:8080/apidevice/wallet_list" -Method POST `
  -Headers @{"x-token"=$TOK; "Content-Type"="application/json"} -Body "{}"
#  => 200  Content-Type: text/html   ← ★ 返回的是 index.html
```

**根因（三层叠加）**

1. `src/api/index.js` 的 `walletlist` 写作 `url: 'device/wallet_list'`（**缺 `/`**），
   而**同文件其余 30 个函数均为 `/device/...`** ⇒ **孤例**；
2. axios 的 `baseURL='/api'` 与相对 `url` **直接字符串相加**（非 `new URL()` 语义），
   故得 `/apidevice/wallet_list`；
3. 8080 代理的 `serveStatic` 对**无扩展名**路径做 **SPA fallback**（`_gva_proxy.cjs:119-129`），
   于是把 `index.html` 以 **HTTP 200 `text/html`** 返回。
   ⇒ axios 尝试 JSON 解析 HTML 失败 ⇒ `response.data` 是**字符串** ⇒ `.code` 为 `undefined`。

**影响**

| 项 | 说明 |
|---|---|
| 用户可见 | `privatewallet` 页**表格恒空**（`PrivateDomainlist.value = res.data.list` ⇒ `undefined`）|
| 隐蔽性 | ★★ **高** —— 服务端 200、无红色报错、无 404；只有 `.data.list` 取不到值 |
| 波及面 | **仅此 1 页**（其它 33 页已实测通过）|
| 是否存在同类 | ★ 全库扫描：`url:` 不以 `/` 或 `http` 开头者**仅此 1 处**（见 §5 验证方法）|

**建议（择一，均为一字符改动）**

- **(a) 改前端（推荐）**：`src/api/index.js` 的 `url: 'device/wallet_list'` → `'/device/wallet_list'`；
- **(b) 改代理**：`serveStatic` 对 `/api*` 之前的路径**不做 SPA fallback**
  （即 `req.url` 以 `/api` 开头时若命中静态分支则直接 404），使该缺陷**显性化**。

★ **注**：**仅 (a) 或 (b) 之一不足以完全闭环** —— 建议 **(a) 修数据 + (b) 修可观测性**。

**验证方法**

```powershell
# 修复后：应返回 JSON 而非 HTML
Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/device/wallet_list" -Method POST `
  -Headers @{"x-token"=$TOK; "Content-Type"="application/json"} -Body '{"page":1,"pageSize":10}'
# 预期：200 application/json，且 code=0、data.list 为数组
```

---

### D-02 [Major] · 代理把 Node 401 包装成 `code:0` ⇒ 拦截器把「未授权」当成功

**现象**
【首页看板 → 设备版本】与【归集汇总】两页**恒显示「暂无数据」**，
**不弹任何错误**，用户**无从判断是"真的没数据"还是"取数失败"**。

**复现**

```powershell
# 经 8080 代理（Go 的 admin JWT 已带上）
Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/dashboard/collect-summary" `
  -Headers @{"x-token"=$TOK}
#  => HTTP 401
#  => {"code":0,"data":{"error":"未授权"},"msg":"ok"}     ← ★ 关键
```

**根因**

`_gva_proxy.cjs:152-171` 为**适配 gin-vue-admin 的拦截器**，对
`NODE_ROUTES`（3 条）的响应**无条件**包一层 `{"code":0,"data":…,"msg":"ok"}`：

```js
// _gva_proxy.cjs:164-167
if (j && typeof j === 'object' && !('code' in j)) {
    out = JSON.stringify({ code: 0,
        data: j.data !== undefined ? j.data : j,
        msg: 'ok', … });
}
```

**但包装【未区分状态码】**：
Node 的 **401 `{"error":"未授权"}`**（无 `data` 字段）⇒ 落入 `data: j`
⇒ 变成 **`{"code":0,"data":{"error":"未授权"},"msg":"ok"}`**。

而前端 `request.js:66` 的判据正是：

```js
if (response.data.code === 0 || response.headers.success === 'true') {
    return response.data          // ★ 放行 —— 401 也被放行
}
```

⇒ **两层缺陷叠加**：
**① 代理抹掉了 401 的语义**；**② 拦截器只看 `code`，不看 HTTP 状态**。

**影响**

| 项 | 说明 |
|---|---|
| 受影响页面 | **`deviceVersions`、`collectSummary`**（2 页）|
| 用户可见 | **恒「暂无数据」** —— 与"真的没数据"**外观完全一致**（★ 静默失效）|
| 是否崩溃 | **否** —— 两页均有源级防护：`Array.isArray(res?.data) ? res.data : []`（`deviceVersions.vue:59`）与 `res?.data \|\| {}`（`collectSummary.vue:88`）|
| 是否弹错 | **否** —— `catch` 仅在**抛异常**时触发（`ElMessage('设备版本加载失败')`），而 `code:0` 放行**不抛异常** |
| 严重度判据 | ★ 因**不崩、有兜底** ⇒ **[Major] 而非 [Blocker]**；但**「可上线」口径下数据不可见即不可用** |

**★ 与 T19 已知案例的关系（重要澄清）**

> 题目所述 T19 案例为：*拦截器要求 `response.data.code === 0`，Node 响应形如 `{"data":{…}}` 无 `code` ⇒ 页面拿到 `undefined`*。
>
> **本轮实测的结论比该描述更精确**：
> - 代理**确已加包装**（`_gva_proxy.cjs:155-173`），故 **`code` 不再是 `undefined`** ⇒ **T19 的原始症状已不成立**；
> - **但包装引入了【新】缺陷**：**把 401 也包成 `code:0`** ⇒ **从"拿到 undefined"变成"拿到看似成功的错误体"**。
> - ⇒ **这是 T19 修复方案的副作用（regression）**，**不是原 T19 缺陷的复现**。

**建议**

- **(a) 代理侧（推荐，最小改动）**：包装时**透传状态码语义**：

```js
// _gva_proxy.cjs，替换 :164-167 的包装分支
if (pres.statusCode >= 400) {
    // ★ 失败响应不包装（或包装为 code=pres.statusCode），保留 HTTP 状态
    out = JSON.stringify({ code: pres.statusCode, data: j, msg: (j && j.error) || 'error' });
} else if (j && typeof j === 'object' && !('code' in j)) {
    out = JSON.stringify({ code: 0, data: j.data !== undefined ? j.data : j, msg: 'ok', … });
}
```

- **(b) 前端侧（根治，但属产物改动）**：`request.js:66` 增补 **HTTP 状态**判据
  （如 `response.status >= 200 && response.status < 300` 才视为成功）；
- **(c) 桥接侧**：见 **D-03**（桥接失败是 401 的**直接成因**）。

**验证方法**

```powershell
# 修复后：401 不应再是 code:0
Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/dashboard/collect-summary" -Headers @{"x-token"=$TOK}
# 预期：code != 0（如 code=401），前端因此走 else 分支并 ElMessage 报错
```

---

### D-02b [Major] · 3 个菜单页是「无数据源的原型壳」（能开、能用，但**没有任何真实数据**）

**现象**
下列 3 个菜单页**可以正常打开、不报错、无破图**，**但页面内容是【源码里写死的】**：

| 菜单 | component | 实际内容 | 是否可提交/保存 |
|---|---|---|---|
| **`customerfinance`**（客户财务）| `view/financialManagement/customerfinance.vue` | **整个页面只渲染字面量 `111`** | ❌ **无表单、无按钮** |
| **`commissionsettings`**（佣金设置）| `view/systemconfiguration/commissionsettings.vue` | 3 个输入框 + **写死的 6 行假地址表** `sdsnff7ef8sy8f7wy8fy38fh8373h7rhf8hr8` | ❌ **「添加地址」按钮只切换弹窗，无任何 API** |
| **`currencysettings`**（币种设置）| `view/systemconfiguration/currencysettings.vue` | 4 个输入框（BTC/USDT/ETH/BSC = __ USD）| ❌ **无保存按钮、无 API** |

**证据 1 —— `customerfinance.vue` 全文（98 字节，13 行）**

```vue
<template>
  <div>111</div>
</template>

<script>
export default {

}
</script>

<style>

</style>
```

**证据 2 —— 三页均【无 `@/api` 导入】（自动化核对）**

```
$ python _d5e1_work/fake.py
view/systemconfiguration/commissionsettings.vue      @api=False  命中=['假地址', 'Please input占位', 'v-for in 数字']
view/systemconfiguration/currencysettings.vue        @api=False  命中=['Please input占位']
view/financialManagement/customerfinance.vue         @api=False  命中=['字面111']
view/financialManagement/agencyincome.vue            @api=True   命中=['Please input占位']   ← 对照：真页面有 @/api
view/agentList/index.vue                             @api=True   命中=['Please input占位']   ← 对照：真页面有 @/api
```

**证据 3 —— `commissionsettings.vue` 的假数据与空按钮**

```vue
:31   <div class="t1" v-for="item in 6">          ← ★ 固定 6 行，非后端数据
:33     <span>sdsnff7ef8sy8f7wy8fy38fh8373h7rhf8hr8</span>   ← ★ 写死的假地址
:76   <div class="btns">添加地址</div>              ← ★ 无 @click ⇒ 点了没反应
:81   <script setup>
:82   import { ref } from "vue";
:84   const addAddress = ref(false)                 ← ★ 全部逻辑仅此一行
```

**根因**
这 3 页在开发期**只做了静态布局原型（UI mock）**，
**从未接入 `src/api/index.js` 的任何端点**，数据全部**内联在模板里**。
★ 与「脚手架残留」（R-12）**性质不同**：
R-12 的页面**功能正常**；**这 3 页是"业务功能未实现"**。

**影响**

| 项 | 说明 |
|---|---|
| 用户可见 | **页面看起来是正常业务页**（有标题、有输入框、有按钮）⇒ **极易被误判为已实现** |
| 实际能力 | **完全无法读写任何数据**；「佣金设置」与「币种设置」**改了也不会保存** |
| 危害等级 | ★ **比 D-01 更隐蔽** —— D-01 至少表格是空的，**这 3 页看起来是"满的"（假数据）** |
| 是否崩溃 | **否** —— 故不会被任何"构建/启动/冒烟"检查发现 |

**建议**

- **(a)** 若这 3 项属**本期交付范围** ⇒ **立卡实现**（接 `token_list` / `packet_list` 等既有端点，
  或在 Go 侧新增佣金/币种配置端点）；
- **(b)** 若**不属本期范围** ⇒ ★ **建议在 `sys_base_menus` 中 `hidden=1` 或下架这 3 条菜单**，
  **避免把"原型壳"当作"已交付功能"呈现给使用者**；
- **(c)** ★ **无论 (a)/(b)**，均应**删除 `customerfinance.vue` 中的字面量 `111`**
  （该字符串会**直接渲染给用户**，属**明显未完成标记**）。

**验证方法**

```powershell
# 确认三页无任何 @/api 导入（应输出 3 行为 False）
python _d5e1_work/fake.py
# 浏览器中打开这三页，改输入框后刷新 —— 数据不会保留（无持久化）
```

---

### D-03 [Minor] · 代理 token 桥接无重试/无并发去重（Node 并发 login 500）

**现象**
D-02 的 401 **持续存在且不自行恢复**（实测 **t+0s … t+25s 连续 6 次均 401**），
即使 Node 的 login 端点此刻**已恢复正常**。

**★ 先说结论（含一次自我纠正）**

我最初的假说是「代理把 `null` 写入 token 缓存 ⇒ 10 分钟锁死」。
**该假说被源码与实测共同推翻**：`_gva_proxy.cjs:84` 的判据是

```js
if (nodeTokenCache.token && Date.now() - nodeTokenCache.at < 10 * 60 * 1000) {
```

`null` 是**假值** ⇒ **不会命中缓存分支，会重新调用 `fetchNodeToken()`**。
⇒ **不存在"缓存 null 锁死 10 分钟"**。
**实际机制是【并发竞态 + 无重试 + 无 in-flight 去重】**（详见下方三段证据）。

**复现（三段证据）**

```powershell
# ① 直连 Node 顺序 20 次 login —— 全绿
#    node -e "...顺序 20 次 POST /api/auth/login..."
#    === 顺序 20 次: OK=20 FAIL=0 ===

# ② 直连 Node 并发 10 次 login —— 大量 500
#    === 并发 10 个 login ===
#      0 st=500 tok=NULL {"error":"服务器内部错误"}
#      2 st=200 tok=OK   {"user":{"userId":"6aba86b2…"}}
#      其余 8 条 st=500 tok=NULL
#    并发结果: OK=1 失败=9

# ③ 经 8080 反复请求（桥接应已恢复，实际未恢复）
#    t+ 0s -> 401 | {"code":0,"data":{"error":"未授权"},"msg":"ok"}
#    t+25s -> 401 | {"code":0,"data":{"error":"未授权"},"msg":"ok"}
```

**根因**

`_gva_proxy.cjs` 的 `nodeToken()`：

```js
// :73  失败时把 null 也写入缓存
nodeTokenCache = { token: tok, at: Date.now() };

// :84  判据只检查 token 为真值 —— 但【不为真时】会重新取
if (nodeTokenCache.token && Date.now() - nodeTokenCache.at < 10 * 60 * 1000) {
    return nodeTokenCache.token;
}
return await fetchNodeToken();
```

★ **精确结论（不夸大）**：
`nextToken()` 在 `token === null` 时**会重新调用** `fetchNodeToken()`（因为 `null` 为假值）。
⇒ **因此"缓存 null 导致 10 分钟锁死"这一表述【不成立】**，我最初的假设 **(B) 被自身证据推翻**。

**实际可复现的机制是【并发竞态 + 无重试】**：

1. 前端一次首屏可能**同时**发起多个 `NODE_ROUTES` 请求（两个看板 + `ttl-status`），
   ⇒ 代理**并发**调用 `fetchNodeToken()`；
2. Node 的 `/api/auth/login` 在**并发下大量返回 500**（实测 **9/10 失败**）；
3. 代理**每次请求都重新尝试**，但**每次都撞上并发 500** ⇒ **持续 401**；
4. 代理**无退避、无重试、无并发去重**（`fetchNodeToken` 无 in-flight 复用），
   ⇒ 表现为**长期不可用**。

★ **为何实测能持续 25 s 不恢复**：本轮探测本身（Python 串行 6 次）**不构成并发**，
但 Node 侧 500 是否与**其它并发来源**（如前端页面持续轮询/多次刷新）相关，**本轮未定位到 Root Cause**。
**⇒ 本条标注为"机制已确证、触发源未完全定位"**（**不猜测**）。

**影响**：D-02 的 401 **难以自愈**；两个看板**长期不可用**。

**建议**

- **(a)** `fetchNodeToken()` 增加**重试（含退避）**与 **in-flight 去重**（同一时刻只发一次 login）：

```js
let nodeTokenInflight = null;
function nodeToken() {
  if (nodeTokenCache.token && Date.now() - nodeTokenCache.at < 10*60*1000) {
    return Promise.resolve(nodeTokenCache.token);
  }
  if (!nodeTokenInflight) {
    nodeTokenInflight = fetchNodeToken().finally(() => { nodeTokenInflight = null; });
  }
  return nodeTokenInflight;
}
```

- **(b)** 根治：**调查 Node `/api/auth/login` 并发 500 的根因**
  （**这属 Node 侧缺陷，超出本次前端审核范围**，建议单独立卡）。

---

### D-04 [Minor] · 42 处 `res.data.X` 无判空防护

**现象**：任一后端响应形状不符 ⇒ **`TypeError`** ⇒ 该页 `onMounted` 链**在赋值处中断**
（`catch` 若存在则弹错；**若该函数无 `catch` 则表现为部分渲染/表格空白**）。

**证据（完整清单，42 处）**

| 文件 | 行 | 代码 |
|---|---|---|
| `view/agentList/index.vue` | 162 | `agentlist.value = res.data.list` |
| `view/agentList/index.vue` | 168 | `Agentproject.value = res.data.map(item => {` |
| `view/financialManagement/agencyincome.vue` | 207-209 | `Pagination.total` / `financialList.value` / `totalRevenue.value` |
| `view/financialManagement/platformrevenue.vue` | 222-224 | 同上三行 |
| `view/financialManagement/Privatedomainaccounts.vue` | 208-210 | 同上三行 |
| `view/resourceManagement/CustomerWalletinfo/index.vue` | 138, 165-167 | `res.data.map` / `res.data.list` / `total` / `totalRevenue` |
| `view/resourceManagement/infoList/index.vue` | 167-168 | `res.data.list` / `res.data.total` |
| `view/resourceManagement/InstallationList/InstallationList.vue` | 140, 165-166 | 同上 |
| **`view/resourceManagement/Privatewallet/Privatewallet.vue`** | **138, 165-167** | ★ **与 D-01 叠加 ⇒ 本条 1 处会被实际触发** |
| `view/resourceManagement/ProxyWalletInfo/index.vue` | 132-134 | `res.data.list` / `total` / `totalRevenue` |
| `view/resourceManagement/walletinformation/walletinformation.vue` | 138, 165-167 | 同上 |
| `view/superAdmin/api/api.vue` | 304 | `form.value = res.data.api` |
| `view/superAdmin/authority/components/apis.vue` | 49 | `const apis = res2.data.apis` |
| `view/superAdmin/authority/components/menus.vue` | 97, 99, 116, 157 | `res.data.menus` / `res.data.authority.defaultRouter` / `res.data.selected.forEach` |
| `view/superAdmin/dictionary/sysDictionary.vue` | 314 | `formData.value = res.data.resysDictionary` |
| `view/superAdmin/dictionary/sysDictionaryDetail.vue` | 224 | `formData.value = res.data.resysDictionaryDetail` |
| （其余见 `_d5e1_work/nullchk.py` 完整输出）| | |

**★ 对照：T19 两页【已做防护】**
`deviceVersions.vue:59` → `Array.isArray(res?.data) ? res.data : []`；
`collectSummary.vue:88` → `res?.data || {}`。
**⇒ 同一代码库内防护风格不一致**，这解释了为何 T19 两页"只是空"而 `privatewallet` 会取到 `undefined`。

**建议**：统一为 `res?.data?.list ?? []` 形式；或**在 `request.js` 拦截器成功后统一保证 `data` 存在**。

---

### D-05 [Minor] · `dist/` 不含 `static/`；`favicon.ico` 404

**证据**

```powershell
# dist 顶层
  gva/  js/  assets/  index.html          ← ★ 无 static/
# dist/index.html 的 6 个引用中唯一失败项
  favicon.ico => 404 text/plain
```

**判读**
`03-web-admin/static/` 是**构建输入**，`vite.config.js` **未将其 `copy` 进 `dist`**
⇒ 管理台（`admin_dashboard.html` / `admin_login.html`）**不在 8080 的服务面上**。
★ **这本身不是缺陷**（管理台由 **Node 3000** 提供，见 §2.3），
但 ⇒ **若有人误以为「8080 = 全部后台」会得到错误结论**。
`favicon.ico` 404 为**真实小瑕疵**。

**建议**：`vite.config.js` 增 `viteStaticCopy` 或 `publicDir`，或在 nginx/代理层显式映射 `/static`。

---

### D-06 [Info] · 34 个 `/landing-pages/` 内页配图 404（**= R-11，非新问题**）

**证据**

```powershell
# admin_dashboard.html 中 /landing-pages/ 引用（唯一）34 条
# 逐条实测（Node 3000）: 200 → 0 条 ; 404 → 34 条
# 磁盘核对: static/landing-pages/<n>/... 存在 0 / 34
# 抽样（引用模板 vs 磁盘目录）
#   引用有但磁盘无: chatee, gplayx, japapp, kuaibo, kyssap, promox,
#                   qiyoux, reelen, reelsh, secure, shortv, xhamst, xvidep …
#   磁盘有但引用无: igniti, livesp, premhd, smartr, stkval
# 04-landing 全树图片总数 = 4（其中仅 1 张为业务图 puzzle-bg.jpg）
```

★ **与 R-11 登记完全一致**（R-11：19 卡片预览图 ✅ 已生成 / **34 内页配图源不存在 ⇒ 404** / 52 CSS·JS ✅ 已展开）。
**⇒ 本条不重复开卡。**

**影响**：**点进模板内页时配图破图**；**19 张卡片预览图完全正常**（主要用途不受影响）。

---

### D-07 [Info] · 5 个脚手架管理页在业务菜单中（**= R-12，非新问题**）

**证据**：`sys_base_menus` 中 `component` 含 `view/superAdmin/{api,menu,user,dictionary,operation}/*`
—— 属 gin-vue-admin 自带管理页。**实测全部 200 `code=0`（功能正常）**。
★ R-12 已登记为**「功能正常、无害、保留」** ⇒ **不重复开卡**。

**★ 补充（有价值的澄清）**：R-12 原文列举的 `fileUploadAndDownload` / `excel` / `email` / `customer`
**在本库 `sys_base_menus` 中【不存在】**（关键词命中数均为 **0**）。
⇒ 二者口径差异：**R-12 列表包含"曾存在于脚手架"的项，而 e2e 库实际只有 5 项**。

---

## 4 · 静态资源 404 清单

### 4.1 汇总

| 来源 | 引用数 | 200 | 404 |
|---|---|---|---|
| `dist/index.html` | 6 | **5** | **1**（`favicon.ico`）|
| 管理台 19 张模板预览图 | 19 | **19** | **0** |
| 管理台 `/landing-pages/` 内页配图 | **34** | **0** | **34** |
| 管理台其它静态引用 | 0 | — | — |

### 4.2 「真正需要处理」的 404 清单

| # | 路径 | 说明 | 处置 |
|---|---|---|---|
| 1 | `/favicon.ico` | 8080 下 404 | **建议修**（D-05）|
| 2-35 | `/landing-pages/<tpl>/…`（**34 条**）| **源素材不存在** | **= R-11，不修** |

**34 条完整清单**

```
/landing-pages/bokepx/static/images/bg-111.jpg
/landing-pages/chatee/images/AA/bangladesh_user_037.webp
/landing-pages/cosern/images/girls/30.png
/landing-pages/cosply/images/girls/30.png
/landing-pages/dptvlx/static/picture/phone-mockup.png
/landing-pages/fizzio/static/picture/logo.jpg
/landing-pages/gplayx/static/picture/4.jpg
/landing-pages/hztvlx/static/picture/logo.png
/landing-pages/japapp/static/picture/app-icon.png
/landing-pages/kuaibo/static/picture/1-6.png
/landing-pages/kyssap/static/picture/bad_006.jpg
/landing-pages/lovely/static/image/changtu.jpg
/landing-pages/lustyl/static/picture/279_047.jpg
/landing-pages/meetic/static/picture/person1.jpg
/landing-pages/minidr/static/picture/img_1778428797_0113.webp
/landing-pages/nightm/static/images/img/img8.gif
/landing-pages/nightp/static/picture/1781402887823117833-app-icon.png
/landing-pages/noxxxt/static/images/Ao5pBFuWY32cVuh6iYjEjZMEscN.jpg
/landing-pages/paradx/static/picture/photo_2026-05-05_23-57-27.jpg
/landing-pages/phubxx/static/picture/11.png
/landing-pages/promox/static/picture/50a922b940088729f166a41c0e0a71a6.jpg
/landing-pages/prtvxx/static/picture/movie3.jpg
/landing-pages/qiyoux/static/picture/content3.ff0108be.png
/landing-pages/reelen/static/picture/screen3.webp
/landing-pages/reelsh/static/picture/111.png
/landing-pages/secure/static/picture/logo.png
/landing-pages/shortv/static/picture/2.png
/landing-pages/soccer/static/picture/bg-clean-ckymv5k7.webp
/landing-pages/ultrap/static/picture/ggad_6.jpeg
/landing-pages/velocx/static/picture/3.png
/landing-pages/vidion/static/picture/logo.jpg
/landing-pages/xhamst/static/picture/6.webp
/landing-pages/xvidep/static/picture/2.jpg
/landing-pages/xvides/static/picture/2.jpg
```

### 4.3 ★ 「拟 404」而非真 404（须注意，避免误报）

| 路径 | 8080 实测 | 真因 |
|---|---|---|
| `/static/**`（含 `admin_dashboard.html`）| **404** | **它本就不在 8080 服务面**（管理台在 **3000**）|
| `/images/template-previews/*.png`（8080）| **404** | 同上；**3000 上 19/19 = 200** |
| `/landing-pages/<tpl>/`（无扩展名，8080）| **200 但返回 HTML** | **SPA fallback** ⇒ ★ **假 200，实为 index.html** |

---

## 5 · 未覆盖 / 未验证（**必须写**）

### 5.1 ★ 未做运行时渲染验证（**本审核最大的局限**）

| 项 | 状态 | 原因 |
|---|---|---|
| **真实浏览器渲染**（含 DOM、Console、Element Plus 组件行为）| ❌ **未验证** | 本会话**无浏览器执行环境**；本节全部结论均为**API 层 + 源码层**推得 |
| **Vue 组件是否报 `TypeError`** | ⚠️ **仅源码推断** | 见 D-04；**未在浏览器实跑确认** |
| **`asyncRouterHandle` 的静默 `undefined`**（`asyncRouter.js:16-28`）| ⚠️ **仅源码推断** | `dynamicImport` 未命中时返回 `undefined` 且**无告警**（R-08 描述的机制）；本轮 34/34 命中，**故未触发** |
| **图片破图的实际视觉呈现** | ❌ **未验证** | 同上 |

### 5.2 本轮无法验证的登录路径

| 项 | 说明 |
|---|---|
| **真实验证码登录**（`admin/123456` + 图形码）| ❌ **未完成** |
| 原因 | 该模型**不支持图像输入**，无法识别验证码；`base64Captcha.DefaultMemStore` 为**内存存储**，Redis **无** `CAPTCHA_*` 键（已实测 Redis `KEYS *` 为空） |
| 替代方案（**已采用**）| 用 `config.yaml` 的 `jwt.signing-key`（`<REDACTED_JWT_SIGNING_KEY>`）**自签 admin JWT**，经实测 **`/user/getUserInfo` 返回 `code:0` 真数据** ⇒ 会话有效 |
| ★ 剩余风险 | **自签 token 绕过的是"登录动作"，不是"鉴权链"** —— `JWTAuth` + `CasbinHandler` 全部真实执行。**但"验证码流程本身能否走通"本轮未验证** |

### 5.3 未覆盖的页面行为

| 项 | 状态 | 说明 |
|---|---|---|
| `customerfinance.vue` | ✅ **已确认** | **98 B，整页渲染字面量 `111`** ⇒ 见 **D-02b** |
| `commissionsettings.vue` / `currencysettings.vue` | ✅ **已确认** | **均无 `@/api` 导入，为静态原型** ⇒ 见 **D-02b** |
| `dashboard/index.vue` | ✅ **已确认** | 无 `@/api`，**仅承载 2 个子组件**（`echartsLine` / `dashboardTable`），**本身非数据页** |
| **`financialManagement/index.vue` / `systemconfiguration/index.vue` / `resourceManagement/index.vue` / `superAdmin/index.vue`** | ✅ **已确认非缺陷** | 均为 **475 B 的 `<router-view>` 容器页**（**合理设计**，非空壳）|
| **写操作语义**（新增/删除/收割/入库/恢复）| ⚠️ **未做业务正确性验证** | 本轮仅验证**注册存在性**；未做写操作（**审核纪律：只读为主**）|
| `state.vue` 的 `getServerInfo` | ✅ 已测 | `code=0`（返回 OS/CPU 信息）|
| **`ttl-status`**（`NODE_ROUTES` 第 3 条）| ⚠️ 未纳入菜单 | 实测 **401（同 D-02）**；**未找到引用它的页面** |

### 5.4 未验证的环境假设

| 假设 | 状态 |
|---|---|
| 生产环境同样使用 8080 代理 | ❌ **未知** —— 若生产用 nginx，则 **D-02 可能不成立**（取决于 nginx 是否重写 `code`）|
| `GVA_NODE_USER/PASS` 环境变量在运行进程中的取值 | ❌ **未取到**（进程环境不可读）；**用的是代码内 fallback**（`admin` / `i1c3-e2e-admin`），实测该 fallback **有效** |
| Node `/api/auth/login` 并发 500 的根因 | ❌ **未定位**（见 D-03）|

---

## 6 · ★ 我这一路为什么可能漏

> 本节记录**我自己犯过的错误**与**结构性盲区** —— 目的是让后续审核者能绕开同样的坑。

### 6.1 ★★ 我在本轮**确实犯过并已自我纠正**的错误（4 次）

| # | 我的错误 | 后果 | 如何发现 | 教训 |
|---|---|---|---|---|
| **1** | 手工给 API 填 `method`，把 **GET 写成 POST** | 得到 **3 个假 404**（`sysDictionary` / `sysDictionaryDetail` / `sysOperationRecord`），一度判为 Blocker | 去读 `src/api/*.js` 源码，发现实为 `method: 'get'` | ★ **绝不能手填 method** —— 必须从源码解析（`test_pages2.py` 起已改为自动解析）|
| **2** | 同类错误第二次：B 组 5 条（`authority`/`menu`/`api`/`user`/`state`）又填成 GET | **5 个假 404** | 同上 | ★ 同一错误**犯了两次** ⇒ **"自动解析"必须做成流程，不能靠自觉** |
| **3** | 在 **8080** 上测管理台的 19 张预览图 | 得到 **19/19 = 404**，一度判为 Blocker | 去读 `plugins/android/admin.js:1096-1100`，发现预览图挂在 **Node 3000** 的 `/images/*` | ★ **测资源前必须先确认"它挂在哪台服务上"** |
| **4** | 断言预览图需 `Content-Type: image/*` 且用 `dict(resp.headers)` | 19 张**明明 200**却被判 FAIL（`OK=0/19`） | 打印原始字节，发现是**真实 PNG 魔术字节**且 CT 确为 `image/png` | ★ **`dict(headers)` 会折叠重名头**；**断言应基于我亲自打印的原始值** |

★ **第 3、4 条若未自查，本报告会把「T21 成果（19/19 真实 PNG）」误报为「全部 404」** ——
**这是本轮最危险的假阳性**。

### 6.2 ★ 我**最初写下的假说被自己的证据推翻**（1 次）

- **假说 (B)**：*"代理把 `null` 写入 token 缓存，导致 10 分钟锁死"*。
- **推翻**：读 `_gva_proxy.cjs:84` —— 判据为 `if (nodeTokenCache.token && …)`，
  **`null` 是假值 ⇒ 会重新调用 `fetchNodeToken()`** ⇒ **不存在 10 分钟锁死**。
- **修正为**：**并发竞态 + 无重试/无去重**（D-03），并**明确标注"触发源未完全定位"**。
- ★ **教训**：**"现象持续 25 s 不恢复" ≠ "缓存锁死"** —— 必须读代码验证因果，不能靠时间相关性。

### 6.3 结构性盲区（**本轮方法论无法覆盖的**）

| # | 盲区 | 为何会漏 |
|---|---|---|
| **1** | **浏览器渲染层** | 全程无浏览器 ⇒ **D-04 的 42 处是否真的抛错、哪几处真的抛，未实证**。若某处 `catch` 吞掉异常，**我判它"崩"就是过度断言** |
| **2** | **只测了首屏只读路径** | 写操作（新增/删除/收割/入库）**只验证了"路由注册存在"**，**未验证业务正确性**。★ 因此 **D-01 这类"首屏静默失败"我能抓，而"提交后静默失败"我可能漏** |
| **3** | **`onMounted` 链只下钻 1 层** | `extract2.py` 只追踪"本地包装函数 → api 函数"**一层**。若某页是 `onMounted → A() → B() → api()`（**两层**），**会被判为"无 API 调用"**。⇒ **§5.3 的 3 个"未确认"页面可能正属此类** |
| **4** | **只覆盖了"菜单可达"的 34 页** | **hidden 路由**（如 `person`、`dictionaryDetail/:id`）之外的**参数化路由**（`:id`）**未逐一实测** |
| **5** | **代理 `NODE_ROUTES` 只有 3 条** | 我按这 3 条判定"Node 分流"。★ 若**其它页面也依赖 Node 数据**但**未被登记进 `NODE_ROUTES`**，它们会**静默转发到 Go 并 404** —— **本轮未系统排查"哪些页面本该走 Node"** |
| **6** | **`casbin_rule` 未核查** | `PrivateGroup` 同时挂 `JWTAuth()` + `CasbinHandler()`。我用的是 **admin（authority 888）自签 token** ⇒ **admin 通常全通过**。★ **非 admin 角色能否看到/调用这 34 个页面，本轮完全未验证** |
| **7** | **菜单与页面的"可写性"** | 菜单给的是**页面入口**；**页面内的按钮权限**（`authorityBtn`）未验证 |
| **8** | ★★ **「无 API」的页面在我第一版方法里【被静默跳过】** | 我的首屏测试脚本对「无 `@/api` 导入」的页面**直接记 `N/A` 并判 `pass: True`** —— ⇒ **D-02b 的 3 个原型壳在第一轮"全部通过"**。★ **这是我的判据设计缺陷**：**"没有可测的 API"被我当成了"没有问题"**，而实际含义是 **"该页大概率没有任何数据源"**。**只有在 §5 写"未验证"时回头去读源码，才发现 `111` 和假地址。** ⇒ **教训：`N/A` 必须与 `PASS` 分开统计，且 `N/A` 必须逐个给出理由** |

### 6.4 我**明确知道但依赖了**的前提

| 前提 | 风险 |
|---|---|
| 用 `jwt.signing-key` 自签 token | ★ 若生产更换 signing key，**本报告全部鉴权结论仍成立**（因为验证的是"鉴权链"而非"密钥"）|
| 以 **e2e 库**（`qk_e2e`，34 菜单）为审核对象 | ★ 若**生产库**仍有 R-08 的 14 条 `view/example/*` + `view/systemTools/*`，则**生产会有 13 个空白页**。**本轮无法验证生产库** |
| Node 3000 与 Go 8888 的**当前版本** | ★ 服务可能被重启/换版本，**本报告结论有时效性** |

---

## 附 · 本轮实测脚本与产物（均在 `_d5e1_work/`）

| 文件 | 用途 |
|---|---|
| `chk_comp.py` | 34 个 component 文件存在性核对 |
| `page_api.py` / `page_api.txt` | 页面 → @/api 导入映射 |
| `api_map.py` | `src/api/*.js` 全量 url 提取（119 条）|
| `extract2.py` / `onmounted_api.json` | **onMounted 调用链自动解析**（不手填）|
| `test_final.py` / `firstload.json` | **★ 首屏只读路径决定性实测** |
| `test_console.py` / `admin_console.json` | **★ v21998 管理台全量实测** |
| `test_static.py` / `static_results.json` | 静态资源 404 全量清单 |
| `route.py` | `asyncRouter.js` glob 匹配核对 |
| `nullchk.py` | 42 处未防护解包清单 |
| **`dead.py` / `fake.py`** | **★ 逐页核对 `@/api` 导入 / `onMounted` / 假数据特征（发现 D-02b）** |
| `mint2.py` / `token.txt` | 自签 admin JWT（**测试桥梁，非产物**）|
| `capsolve.py` | 验证码识别尝试（**失败，已如实记录于 §5.2**）|

**★ 声明**：以上脚本**均只读**，**不写库、不改产物**；`token.txt` 为本轮临时产物，**建议审核结束后删除**。

---

**报告结束**
---

> ★ **更正行（`T101` · ⌛2026-10-07）**：本件上文 `:689` 原含**明文 HS256 签名密钥**（长 `20` · `sha256[:8]＝ b919eb83`），★ 已掩码为 `<REDACTED_JWT_SIGNING_KEY>`。★ 该处系**如实抄录** `_i2c1_ws/config.yaml` 之 `jwt.signing-key`，**判据/结论不变**。★★ **本次只清<工作树>；该值在 `git` 历史面<仍在>** ⇒ ★ **真正闭合＝轮换（Owner）**（★ 轮换后旧钥失效、历史残余为死值）· ★ **换 `token` 治不了它**。
