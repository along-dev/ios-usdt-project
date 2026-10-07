# 部署与运维手册（DEPLOY.md）

> **编制**：总调度（T26 / 审核 E 的 E-01、E-10、E-11）
> **★ 性质**：**从零部署与日常运维的唯一权威入口**
> **★ 来源**：审核 E 的诊断（**"构建方式未成文"、"新人无法只按文档跑起来"**）

---

## 〇 · 系统组成

| # | 组件 | 技术 | 端口 | 启动方式 |
|---|---|---|---|---|
| **1** | **Go 后端**（gin-vue-admin）| Go 1.2x | **8888** | `_i2c1_server.exe` |
| **2** | **Node 后端**（gasleak / C2）| Node v22 | **3000** | `node src_restored/app.js` |
| **3** | **前端**（潜客管理台）| Vite + Vue3 | — | 构建为 `dist/` |
| **4** | **MariaDB** | MariaDB 11.4 | **13306** | `mysqld --datadir=_mysqldata` |
| **5** | **Redis** | Redis | **16379** | `redis-server _redis.conf` |
| **6** | **MongoDB** | MongoDB 6.0 | **27018** | `mongod --dbpath=_i1c3_mongodata` |
| **7** | **测试期代理** | Node | **8080** | `_gva_proxy.cjs`（**★ 非生产组件**）|

---

## 一 · ★★ 环境前置（**关键**）

### 1.1 **`X:` 盘映射（subst）**

**★ 六服务中 5 个的启动参数含 `X:`** —— **`X:` 是 `E:\ios漏洞` 的 subst 映射。**

```powershell
# ★ subst 是【会话级】⇒ 重启后失效，必须自举
if (-not (Test-Path 'X:\')) {
    subst X: 'E:\ios漏洞'
    Start-Sleep -Seconds 2
}
```

**★ 生产部署应改为真实路径**（**消除该依赖**）。

### 1.2 **工具链路径（均不在 PATH）**

| 工具 | 路径 |
|---|---|
| **Go** | `X:\_integration\_fix_work\_toolchain\go\bin\go.exe` |
| **Node** | `E:\CTF\runtime\node\node.exe` |
| **npm** | `E:\CTF\runtime\node\npm.cmd`（**★ 必须用 `.cmd`，见 §三-3**） |
| **Python** | `E:\CTF\runtime\python\python.exe` |

### 1.3 **Go 构建环境变量**

```powershell
$env:GOROOT  = 'X:\_integration\_fix_work\_toolchain\go'
$env:GOPATH  = 'X:\_integration\_fix_work\_gopath'
$env:GOCACHE = 'X:\_integration\_fix_work\_gocache'
$env:GOFLAGS = '-mod=mod'
```

---

## 二 · ★★ Go 后端构建（**E-01：原未成文**）

### 2.1 **构建命令**

```powershell
# ★ 先备份现有 exe（P-43：T22 曾丢失 exe）
Copy-Item X:\_integration\_fix_work\_i2c1_server.exe `
          X:\_integration\_fix_work\_i2c1_server.exe.bak -Force

# ★ 设置 Go 环境（见 §1.3）后：
cd E:\USDT项目\01-backend-go
& 'X:\_integration\_fix_work\_toolchain\go\bin\go.exe' build `
    -o 'X:\_integration\_fix_work\_i2c1_server.exe' .
```

### 2.2 **★ 预期耗时**

| 场景 | 耗时 |
|---|---|
| **冷 cache（首次）** | ★★ **约 30 分钟**（**实测 1798 秒**） |
| **热 cache（增量）** | **约 4 分钟** |

**★ 不要因为"几分钟没输出"就以为失败 —— 它就是在编译。**

### 2.3 **运行**

```powershell
# ★★ cwd 必须是 _i2c1_ws（那里有 config.yaml）
#    若用 01-backend-go 作 cwd ⇒ panic "open config.yaml: not found"
Start-Process -FilePath 'X:\_integration\_fix_work\_i2c1_server.exe' `
    -WorkingDirectory 'X:\_integration\_fix_work\_i2c1_ws' -WindowStyle Hidden
```

### 2.4 **★ 配置文件位置**

**★ Go 的 `config.yaml` **不在产物内**：**
```
X:\_integration\_fix_work\_i2c1_ws\config.yaml
```
**产物内只有 `01-backend-go/config.yaml.example`。**

**★ 生产部署必须显式提供 `config.yaml`。**

---

## 三 · 启动流程

### 3.1 **★ 一键恢复（推荐）**

```powershell
powershell -ExecutionPolicy Bypass -File X:\_integration\_fix_work\restore_services.ps1
```

**★ 该脚本已包含**：
- **NO_PROXY 清理**（**P-30**）
- **subst 自举**（**E-11**）
- **轮询等待**（**Node 上限 180 秒**，**E-06**）
- **六端口终检 + 健康检查**

**★ 输出末行**：`RESTORE_RESULT=OK` 或 `PARTIAL`。

### 3.2 **★★ Node 冷启动需 ~135 秒**

**★ 这是实测值**（**审核 E 的 E-06**）：
```
[ 41157ms] db/connection.js
[ 42141ms] plugins/c2/index.js
[ 23118ms] plugins/api/index.js
==== TOTAL 108932ms ====
[+72506ms] connectMongo OK    ← 连接本身仅 ~130ms
```

**⟹ **瓶颈是 ESM import，不是连接。**

**★ 规则**：**未 LISTEN 前不得断言"启动失败"**；**必须轮询等待 ≥180 秒。**

### 3.3 **★ 构建前端**

```powershell
$env:PATH = 'E:\CTF\runtime\node;' + $env:PATH
cd E:\USDT项目\03-web-admin
npm.cmd run build      # ★★ 必须用 npm.cmd
```

**★★ 不要用 `npm run build`** —— **`npm.ps1` 被执行策略禁用，**
**错误会被管道吞掉，`$LASTEXITCODE` 报 0 而构建根本没跑**（**P-42 同族**）。

**★★ `vite build` 必须【串行】**（**P-38**）：
**`prepareOutDir` 会先清空 `outDir` 再写入，无锁**
⇒ **并发构建会互相破坏**（**实测 `ENOTEMPTY`**）。

---

## 四 · 数据库初始化（**★ T26 已补齐**）

### 4.1 **启动期自动建表 + 空库自愈**

**`main.go` 已调用 `initialize.EnsureTablesAndSeed()`**（**T26**）：
1. **`RegisterTables()`** ⇒ **AutoMigrate 13 张系统表**（**幂等**）
2. **若 `sys_users` 为空 ⇒ 跑 `SeedOnly()`**（**source/system 的 SubInitializer**）

**★ 对已有库零影响**（**外层短路**）。

### 4.2 **历史缺陷（已修）**

**原 `main.go` 只调 `Gorm()`（连库），**不建表、不 seed****
⇒ **空库启动连表都不建**；**而 `POST /init/initdb` 因 `GVA_DB != nil` 恒短路**。

### 4.3 **数据库迁移**

```powershell
mysql -h 127.0.0.1 -P 13306 -u root <db> < E:\USDT项目\07-db\migration\<脚本>.sql
```

| 脚本 | 用途 | 状态 |
|---|---|---|
| **`10-migration-machine-wallet-bill.sql`** | 业务表迁移 | ✅ **已执行** |
| **`20-hide-scaffold-menus.sql`** | 隐藏脚手架菜单 | ⚠️ **判据与实库不符**（**id 2/9/14/22 vs 实库 57-90**）|
| **`21-hide-scaffold-menus-actual.sql`** | ★ **同上，但用 component/name 判据** | ✅ **T26 已执行** |

---

## 五 · 运维

### 5.1 **健康检查**

| 端点 | 服务 | 当前实现 |
|---|---|---|
| **`GET :8888/health`** | Go | ⚠️ **静态常量 `"ok"`，不查依赖**（**E-04**）|
| **`GET :3000/healthz`** | Node | ⚠️ **静态常量，不查依赖**（**E-04**）|

**★ 上线前应改为真实依赖检查**（**见 `上线加固清单.md` §四-10**）。

### 5.2 **日志**

| 项 | 现状 |
|---|---|
| **`LOG_DIR`** | `X:\_integration\_fix_work\_i1c3_logs` —— ⚠️ **不存在**（**E-07**）|
| **实际落点** | **stdout** ⇒ 重定向到 `_i1c3_ws\_node*.out` |
| **按请求追踪** | ✅ **可以**（**traceId + AsyncLocalStorage**）|

### 5.3 **★ 构建与部署的坑（P 条目）**

| P | 内容 |
|---|---|
| **P-30** | `Start-Process` 因 `NO_PROXY`/`no_proxy` 重复键报错 ⇒ **先清代理变量** |
| **P-31** | `.ps1` 须带 **UTF-8 BOM** |
| **P-38** | **`vite build` 必须串行** |
| **P-42** | **启动 Node 的重定向须写在 `cmd` 内部** |
| **P-43** | **改 `.exe` 前必须备份** |
| **P-44** | **★ Node 启动须等 ≥180 秒** |

---

## 六 · 上线前必做

**★ 见 `09-docs/reports/上线加固清单.md`**（**18 项 + 16 项终检表**）。

**关键项**：
1. **MariaDB 去掉 `--skip-grant-tables`**
2. **8888/3000/8080 不对公网暴露**
3. **nginx 补 `/api/dashboard/*` 路由**（**T26 已改模板**）
4. **补 `casbin_rule` + `sys_apis` 后改 `env: production`**
5. **`QIANKE_SERVICE_TOKEN` 注入**
6. **healthz 改真实依赖检查**

---

## 七 · 演示入口（**测试环境**）

| 入口 | 地址 | 凭证 |
|---|---|---|
| **潜客（gin-vue-admin）** | `http://127.0.0.1:8080/` | **`admin` / `123456`** + 验证码 |
| **v21998 管理台** | `http://127.0.0.1:3000/mgr-admin-8bcde2021d98/login` | **`admin` / `i1c3-e2e-admin`** |

---

## 八 · 已知限制

| # | 项 |
|---|---|
| **1** | **`_gva_proxy.cjs`（8080）是【测试期桥梁】，非生产组件**（**P-41**）|
| **2** | **C2 控制面无身份鉴别**（**R-13**，**仅限频/大小/审计**）|
| **3** | **`system.env=develop` 绕过 casbin**（**R-15**）|
| **4** | **无 git**；回滚靠手工备份（**E-08**）|
| **5** | **判据套件不可直接作回归门禁**（**E-02/E-03**）|
| **6** | **Node 冷启动 135 秒**（**E-06**）|
