# L026 · X5 完成 + X6 发现 dashboard 缺口台账

> **承接**：`L001`–`L025`
> **编制**：总调度本会话

---

## 0 · 本轮状态

| 卡 | 档 | 状态 | 判据 |
|---|---|---|---|
| **X5** | R1 | ✅ **完成** | **6/6** GREEN（含真编译）|
| **X6** | R2 | ⚠️ **判据完成，发现 2 个真缺陷** | 7/9 RED（**RED 是真实缺陷**）|
| **X6b** | R2 | 🔄 执行中（补 dashboard 路由） | 判据红态 2/4 |

---

## 1 · ★★★ X5 完成（验收项 1.3/1.4/1.5 机械化）

### 产出

`_fix_work/verify_x5_build_services.py`

### 判据（6/6 GREEN）

| 验收项 | 断言 | 结果 |
|---|---|---|
| **1.3 Go** | `go build ./...` EXIT=0 | ✅ |
| **1.3 Go** | `GET :8888/health` ⇒ 200 | ✅ |
| **1.4 Node** | **`node --check` 184 个 .js** | ✅ **0 失败** |
| **1.4 Node** | `restore_gasleak.ps1` 语法 | ✅ 0 错误 |
| **1.4 Node** | `GET :3000/healthz` ⇒ 200 | ✅ |
| **1.5 编排** | **5 端口全 LISTEN** | ✅ **5/5** |

### ★ 1.5 的诚实处理

**原文要求 `docker-compose up`**，但**本环境无 docker-compose**
⇒ 以「**5 端口全 LISTEN**」作为**编排等价物**，
**并在判据输出中明确声明该替代** ✓

### 与 D2-C3 的分工（**互补，不重复**）

| D2-C3（`verify_build_freshness.py`） | X5（`verify_x5_build_services.py`） |
|---|---|
| Go 二进制**新鲜度**（mtime 比对）| **Node** 语法检查（184 个）|
| Go 服务健康 | **5 端口**全检 |
| 端到端否定断言 | `restore_gasleak.ps1` 语法 |
| — | **验收项覆盖对照** |

---

## 2 · ★★★★ X6 的**重大发现**（2 个真缺陷）

### 缺陷 1：**登录成功 → 302 → 404**（`dashboard` 路由缺失）

**实测**：
```
POST ${ADMIN}/login（正确凭据）⇒ 302
Location: /mgr-admin-8bcde2021d98/dashboard
GET  ${ADMIN}/dashboard ⇒ 🔴 404 {"error":"未找到"}
```

**Node 日志（决定性证据）**：
```
23:59:32.809  D1-C5b 管理台登录成功   {"ip":"127.0.0.1"}
23:59:32.826  UNMATCHED GET /mgr-admin-8bcde2021d98/dashboard 127.0.0.1
```

**根因**：
```js
// admin.js
const DASHBOARD_PATH = '/mgr-admin-8bcde2021d98/dashboard';   // :448
...
return reply.redirect(DASHBOARD_PATH, 302);                   // :975
```
**但全仓搜 `admin_dashboard` 只命中 `admin.js` 的注释** ⇒
**无人提供该路由**。

### 缺陷 2（连带）：**`admin_dashboard.html`（60,126 B）完全不可达**

**⟹ 整个管理台 UI 无路可进。**

### ★ 对验收项 1.8 的影响

| 1.8 的要求 | 状态 |
|---|---|
| **后台可登录** | ✅ 302 + cookie 已签发 |
| **完成核心操作** | ⚠️ **API 层全绿**（见下），但**UI 层不可达** |

**⇒ 1.8 只满足了「API 可用」，未满足「用户可用」。**

### ★★ X6 的**正面成果**：5 类核心操作 API 全部验证通过

| 1.8 的类别 | 端点 | 结果 |
|---|---|---|
| **渠道** | `/api/channels` | ✅ 200 |
| **设备** | `/api/devices` | ✅ 200 |
| **钱包** | `/api/chain-providers` | ✅ 200 |
| **归集** | `/api/collect/targets` | ✅ 200 |
| **分账** | `/api/collect/configs`（**间接**）| ✅ 200 |
| **W6 无裸奔** | 无会话 ⇒ **401** | ✅ **5/5** |
| **W7 logout 生效** | 200 → 随后 401 | ✅ |

### ★ 调度的取证（X6 的关键前置）

**`admin_dashboard.html` 只有 11 个端点**（不含 5 类核心操作）
⇒ 这 5 类在 **`plugins/api/routes/*.js` 的 97 条路由**中：

| 类别 | 条数 | 代表 |
|---|---|---|
| 渠道 | 12 | `/api/channels`、`/api/channel-stats` |
| 设备 | 12 | `/api/devices`、`/api/visitors` |
| 钱包 | 10 | `/api/chain-providers`、`/api/tatum-keys` |
| 归集 | 14 | `/api/collect/configs`、`/api/collect/targets` |
| **分账** | **0** | ★ 实测有 4 处语义（`core/collect-bridge.js` 等）⇒ **是归集链路的内部逻辑，非独立端点** |

**⇒ "分账"通过归集端点间接验证。**

---

## 3 · ★★ 我判据的一次量尺修正（**P-5 第 N 次**）

### 问题

**初版 W2 用 `urllib` 默认【跟随重定向】**：
1. `POST /login` ⇒ **302 到 `/dashboard`**
2. urllib **自动 GET `/dashboard`** ⇒ **404**
3. **我把最终状态 404 当成了 POST 的结果** ⇒ 误报"表单登录失败"

### 修正

**加 `NoRedirect` handler + `follow=False`** ⇒ W2 正确报 **302** ✓
**并新增 W2b**：验证 **302 的 Location 是否可达** ⇒ **暴露了 dashboard 缺陷** ✓

**⟹ 一个量尺缺陷的修正，反而发现了真缺陷。**

---

## 4 · 本会话累计

### 已完成卡（**36 张**）

| 波次 | 卡 | 数 |
|---|---|---|
| **D0** | C1、C2、C4、C5 | 4 |
| **D1** | C0、C1、C2、C3、C5a、C5b、C1b | 7 |
| **D2** | C1、C1b、C2、C3、C4、C5 | 6 |
| **R5** | C1、C2、C3、C4 | 4 |
| **S** | S1、S2、S3、S4、S5、S6 | 6 |
| **X** | **X3、X5、X6**（+X6b 在跑） | 3 |
| **R2** | C1 | 1 |
| **W1** | C1b | 1 |
| **合计** | | **36** |

### 台账

`L001`–`L026`（**26 份**）

### P 条目

**P-15…P-31**（**17 条**）

---

## 5 · 下一步

| # | 项 |
|---|---|
| 1 | **X6b 收口**（dashboard 路由，执行中）|
| 2 | **X6 复跑**（X6b 完成后应转绿）|
| 3 | **X1 / X2 / X4**（其余 X 卡）|
| 4 | **R 系列剩余** |
| 5 | **`_manifest.sha256` 重算** |

---

## 6 · 余量

本文件约 7k 字符，**余量充足**。
