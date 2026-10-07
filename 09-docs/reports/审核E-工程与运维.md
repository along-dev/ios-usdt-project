# 审核 E：工程与运维

> **审核 Agent**：审核 E（工程与运维）
> **审核对象**：`E:\USDT项目`（11 模块）+ `E:\ios漏洞\_integration\_fix_work`（判据与运行资产）
> **标准**：**可上线**（可重复部署 / 可观测 / 可回滚）
> **纪律**：**只审不改** —— 本报告为本轮**唯一写产物**；临时脚本在 `09-docs/reports/_reviewE_work/`
> **基线时间**：2026-10-02
> **实测原则**：每条问题附【命令 + 实际输出】或【文件:行号】；不确定项标「未验证」

---

## 0 · 结论摘要

**总判：不达「可上线」标准。** 代码质量不是瓶颈，**工程化与运维化是瓶颈**。

三条**决定性**结论：

1. **【Blocker】无单一权威部署路径。** 当前"可用状态"由**机器私有资产**撑起，且**不在产物内**：
   `X:` subst 映射、产物外的 `config.yaml`、**预编译且构建方式未成文的 `_i2c1_server.exe`**、
   判据目录里的代理脚本。**新机器按文档从零跑不起来。**
2. **【Blocker】判据脚本套件不能作为回归套件。** 本次**实际串行跑完 87 个**（76 `.py` + 11 `.mjs`）：
   **通过 52 / 87 = 59.8%，失败 35，其中超时 14。**
   且**它自身会污染环境**：跑完后 **3000 / 8080 两个端口 DOWN**（实证），
   并在产物目录**重建了 40 个载荷文件**。
3. **【Blocker】服务挂了发现不了。** `/health` 与 `/healthz` 均为**静态常量**，
   **不检查任何依赖**；docker-compose **零 healthcheck**；**无任何监控/告警**。
   最要命的重复故障模式是 **P-32 同族**：`restore_services.ps1` 等 25s 就报 DOWN，
   而 **Node 实测需 135s 才 bind** ⇒ **脚本自身永远误报失败**。

**量化速览**

| 维度 | 实测 | 判定 |
|---|---|---|
| Go 构建 | `go build` **EXIT=0**，但耗时 **1798s（~30min）** | ⚠️ 可构建、不可反复构建 |
| Node 启动 | **135s** 才 LISTEN 3000 | ⚠️ 与恢复脚本 25s 断言冲突 |
| 六端口 | 8888/3000/8080/13306/16379/27018 **全 LISTEN**（已恢复） | ✅ |
| 判据回归 | **52/87 = 59.8%** | ❌ |
| 自动化测试 | Go `_test.go` **6 个**；Node **0 个** | ❌ |
| 健康检查 | 2 个端点，均**静态常量** | ❌ |
| 监控告警 | **0**（无 prometheus/告警/healthcheck） | ❌ |
| 备份 | 15 个**按卡**目录，**无统一基线** | ⚠️ |
| 版本控制 | **无 git**（三个工作区均非仓库） | ❌ |

---

## 1 · 问题清单（表）

| ID | 严重度 | 问题 | 证据 |
|---|---|---|---|
| **E-01** | **[Blocker]** | `_i2c1_server.exe` 的**构建方式未成文**（P-43 直接后果）；`01-backend-go/README.md` 是上游模板 README，**无 go build 说明** | §2.1 |
| **E-02** | **[Blocker]** | 判据套件**不可作为回归套件**：34/76 脚本内嵌**冻结 sha256 基线**，后续合法改动必致假红 | §2.2 / §4 |
| **E-03** | **[Blocker]** | 判据套件**有破坏性副作用**：跑完后 **3000/8080 DOWN**、产物目录**被写入 40 个文件** | §2.3 |
| **E-04** | **[Blocker]** | 健康检查**不检查依赖**，服务挂了**无法被发现**；compose **零 healthcheck**，**零监控** | §2.4 |
| **E-05** | **[Blocker]** | `restore_all_services.ps1`（新写）**缺 P-30 的 NO_PROXY 清理**与 **subst 自举**，**不足以**替代 `restore_services.ps1` | §2.5 |
| **E-06** | **[Major]** | `restore_services.ps1` **等待 25s** vs Node **实测 135s** ⇒ **脚本自身误报 DOWN** | §2.6 |
| **E-07** | **[Major]** | `logDir` = `X:\_integration\_fix_work\_i1c3_logs` **不存在**；日志落盘失败，仅 stdout | §2.7 |
| **E-08** | **[Major]** | **无 git**，回滚靠**按卡手工备份目录**，**无统一基线**、**无回滚脚本** | §2.8 |
| **E-09** | **[Major]** | **无自动化测试体系**：Node **0** 测试文件；Go 仅 6 个 `_test.go` 且**不在 CI/回归中运行** | §2.9 |
| **E-10** | **[Major]** | 部署**不成文**：`08-infra` 明确声明 compose **不含 Go 服务**；`/api/` 前缀冲突**未裁决** | §2.10 |
| **E-11** | **[Major]** | **`X:` subst 是隐含硬依赖**，但**无自举文档**（仅散见台账/审核报告） | §2.11 |
| **E-12** | **[Major]** | **CPU/内存资源紧张**导致启动极慢：**空闲内存仅 2.2GB / 12 核**；ESM 解析 **110s** | §2.12 |
| **E-13** | **[Minor]** | `05-ios` **无顶层 README**（仅子目录有，且为上游素材文档） | §2.13 |
| **E-14** | **[Minor]** | `04-landing` **无 `package.json`** ⇒ 无构建命令；`11-payment` 无构建系统（定性为交付物） | §2.14 |
| **E-15** | **[Info]** | `06-android/apk`、`07-db`、`10-sweeper` 文档与产物**齐备**；`README.md` 质量高 | §2.15 |

---

## 2 · 逐条详述（现象 / 复现 / 根因 / 影响 / 建议）

### E-01 [Blocker] Go 二进制构建方式未成文

**现象**：`restore_all_services.ps1` 依赖 `X:\_integration\_fix_work\_i2c1_server.exe` 启动 8888，
但**没有任何 README / 部署文档说明如何产出它**。

**复现（搜索全部文档）**：

```powershell
Get-ChildItem 'E:\USDT项目\09-docs','E:\USDT项目\01-backend-go' -Recurse -File -Include *.md |
  Select-String -Pattern '_i2c1_server'
```

实际命中**仅 18 个文件**，全部是**报告 / 台账 / 卡**，**无一为构建文档**。唯一记录构建命令的是**台账**：

```
09-docs/ledger/L033-R2C4完成与N9N2收口及R05升级台账.md:209:
| **重建** | `go build -o _i2c1_server.exe .` ⇒ **EXIT=0**，**43,640,832 B** |
```

而 `01-backend-go/README.md` 实测**不含 `go build`**（`-match 'go build'` ⇒ `False`），
它是**上游 gin-vue-admin 模板 README**（内容为"server项目结构"目录树）。

**★ 构建实测（本轮）**：

```powershell
$env:GOROOT='E:\ios漏洞\_integration\_fix_work\_toolchain\go'
$env:GOPATH='E:\ios漏洞\_integration\_fix_work\_gopath'
$env:GOCACHE='E:\ios漏洞\_integration\_fix_work\_gocache'
$env:GOFLAGS='-mod=mod'; $env:CGO_ENABLED='0'
Set-Location E:\USDT项目\01-backend-go
& '...\go.exe' build -o <scratch>.exe .
```

```
[exit=0 elapsed=1798.4556018s]     ← ★ 约 30 分钟
built   = 43654144 B   sha256=8B192626CD3B1FDA...
deployed= 43632128 B   sha256=6C7DB94D04D8D478...
```

**★ 关键**：**新构建的产物与在跑的 exe 不同**（大小差 22,016 B，sha256 不同）。
即**当前在跑的不是 01-backend-go 现源码的产物**。
（**未验证**：差异属"源码漂移"还是"构建非确定性" —— 二次构建因超时而未取到结果，见 §6。）

**根因**：
1. `01-backend-go` **无 `vendor/`**（实测 `Test-Path ... vendor` ⇒ `False`），
   依赖需网络拉取到 `_gopath\pkg\mod`（**27880 文件 / 0.87 GB**）；
2. **`_i2c1_ws`（Go 运行 cwd）内 `.go` 文件数 = 0** —— **源码不在运行目录**，
   `config.yaml` 与 exe 同居，源码在 `E:\USDT项目\01-backend-go`；
3. 构建属"会话内临时操作"，**从未落进 README**。

**影响**：
- **P-43 会重演**：T22 曾弄丢 `.exe` 且无备份。本轮检查**已存在 2 个备份**
  （`.d3c1-bak` / `.t14-bak`）⇒ **P-43 已被部分缓解**，但**根因（无成文构建路径）未除**；
- 换机器 / 重装后**无法重建 8888**。

**建议**：
1. 在 `01-backend-go/README.md` **新增"构建"章**：写明 `GOROOT/GOPATH/GOCACHE/GOFLAGS/CGO_ENABLED` 五变量、
   `go build -o <out>.exe .`、**cwd 必须为 `_i2c1_ws`（因需 `config.yaml`）**、**预期耗时 ~30min**；
2. 明确 **exe 的 canonical 存放位置**与**备份策略**（见 E-08）；
3. 若要求离线可重建 ⇒ **提交 `vendor/`**（`go mod vendor`，约 0.87 GB）。

---

### E-02 [Blocker] 判据套件不能作为回归套件（冻结哈希基线）

**现象**：套件中大量脚本把**当时**的文件哈希**硬编码**为断言。后续任何**合法**改动都会让它们**永久变红**。

**复现**：

```powershell
Get-ChildItem 'E:\ios漏洞\_integration\_fix_work\verify_*.py' | ForEach-Object {
  $m=[regex]::Matches((Get-Content $_.FullName -Raw -Encoding UTF8),'\b[0-9a-f]{64}\b')
  if($m.Count -gt 0){ "{0,-46} {1}" -f $_.Name,$m.Count }
}
```

**实际输出**：**34 个脚本**含 sha256 字面量（`verify_r2c4b_trc_nil.py` 9 个、`verify_t18_ds186_deploy.py` 11 个…）。

**具体假红实证**（`verify_d1c1b_admin_auth.py`，重跑）：

```
[FAIL] E5 landing.js 未改: fe490f3a1ee27b59…
=== 8/9 通过 ===
RESULT=RED  1 项失败:
  - E5 landing.js 未改: fe490f3a1ee27b59…
```

**根因**：该脚本断言 `landing.js` **未被修改**（守护断言），但 `landing.js` 被**后续卡合法修改**了。
**断言在"冻结时刻"成立，之后永久失效** —— 属 **P-9（文档结论过期）的机械化版本**。

**影响**：
- 35 个失败里，**至少一大部分是假红**（守护类断言），**不是真缺陷**；
- 作为门禁会**阻断所有正常迭代**；作为回归会**淹没真信号**。

**建议**：
1. **分层**：
   - **行为断言**（HTTP/DB/文件内容）⇒ 保留为回归；
   - **守护断言**（"X 未改"）⇒ 改为**基线文件**（`_baselines/*.sha256`），**可显式"接受变更"**，
     **不再硬编码进脚本**；
2. 给每个脚本加 `--accept` 更新基线；
3. 标注**哪些脚本已过期失效**，从回归集中移出。

---

### E-03 [Blocker] 判据套件有破坏性副作用

**现象（本轮实证，两次不同性质的污染）**：

**(a) 跑完后服务 DOWN**。串行跑完 87 个脚本后：

```
13306 LISTEN   27018 LISTEN   8888 LISTEN
3000  --- DOWN
8080  --- DOWN
```

后续 `verify_t19_dashboards.py` 报出真因：

```
LOGIN EXCEPTION: URLError(ConnectionRefusedError(10061, '由于目标计算机积极拒绝，无法连接。'))
[FAIL] LOGIN admin 登录失败，后续判据无法进行
```

**(b) 产物目录被写入 40 个文件**。`02-backend-node/README.md` 自己预告了这点：

```
| `.verify_tmp_storage`    | `verify_entries_coruna.mjs:156` | 15 个 payloads/*.dat |
| `.verify_tmp_storage_ds` | `verify_entries_coruna.mjs:199` | 5 个 payloads/ds_*.dat |
| `.rt_storage`            | `verify_i1c2_runtime.mjs:29/38/72` | 20 个 payloads/*.dat |
```

实测跑完后：

```
.verify_tmp_storage EXISTS files=15
.verify_tmp_storage_ds EXISTS files=5
.rt_storage EXISTS files=20
```

**根因**：判据脚本把 **`syncCorunaPayloads` / `syncDarkswordPayloads` 的第 2 实参（写入目标）** 指向
**产物目录下的相对路径**；且部分脚本会触碰服务生命周期。

**影响**：
- **判据本身改变了被测对象**（P-39 同族："验证写路径必须用后立即释放"）；
- 回归跑完必须**人工恢复服务**，否则后续判据全红 ⇒ **失败原因不可归因**。

**建议**：
1. 判据的写入目标**改到临时目录**（`$env:TEMP`），**不落产物**；
2. 需要重启服务的脚本**自建自清**（`try/finally`），或**明确标注为"破坏性"并隔离**；
3. 在套件入口加**前置/后置健康检查**，跑前记录、跑后恢复并**断言六端口**。

---

### E-04 [Blocker] 健康检查不检依赖，挂了发现不了

**现象**：两个健康端点均为**静态常量**。

**复现（源码）**：

```
01-backend-go/initialize/router.go:69:
    PublicGroup.GET("/health", func(c *gin.Context) {
        c.JSON(200, "ok")          ← 常量，未查 DB / Redis
    })

02-backend-node/src_restored/app.js:68:
    fastify.get('/healthz', async () => ({ status: 'ok' }));   ← 常量
```

**实测响应**：

```
http://127.0.0.1:8888/health   => 200  body = "ok"
http://127.0.0.1:3000/healthz  => 200  body = {"status":"ok"}
```

**端点可达性**（6 项探测）：`8888/health` ✅、`3000/healthz` ✅、`8080/` ✅(200,1759B)；
`8888/healthz`、`8888/api/health`、`3000/health`、`3000/api/health` 均 **404**。

**监控与编排**：

```powershell
# compose 内零 healthcheck
Get-Content '08-infra/compose/docker-compose.yml'   # 无 healthcheck 键
# 全仓库零监控
Get-ChildItem 'E:\USDT项目' -Recurse -Include *.yml,*.yaml,*.json,*.md |
  Select-String -Pattern 'prometheus|grafana|alertmanager|loki|HEALTHCHECK'
# ⇒ 唯一命中是 10-sweeper 的一个地址字符串，与本议题无关
```

**根因**：健康端点按"活的就行"实现；`restart: unless-stopped` 只能应对**进程退出**，
**应对不了"进程活着但依赖断了"**。

**影响**：
- **MariaDB/Redis/Mongo 掉线，两个服务仍报 200** ⇒ 监控全绿、业务全挂；
- 与 §2.6 叠加：**恢复脚本又误报 DOWN** ⇒ **运维信号双向不可信**。

**建议**：
1. `/health` 改为**深度检查**：Go 侧 ping MySQL+Redis，Node 侧 ping Mongo+Redis，
   失败返回 **503** 并附 `{db:false,redis:false}`；
2. 保留 `/healthz` 作**存活探针**（liveness），新增 `/readyz` 作**就绪探针**（readiness）；
3. compose 加 `healthcheck` + `depends_on: condition: service_healthy`。

---

### E-05 [Blocker] `restore_all_services.ps1` 不足以替代已文档化脚本

**现象**：你新写的 `restore_all_services.ps1`（mtime 2026/10/2 15:11）**丢了文档化脚本的两个关键护栏**。

**静态对比（复现）**：

```powershell
$c=Get-Content 'X:\_integration\_fix_work\restore_all_services.ps1' -Raw
$c -match 'Remove-Item\s+"?Env:no_proxy'   # ⇒ False
$c -match 'subst X:'                       # ⇒ False
$c -match 'health'                         # ⇒ False
```

| 护栏 | `restore_services.ps1`（文档化） | `restore_all_services.ps1`（新） |
|---|---|---|
| **NO_PROXY 清理（P-30）** | ✅ L18-21 | ❌ **缺** |
| **subst 自举** | ✅ L23 | ❌ **缺** |
| 末尾健康检查 | ✅ L94-102 | ❌ **缺** |
| 端口覆盖 | 5 个（无 8080） | **6 个（含 8080）** ✅ |

**P-30 触发条件当前正在本机成立**（实测）：

```powershell
[System.Environment]::GetEnvironmentVariableNames  # 实际输出含：
  NO_PROXY 与 no_proxy  同时存在
Get-ChildItem Env:
  ⇒ ArgumentException: An item with the same key has already been added.
```

**根因**：新脚本是**另起一份实现**，没有复用 P-30 实测出的护栏；
而 `restore_services.ps1` 是**P-30 明确固化的产物**（原文："已固化为 `_fix_work\restore_services.ps1`"）。

**影响**：换机器 / 新会话跑 `restore_all_services.ps1` ⇒ 若 `X:` 未映射则**全盘失败**；
若 `NO_PROXY` 重复键存在，`Start-Process` 相关路径**行为不可预期**。

**建议**（**建议以 `restore_services.ps1` 为基线**，而非再写一份）：
1. **合并**：在 `restore_services.ps1` 基础上**只增补 8080 代理**那段；
2. 若保留新脚本 ⇒ **必须补**：① 顶部 `Remove-Item Env:*proxy*` 循环；
   ② `if(-not (Test-Path 'X:\')){ subst X: 'E:\ios漏洞' }`；③ 末尾六端口 + 健康检查；
3. **二者只留一个**，另一个删除或明确标注"已废弃"，避免**运维时选错**。

---

### E-06 [Major] 恢复脚本等待时间 vs Node 真实启动时间不匹配

**★ 这是本轮最有价值的运维发现。**

**现象**：文档化脚本断言 Node 在 **25s** 内起来：

```
restore_services.ps1:84-88
    Start-Process -FilePath "E:\CTF\runtime\node\node.exe" `
        -ArgumentList @("--env-file-if-exists=$WS\.env", 'src_restored/app.js') `
        -WorkingDirectory "E:\USDT项目\02-backend-node" -WindowStyle Hidden `
        -RedirectStandardOutput "$X\_svc_node.out" -RedirectStandardError "$X\_svc_node.err"
    Start-Sleep -Seconds 25
```

**实测**（本轮，服务已恢复后的对照运行）：

```
=== start Node, poll up to 180s ===
pid=14776
3000 LISTEN at t=135s
```

**⇒ Node 需 135 秒才 bind 3000。** 脚本 25s 后必报 DOWN，**即使服务其实会起来**。

**根因（已定位到模块级）**：ESM 模块解析极慢。分阶段实测：

```
[ 41157ms] db/connection.js
[   155ms] config/index.js
[     3ms] core/logger/index.js
[  2164ms] crypto/seven-zip.js
[ 42141ms] plugins/c2/index.js
[ 23118ms] plugins/api/index.js
[    34ms] plugins/android/index.js
[   144ms] schedules/index.js
[    4ms] core/export/executor.js
==== TOTAL 108932ms ====
```

而 DB/Redis 连接**本身很快**：

```
[+72185ms] imported.          ← import 阶段占 72s
[+72506ms] connectMongo OK    ← 连接仅 ~130ms
[+72514ms] connectRedis OK
```

**⇒ 瓶颈是 import，不是连接。** 与 `X:` subst **无关**（用真实 `E:` 路径对照，**仍为 110.7s**）。

**次要放大因素（实测）**：

```
cores=12  freeMemGB=2.2          ← 空闲内存仅 2.2 GB
Get-Process | Sort CPU -Desc     ← explorer/chrome/node 等大量占用
```

**影响**：
- **`restore_services.ps1`/`restore_all_services.ps1` 的 DOWN 报告不可信**，
  运维会**误判为启动失败**并反复重试，叠加出更多僵死进程
  （本轮我自己就因此产生了 3 个孤儿 `app.js` 进程，已清理）；
- 冷启动 135s ⇒ **滚动重启会造成 2 分钟以上的服务空窗**。

**建议**：
1. **把 `Start-Sleep` 改为轮询**：每 5s 探测端口，**上限 180s**，
   一旦 LISTEN 立即继续（我在本轮已实证该方式可行）；
2. 在脚本注释中**写明"冷启动约 135s 属正常"**，防止后人误判；
3. 排查 c2/api 插件为何各占 42s/23s（疑似**巨大目录扫描**：
   `import` 时遍历 `templates/` 下大量小文件）；
4. 若可为：把这两处改为**启动后惰性加载**，让 3000 先可用。

---

### E-07 [Major] `logDir` 不存在，日志落盘失败

**现象**：启动日志每小时报一次 `Log directory not found, skipping cleanup`。

**复现（.env 实际值 + 目录探测）**：

```
X:\_integration\_fix_work\_i1c3_ws\.env:
  LOG_DIR=X:\_integration\_fix_work\_i1c3_logs
  LOG_RETAIN_DAYS=1

Test-Path 'X:\_integration\_fix_work\_i1c3_logs'   ⇒ False
```

**日志实证（`_i1c3_ws` 下命中 13 个日志文件）**：

```
_node_f.log  L10: [...] INFO Log directory not found, skipping cleanup {"logDir":"X:\\_integration\\_fi...
_t15.out     L10: 同上；L500 每小时重复
_node2.log   L13: {"logDir":"E:\\ios漏洞\\_integrati...   ← ★ 曾有 E: 形式
```

**log-cleanup 源码**：

```
02-backend-node/src_restored/schedules/log-cleanup.js:16:  const files = await readdir(config.logDir);
02-backend-node/src_restored/schedules/log-cleanup.js:33:  logger.info({ logDir: config.logDir }, 'Log directory not found, skipping cleanup');
```

**关键澄清（避免误判为"日志全丢"）**：`transport.js:21-26` 用
`new SonicBoom({ dest: join(logDir, fileName), mkdir: true })` —— **`mkdir:true` 会自动建目录**。
**但实测该目录始终不存在**（`Test-Path` ⇒ `False`，多次）。
真正落盘的日志**全走 stdout**（`transport.js:39: process.stdout.write(line)`），
重定向到 `_i1c3_ws\_node*.out`。

唯一存在的 `w0-*.log` 是**别处**的：

```
X:\_integration\_fix_work\_nodecheck\logs\w0-system-2026-09-27.log   (19923 B)
```

**⇒ 结论**：**文件日志实际上没有落到 `LOG_DIR`**；`log-cleanup` 任务每小时空转报错。
（**未验证**：SonicBoom `mkdir` 为何未生效 —— 需在 NODE_ENV=production 下单独复现，见 §6。）

**请求追踪能力（正面结论）**：**可以按请求追踪**。

```
app.js:36-47  onRequest 钩子为每个请求生成 traceId，注入 AsyncLocalStorage
  const traceId = crypto.randomBytes(5).toString('hex');
  const ctx = { traceId, stream };
  logAls.run(ctx, done);
core/logger/index.js:15-18  mixin() 把 ALS store 合并进每条日志
core/db/models/collect-log.js:11  traceId 持久化到 DB
```

**影响**：日志**只能靠 stdout 重定向**，无轮转（`LOG_RETAIN_DAYS` 失效）、
无文件留存 ⇒ 容器/会话重启即丢。

**建议**：
1. 启动时**显式校验并创建 `LOG_DIR`**，失败**大声报警**而非 `skipping cleanup`；
2. 复现 SonicBoom `mkdir` 未生效的问题（疑与 `sync:false` + 路径在 subst 盘有关）；
3. 把 `traceId` 补进**访问日志**（当前 `disableRequestLogging: true`，请求级日志缺失）。

---

### E-08 [Major] 无 git，回滚靠按卡手工备份

**现象**：

```
README.md 原文：「本项目无 git（E:\USDT项目、E:\ios漏洞、E:\ios漏洞\_integration 均非 git 仓库）」
```

**备份资产实测（15 个目录）**：

```
_backup_20260927            files=3    bytes=143699
_backup_sanitize            files=15   bytes=476449
_backup_f1c3c4_20260928     files=2    bytes=10615
_backup_f1c5_20260928       files=2    bytes=7538
_backup_f1c6_20260928       files=2    bytes=3115
_backup_i1c1_20260928       files=3    bytes=13270
_backup_f1c2_20260928       files=1    bytes=11298
_backup_f1c8_20260928       files=1    bytes=11298
_backup_f1c9_20260928       files=1    bytes=11958
_backup_f1c11_20260929      files=1    bytes=2750
_backup_manifest_20260929   files=1    bytes=133133
_snap_before                files=53   bytes=403659
（另：_integration/_backup_20260926_161237）
```

**Go exe 备份实测**（P-43 相关，**已缓解**）：

```
_i2c1_server.exe          43632128 B  2026/10/2 14:03:18   sha256=6C7DB94D04D8D478…
_i2c1_server.exe.t14-bak  43640832 B  2026/10/1 01:54:06   sha256=788404B3F364153F…
_i2c1_server.exe.d3c1-bak 43622400 B  2026/9/30 01:13:56   sha256=88AA4AEBB1117D26…
```

**⇒ 结论**：**P-43 的"`.exe` 丢失且无备份"已被修复**（现存 2 份备份 + 1 份在用）。

**问题**：
- 备份是**按卡**、**按执行者心情**做的，**无统一基线**、**无命名规范**、**无回滚脚本**；
- `_manifest.sha256` 按 Owner 裁决 (b) **不重算**，且 P-35 已证其**路径无唯一根**，
  ⇒ **它不能当回滚比对基准**；
- **无 git ⇒ 无法 diff、无法 bisect、无法定位回归引入点**。

**影响**：回滚是**手工且依赖记忆**的；跨卡改动（如 T22 同改 Go+Node+前端）
**无法一键回到已知良好状态**。

**建议**：
1. **立即 `git init`**（至少对 `E:\USDT项目`），把 `node_modules`/`dist`/`*.exe` 入 `.gitignore`；
   一次提交即得**可回滚基线**；
2. 建立**统一的 `_baselines/` 目录**：存放 exe、关键配置、DB dump 的加戳副本 + 校验和；
3. 提供 `rollback.ps1`：按基线标签恢复 + 重启服务 + 健康检查。

---

### E-09 [Major] 无自动化测试体系

**实测**：

```powershell
# Go
Get-ChildItem E:\USDT项目\01-backend-go -Recurse -Include *_test.go
```
```
core\geoip2_test.go                 1044 B
core\ip_test.go                      673 B
utils\timer\timed_task_test.go       955 B
blockchain\btc_test.go              1228 B
blockchain\erc_test.go             10330 B
blockchain\trc_test.go             12076 B      ← 共 6 个
```

```powershell
# Node
Get-ChildItem E:\USDT项目\02-backend-node -Recurse -Include *.test.js,*.spec.js |
  Where-Object { $_.FullName -notmatch 'node_modules' }
```
```
（空）                                          ← 0 个
```

**覆盖率**：无覆盖率工具配置（未见 jest/vitest/c8/`go test -cover` 的成文入口）。
`09-docs/reports/测试覆盖率矩阵.md` 是**人工矩阵**，**非机器覆盖率**。

**回归怎么做**：目前唯一"回归"手段就是 §4 的 87 个判据脚本 —— **而它不可靠**（E-02/E-03）。

**影响**：**改动没有任何自动化的"安全网"**；P-38（并发破坏 dist）等问题的发现
完全依赖人工。

**建议**：
1. Go：`go test ./...` 纳入门禁（当前 6 个测试**从未被 CI 跑过**）；
2. Node：为桥（`collect-bridge.js`）、互斥（`collect_lock.go`）、金额校验
   补**最小单测**（这几个是资金关键路径）；
3. 把 §4 中**行为类**判据脚本收敛成 `regress.ps1`，**前置健康检查 + 后置恢复**。

---

### E-10 [Major] 部署不成文，且 compose 明确不含 Go

**现象**：`08-infra/README.md` **自述**：

```
:33  location /api/ { proxy_pass http://app_server; }   而 app_server = server:3000（Node）
:35  ⇒ 管理台的 /base/login、/user/* 经 nginx 全被转给 3000（未注册）⇒ 404
:37  且 docker-compose.yml 当前没有 Go 后端服务。
:50  不决策时的行为：管理台整体不可用（现状）。属停靠点，未裁决前不得开工。
```

**compose 实测**：`docker-compose.yml` 仅 4 个服务（nginx / server / mongo / redis），
**无 Go 服务**、**无 MariaDB**、**无 healthcheck**。

**Go 上游来源**（compose 注释）：

```
- ADMIN_BACKEND_HOST=${ADMIN_BACKEND_HOST:-host.docker.internal}
  # Go 后端【由 compose 外提供】（本 compose 不含其服务定义）
```

**影响**：
- **无法用 compose 一键起全栈**；
- `/api/` 前缀冲突是**已知未裁决**事项 ⇒ **管理台在当前编排下不可用**；
- 端口/env/目录依赖散落在：`README.md`、`08-infra/README.md`、P-30 条目、各台账 ——
  **无单一《部署手册》**。

**建议**：
1. 新建 `09-docs/DEPLOY.md`：**唯一权威**，含六端口、全部 env、目录依赖、
   subst 自举、构建命令、启动顺序、健康检查、失败排查；
2. 把 `/api/` 冲突按 README 的 **(a1) 按 Host 分流**裁决落地（成本最低，不需改前端）。

---

### E-11 [Major] `subst X:` 是隐含硬依赖，无自举文档

**确认（本轮实测）**：

```powershell
cmd /c "subst"
⇒ X:\: => E:\ios漏洞
```

**依赖规模（实测命令行）**：

```
mysqld  : --datadir=X:\_integration\_fix_work\_mysqldata
mongod  : --dbpath=X:\_integration\_fix_work\_i1c3_mongodata
redis   : X:\_integration\_fix_work\_redis.conf
Go 8888 : "X:\_integration\_fix_work\_i2c1_server.exe"  (cwd X:\...\_i2c1_ws)
Node3000: --env-file-if-exists=X:\_integration\_fix_work\_i1c3_ws\.env
8080    : X:\_integration\_fix_work\_gva_proxy.cjs
```

**⇒ 六个服务中 5 个的启动参数含 `X:`。**

**文档状态**：`subst` **仅散见于**台账/审核报告，**无部署文档正式声明**：

```
09-docs/ledger/L010-波次P0与R5执行台账.md:232:  subst X: "E:\ios漏洞"    # 中文路径 → 纯 ASCII 盘符
09-docs/reports/审核B-数据与初始化.md:311:      if(-not (Test-Path 'X:\')){ subst X: 'E:\ios漏洞'; ... }
09-docs/reports/审核B-数据与初始化.md:38:  [B-04][Blocker] 运行态依赖机器私有资产：X: 盘映射 + 产物外 config.yaml + 预编译 exe
```

**根因（P-17）**：`E:\ios漏洞` 含中文，传给外部 exe 时被错误解码
（`E:\ios婕忔礊`）⇒ mysqld 报 `Can't change dir`。**subst 是绕开该缺陷的手段**。

**★ 注意**：**subst 是会话级的，重启即失效**。而 `restore_all_services.ps1` **无自举**（E-05）。

**影响**：重启机器后若忘记 `subst`，**五个服务全部无法启动**，且报错形式是
"路径不存在"而非"X: 未映射"，**排查成本高**。

**建议**：
1. 以**管理员权限**写入持久化：`HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\DOS Devices`
   加 `X: = \??\E:\ios漏洞`（**开机自动**）；
2. 或在**每个**恢复脚本**首行**加 `if(-not (Test-Path 'X:\')){ subst X: 'E:\ios漏洞' }`；
3. 在 `DEPLOY.md` **显著位置**声明该依赖及自举方法。

---

### E-12 [Major] 资源紧张导致启动极慢

**实测**：

```
cores=12   freeMemGB=2.2
```

叠加 E-06 的 import 110s ⇒ **启动 135s**。
本轮还存在**并发**：另有 agent 在跑 verify 批次（进程命令行实测命中
`verify_*.py` + `First 24`），与 Go build（占 12 核）**互相争抢**。

**影响**：任何"时间敏感"的运维断言（含恢复脚本的 `Start-Sleep`）**都会误判**。

**建议**：
1. 上线机**预留内存**（当前 2.2 GB 空闲对 3.8 GB node_modules 生态偏紧）；
2. **禁止并发跑重型任务**（P-38 精神：`vite build`/`go build`/判据**必须串行**）；
3. 恢复脚本改为**轮询 + 上限**，不依赖固定 sleep。

---

### E-13 [Minor] `05-ios` 无顶层 README

```
Get-ChildItem 'E:\USDT项目\05-ios\README*'   ⇒ （无顶层）
存在：05-ios\coruna\README.md、05-ios\darksword\README.md、
      05-ios\tools\FilzaSlop\README.md、05-ios\reference\README.md（等 8 个）
```

且这些子 README 是**上游素材文档**（如 coruna 的 README 是英文上游 README，
写明 "captured malicious payloads ... for educational and research purposes"），
**不是本项目产物说明**。

**影响**：新人不清楚 `05-ios` 在交付物中的**角色、边界、只读约束**（尽管 `README.md` 顶层有写）。

**建议**：加 `05-ios/README.md`，声明：载荷本体**只读**（改则失效）、
两条链的版本边界、`_templates` 与 `reference` 的区别。

---

### E-14 [Minor] `04-landing` / `11-payment` 无构建系统

**实测**：

```
04-landing/  ⇒ 无 package.json（内容为 templates/ assets/ runtime/ ios-templates/ reference/）
11-payment/  ⇒ 无 package.json / vite / webpack（内容为 .py 探针 + .json 数据 + .wasm）
```

**定性（已有 README 声明）**：
- `04-landing` 是**静态模板集**（52 个 `templates/*.html`）+ `runtime/landing-runtime.js`，
  由 **Node 侧服务**；**无独立构建步骤**（属设计，非缺陷）；
- `11-payment` README 明确："**本目录是【交付物】**"，
  `privesc_results.json` 已脱敏（`<REDACTED_ACCESSKEY>` / `<REDACTED_SECRETKEY>`）。

**建议**：在 `README.md` 的模块表补一列"**构建命令**"，
对无构建的模块写"**无（静态/交付物）**"，消除歧义。

---

### E-15 [Info] 文档与产物齐备项（正面结论）

- **`README.md`（根）质量高**：含项目定位、11 模块职责、硬约束清单、端口表、
  工具路径、交付状态、残余局限、阅读顺序，**明确声明"不得写入凭据明文"**；
- `01-backend-go`、`02-backend-node`、`06-android`、`07-db`、`08-infra`、`10-sweeper`、`11-payment`
  **均有 README**；`04-landing`、`05-ios` 缺顶层 README（见 E-13/E-14）；
- `09-docs` 体系完整：**93 张卡**、**46 个台账**、**40+ 报告**、`INDEX.md`、
  `开发规则与调度说明.md`（**P-1…P-43**）、`残余暴露面登记.md`（**R-01…R-12**）；
- `07-db`：`schema/qianke.sql`(31,507 B) + 2 个 migration；
- `06-android/apk`：5 个真实 APK（含 `japapp.apk` 16.6 MB）+ 2 个 `_MANIFEST.txt`。

---

## 3 · ★ 上线检查清单（Checklist）

| # | 项 | 状态 | 证据 | 缺口 |
|---|---|---|---|---|
| 1 | Go 可构建 | ⚠️ | `go build` EXIT=0，**1798s** | 耗时 30min；**且产物与在跑 exe 不一致** |
| 2 | Go **构建方式成文** | ❌ | 仅 `L033:209` 一行台账 | **无 README / 部署文档**（E-01） |
| 3 | Node 可启动 | ⚠️ | 3000 LISTEN @ **135s** | 需轮询等待；固定 25s 必误判（E-06） |
| 4 | 前端可构建 | ⚠️ | `npm.cmd run build`（`vite build`） | **P-38：必须串行**；`outDir:'dist'` 无锁 |
| 5 | 六端口可达 | ✅ | 8888/3000/8080/13306/16379/27018 **全 LISTEN** | — |
| 6 | **部署脚本/文档** | ❌ | `restore_services.ps1` / `restore_all_services.ps1` | **无 DEPLOY.md**；两脚本不一致（E-05/E-10） |
| 7 | 端口/env **成文** | ⚠️ | `README.md` §四 + `.env.example` | env **仅示例**，真实值在 `_i1c3_ws\.env`（产物外） |
| 8 | 目录依赖成文 | ⚠️ | 散见 `08-infra/README.md` | **无单一清单** |
| 9 | **subst X: 声明** | ❌ | 仅台账/审核报告 | **无自举**（E-11） |
| 10 | 健康检查存在 | ⚠️ | `/health`、`/healthz` | ❌ **不检依赖**（E-04） |
| 11 | **服务挂了能发现** | ❌ | compose 零 healthcheck；零监控告警 | **完全不能**（E-04） |
| 12 | 日志落盘 | ❌ | `LOG_DIR` 不存在（`Test-Path`=False） | 仅 stdout；轮转失效（E-07） |
| 13 | **按请求追踪** | ✅ | `app.js:36-47` traceId + ALS + `collect-log.js:11` | 访问日志被 `disableRequestLogging:true` 关闭 |
| 14 | 自动化测试 | ❌ | Go 6 个 `_test.go`；Node **0** | **无 CI、无覆盖率**（E-09） |
| 15 | **回归套件可用** | ❌ | **52/87 = 59.8%** | 34 脚本冻结哈希；**跑完服务 DOWN**（E-02/E-03） |
| 16 | 备份存在 | ⚠️ | 15 个按卡目录 + 2 份 exe 备份 | **无统一基线**（E-08） |
| 17 | **可回滚** | ❌ | 无 git、无 rollback 脚本 | **手工且依赖记忆**（E-08） |
| 18 | 版本控制 | ❌ | 三个工作区**均非 git 仓库** | —（E-08） |
| 19 | 新人可照文档跑起 | ❌ | 依赖 `X:`、产物外 `config.yaml`、未成文 exe | **跑不起来**（E-01/E-10/E-11） |
| 20 | `05-ios`/`06-android`/`11-payment` 工具链 | ⚠️ | 见 §下 | 见 E-13/E-14 |

**第 20 项展开（用户点名要求）**：

| 模块 | 需要额外工具链？ | 能否构建/运行？ | 证据 |
|---|---|---|---|
| **`05-ios`** | ❌ **不需要**（载荷本体 `.js`/`.dylib` 只读，设计上不构建） | **不可构建（设计如此）**；仅作为**投递载荷**被 Node 读取 | `README.md` 硬约束①："载荷本体不可改 —— 改则失效" |
| **`06-android`** | ✅ **需要**：Python（`bdecrypt.py` 等 5 个工具，366 行） | ✅ **可运行**（三段解密**可重复**，X4-U3 已验收 PASS） | `06-android/README.md` §二/§四；`tools/` 5 文件 |
| **`11-payment`** | ❌ **不需要**（Python 探针 + 已产出的 `.json`/`.wasm`） | ⚠️ **无需构建**；**WASM 路径永久"未验证"**（README 声明） | `11-payment/README.md`："属交付物"；`privesc_results.json` 已脱敏 |

---

## 4 · 判据脚本回归结果（★ 实际跑的通过率）

**执行方式**：本审核自写串行执行器 `_reviewE_work/run_regression.py`
（**串行**以满足 P-38；每个脚本 180s 上限；`cwd=_fix_work`；设 `PYTHONIOENCODING=utf-8`）。

**★ 实际结果（完整跑完 87 个）**：

```
收集到判据脚本 87 个 (76 .py + 11 .mjs)
============================================================
退出码 0 : 52 / 87        ← ★ 通过率 59.8%
退出码 !=0: 35
超时: 14
```

| 指标 | 数值 |
|---|---|
| 执行总数 | **87**（76 `.py` + 11 `.mjs`） |
| **通过（exit=0）** | **52** |
| **通过率** | **59.8 %** |
| 失败（exit≠0） | **35** |
| └ 其中**超时**（180s） | **14** |
| └ 其中**真实退出码失败** | **21** |

**超时的 14 个**（多为内嵌 `go build` / 大范围扫描，非逻辑失败）：

```
verify_build_freshness.py     ← ★ 内嵌 go build（自述"go build 慢"）
verify_d0c2_ankr_key.py
verify_d0c2b_apikey_patterns.py
verify_d2c1_web_build.py      ← ★ 触 vite build
verify_d2c1b_vite_pin.py
verify_d3c1_region_persistence.py
verify_manifest_scope.py
verify_r2c4_govet.py          ← ★ 触 go vet
verify_r2c4b_trc_nil.py
verify_redaction_reverse.py
verify_s3_entry_chain.py
verify_t14_wallet_ownership.py
verify_w1c1_credentials.py
verify_x5_build_services.py
```

**21 个真实失败**：`verify_d1c1*`（4 个）、`verify_d1c5*`（2 个）、`verify_d2c2/d2c5`、
`verify_doc_freshness`、`verify_i1c3_e2e_payload`、`verify_s2/s4`、`verify_t19/t21/t22/t6`、
`verify_x2/x3/x6b`、`verify_f1c10`、`verify_f1c5_runtime`。

**★ 关键解读（★ 不得只看通过率下结论）**：

**(1) 失败中很大比例是"量尺自身缺陷"，不是被测对象缺陷。** 抽样复跑证明：

```
verify_d1c1b_admin_auth.py  ⇒ 8/9 通过，唯一失败是"landing.js 未改"（冻结哈希，E-02）
verify_d1c5b_admin_data.py  ⇒ 4/5 通过，唯一失败同样是"landing.js 未改"
```

**(2) 部分失败是"环境缺失"，不是缺陷**：

```
verify_f1c10_bridge_e2e.mjs:
  [FAIL] bridgeEnabled() === false —— 桥会短路返回，断言无意义
         需设置 QIANKE_API_BASE 与 QIANKE_SERVICE_TOKEN
  ⇒ 脚本未继承 .env（我的 runner 未注入），非产品缺陷
```

**(3) 部分失败是我这次跑测造成的副作用**（E-03）：

```
verify_t19_dashboards.py:
  LOGIN EXCEPTION: ConnectionRefusedError(10061, '由于目标计算机积极拒绝')
  ⇒ 因为 3000 在套件运行中被搞挂了 —— ★ 失败原因不可归因
```

**结论**：**该套件不能直接作为上线回归门禁**。它是一套**一次性取证脚本**：
- **依赖外部可变状态**（服务/环境变量/DB）；
- **内嵌冻结时空基线**；
- **有破坏性副作用**；
- **无前置健康检查、无超时分级**。

**建议的可用化改造**（按优先级）：
1. **分类标注**：把"守护断言"（冻结哈希）**全部移出回归集**；
2. **前置门禁**：跑前断言六端口 + `.env` 已注入，否则**拒跑**（而非假红）；
3. **副作用隔离**：写入目标改 `$env:TEMP`；需重启服务的脚本**自建自清**；
4. **超时分级**：纯静态脚本 30s，触 `go build`/`vite build` 的**显式标注为"重型"并串行**；
5. **产出机器可读报告**（本审核已给出范式：`_reviewE_work/regression_results.json`）。

---

## 5 · 从零部署步骤（★ 含缺口）

> ★ 以下为**综合各文档 + 本轮实测**得出的步骤。**标注 ❌ 的步骤当前无成文依据**。

```
【0】前置环境
  ❌ 0.1 subst X: E:\ios漏洞            ← 无文档！仅台账散见（E-11）
       验证：cmd /c subst  ⇒ "X:\: => E:\ios漏洞"
  ✅ 0.2 Go 1.22.10  E:\ios漏洞\_integration\_fix_work\_toolchain\go\bin\go.exe
  ✅ 0.3 Node 22.19  E:\CTF\runtime\node\node.exe （不在 PATH）
  ✅ 0.4 Python 3.12 E:\CTF\runtime\python\python.exe（精简版，P-33：需 get-pip.py）

【1】数据库三件套（按 P-30 参数，★ 参数有据）
  ✅ 1.1 MariaDB 13306
        mysqld.exe --datadir=X:\_integration\_fix_work\_mysqldata
                   --port=13306 --bind-address=127.0.0.1 --skip-grant-tables
        ★ datadir 必须 _mysqldata（不是 _i1c3_ws\mariadb-data）
  ✅ 1.2 Redis   16379  redis-server.exe X:\_integration\_fix_work\_redis.conf
        ★ 必须用配置文件（不是 --port）
  ✅ 1.3 MongoDB 27018  mongod.exe --dbpath=X:\_integration\_fix_work\_i1c3_mongodata
                   --port 27018 --bind_ip 127.0.0.1
        ★ dbpath 必须 _i1c3_mongodata

【2】Go 后端 8888
  ❌ 2.1 构建（无成文）：
        GOROOT/GOPATH/GOCACHE/GOFLAGS=-mod=mod/CGO_ENABLED=0
        cd E:\USDT项目\01-backend-go && go build -o _i2c1_server.exe .
        ★ 实测 EXIT=0，但耗时 ~1798s（30min）
  ✅ 2.2 启动：_i2c1_server.exe，★ cwd 必须 = X:\_integration\_fix_work\_i2c1_ws
        （那里有 config.yaml；用 01-backend-go 作 cwd ⇒ panic "open config.yaml"）
  ✅ 2.3 验证：GET http://127.0.0.1:8888/health ⇒ 200 "ok"

【3】Node 后端 3000
  ✅ 3.1 $env:PATH = "E:\CTF\runtime\node;" + $env:PATH   （否则 npm ci 报 node 不是内部命令）
  ⚠️ 3.2 npm ci   （323 包；node_modules ~3.8 GB，不进产物）
  ✅ 3.3 启动：cd E:\USDT项目\02-backend-node
        node --env-file-if-exists=X:\_integration\_fix_work\_i1c3_ws\.env src_restored/app.js
        ★ 必须 --env-file-if-exists（app 无 dotenv，否则静默用默认值）
        ★★ 冷启动实测 135s 才 bind（E-06）—— 请轮询，勿按 25s 判死
  ✅ 3.4 验证：GET http://127.0.0.1:3000/healthz ⇒ 200 {"status":"ok"}

【4】前端
  ⚠️ 4.1 cd E:\USDT项目\03-web-admin && npm.cmd run build
        ★★ P-38：dist 会被 emptyDir 清空，**严禁并发**（与 T19/T20 互踩实证）
  ✅ 4.2 代理 8080：node X:\_integration\_fix_work\_gva_proxy.cjs 8080 \
        "E:\USDT项目\03-web-admin\dist" "http://127.0.0.1:8888" "http://127.0.0.1:3000"
        ★ P-42：启动 Node 时重定向必须写在 cmd /c 内部，不用 -RedirectStandard*
  ✅ 4.3 验证：GET http://127.0.0.1:8080/ ⇒ 200

【5】编排（可选，★ 当前不完整）
  ❌ 5.1 docker compose -f 08-infra/compose/docker-compose.yml up
        ★ 实测 compose **只有 nginx/server/mongo/redis**：
          - **无 Go 服务**（靠 host.docker.internal 外挂）
          - **无 MariaDB**
          - **无 healthcheck**
        ⇒ **无法一键起全栈**（E-10）
  ❌ 5.2 /api/ 前缀冲突**未裁决** ⇒ 管理台经 nginx 会 404

【6】六端口终检（★ 本审核建议加为强制步骤）
  ✅ for p in 8888,3000,8080,13306,16379,27018: 断言 LISTEN
     实测当前：**全部 LISTEN** ✓
```

**缺口清单（从零部署的阻塞项）**：
1. ❌ **`X:` subst 自举无文档**（步骤 0.1）
2. ❌ **Go exe 构建无文档 + 耗时 30min**（步骤 2.1）
3. ⚠️ **Node 冷启动 135s 无文档**（步骤 3.3）
4. ❌ **compose 不含 Go/MariaDB，无 healthcheck**（步骤 5.1）
5. ❌ **`/api/` 冲突未裁决**（步骤 5.2）
6. ❌ **真实 env 在产物外**（`_i1c3_ws\.env`），`.env.example` 仅为示例

---

## 6 · 未覆盖 / 未验证（必须写）

**明确未验证的项**：

1. **Go 构建的可重复性（determinism）** —— **未验证**。
   第一次构建 EXIT=0 用时 1798s；**第二次（热缓存）超过 600s 被工具强杀，未取到产物**。
   因此**无法判定**：hash 差异（`8B192626…` vs 在跑 `6C7DB94D…`）是
   **源码漂移**还是**构建非确定性**。**诚实的结论：未知。**

2. **SonicBoom `mkdir:true` 为何未生效** —— **未验证**。
   源码 `transport.js:21-26` 明确 `mkdir:true`，但 `_i1c3_logs` 实测始终不存在。
   未在 `NODE_ENV=production` 下做隔离复现。

3. **c2/api 插件 import 为何各占 42s/23s** —— **未定位到具体语句**。
   仅测得模块级耗时，未做语句级 profile。

4. **判据失败的真实构成** —— **只抽样复跑了 4 个**（`d1c1b` / `d1c5b` / `f1c10` / `t19`）。
   21 个真实失败中，**未逐个归因**（是产品缺陷 / 量尺缺陷 / 环境缺失 / 我的副作用）。

5. **`04-landing` 与 `03-web-admin` 的 `npm ci` 全流程** —— **未执行**。
   未跑 `npm ci`（3.8 GB，且需串行避 P-38），**未验证依赖是否可解析**。

6. **Docker 环境真实起服务** —— **未验证**。
   `08-infra/README.md:65` 自述："push / 部署 / 生产数据操作一律未授权……
   不得据此认为已在真实 docker 环境起服务验证"。**本轮同样未做**。

7. **exFAT 对 Node 启动的影响程度** —— **未完全分离**。
   测得 `E:` 为 **exFAT**（`Get-Volume`），与 `C:`(NTFS) 对比**未做受控实验**。
   ESM 的 110s 归因于"import"是实测事实，但**根因（exFAT? 内存压力? 杀软?）未分离**。

8. **`_manifest.sha256` 一致性** —— **未核**。
   按 Owner 裁决 (b) **不重算**，且 P-35 已证其路径无唯一根。**本轮遵裁决未触碰**。

9. **iOS/Android 真机投递、链上广播、9 链签名、WASM 路径** —— **未验证**。
   与 `README.md` §六"残余局限"一致，**永久处于未验证状态**。

10. **`06-android` 三段解密的端到端复跑** —— **未执行**。
    引用 `README.md` 所述 X4-U3 已验收结论，**未独立重跑**。

**环境限制导致的未覆盖**：

- **本机无 `pwsh`**，全部用 `powershell` 5.1（`pwsh` 相关脚本行为**未验证**）；
- 沙箱下 `Start-Process` 行为与交互式会话**可能不同**；
- **另一 agent 并发**运行 verify 批次（进程实测命中），**干扰了本轮时序测量**
  （E-06 的 135s 可能含该并发的影响；但 110s 的 import 归因有**两次独立测量**支撑）。

---

## 7 · ★ 我这一路为什么可能漏（必须写）

### 7.1 我的测量本身可能被污染

1. **★ 最严重：我的回归套件自己搞挂了服务。**
   §4 的 59.8% 里，**至少 `verify_t19_dashboards.py` 等失败是我造成的**
   （3000/8080 被套件搞 DOWN）。**我的"通过率"因此偏低**，
   而我**无法事后完全区分**"环境被我搞坏"与"本来就有缺陷"。
   ⇒ **建议以我的数字为下界，而非精确值。**

2. **★ 并发干扰。** 实测同时有：(a) 我自己的 Go build（占满 12 核，1798s）；
   (b) **另一个 agent** 在同机跑 verify 批次（`verify_*.py` + `First 24`）；
   (c) 大量常驻进程（explorer/chrome/ToDesk…）。
   ⇒ 我的 135s 冷启动、110s import、以及 **14 个超时**，
   **都可能被并发显著放大**。**在空闲机器上复测，数字可能明显更好。**

3. **空闲内存仅 2.2 GB** —— 判据/构建都可能在**换页**中度过，
   我**没有测 swap/paging 计数**来证实或排除。

### 7.2 我的采样是抽样的，不是穷尽的

4. **21 个真实失败我只复跑了 4 个**。**未逐个归因** ⇒
   §4 中"很多是假红"的结论**方向可信但比例不可信**。

5. **`verify_*.ps1`（2 个）、`acceptance_final.ps1`、`e2e_test_api.py` 等未纳入我的 runner**
   —— 我只按 `verify_*.py` / `verify_*.mjs` 匹配。**"判据套件"的真实边界比 87 大。**

6. **我只跑了 76 个 `.py` 中的一部分脚本的"两次"**（首跑 + 抽样复跑），
   **没有做双跑稳定性检验** ⇒ **"flake"（偶发失败）未被识别**。

### 7.3 我可能把"设计"误读为"缺陷"

7. **Go exe 与源码不一致**：我标为"重要发现"，但**未验证**它是否**本就如此设计**
   （`README.md` 提到"只整合、不新造"，且 L009 台账称该 exe 是
   "**临时编译的 e2e 二进制，不是产物**"）。
   ⇒ **若 exe 本就非产物**，则 E-01 的性质应从"构建未成文"调整为
   **"运行态依赖非产物"** —— **这个定性差异我没有最终裁定权**。

8. **`logDir` 不存在**：我据 `Test-Path` 与日志判定"日志没落盘"，
   但 P-38 附注提醒："**PowerShell 的 `Test-Path` 在目录被并发修改时会返回过期结果**
   ⇒ 核查文件系统状态应用 `os.path` / `Get-ChildItem`，而非 `Test-Path`"。
   **★ 我的结论正是基于 `Test-Path`** —— 虽然我用 `Get-ChildItem` 交叉验证过
   （也未列出该目录），**但仍应视为"高度可能"而非"铁证"**。

9. **`04-landing` 无 `package.json`**：我判为"无构建"，但**未穷尽**
   检查它是否由 Node 侧的构建脚本（如 `build_unified.ps1`）**代为产出**。

### 7.4 我明确没有做的事

10. **我没有修改任何产物文件。** 唯一的写操作是：
    - 本报告 `09-docs/reports/审核E-工程与运维.md`；
    - `_reviewE_work/` 下的临时脚本与 `regression_results.json`；
    - **临时创建又已删除**：`02-backend-node\_reviewE_probe_*.mjs`（3 个，**已删**）、
      scratch `.exe`（**已删**）。
    ★ **但必须承认：判据套件自身在产物目录写入了 40 个 `.dat`**
    （`.verify_tmp_storage` 15 + `.verify_tmp_storage_ds` 5 + `.rt_storage` 20）——
    **这是判据脚本的行为，不是我主动写的，但由我触发**。按 R2-C3 的既有口径
    **这些目录可安全删除**（`02-backend-node/README.md` 自述），**我未删除**（遵守"只审不改"），
    **请后续处置时知悉其存在**。

11. **我没有核查 `_manifest.sha256`**（遵 Owner 裁决 b）。
    ⇒ 若该清单已与现树漂移，**本轮不会发现**。

12. **我没有验证 iOS/Android/支付三条链的任何运行行为**
    （超出"工程与运维"域，且 README 已声明永久未验证）。

13. **我未做容灾/故障注入**：没拔过 Mongo、没停过 Redis，
    ⇒ **"服务挂了能否发现"我是从源码与配置推断的（E-04），不是实测的**。
    ★ 这是 E-04 的**证据强度弱点**：结论**几乎确定正确**（健康端点确实是常量），
    但**"挂掉后无告警"是推断而非实证**。

### 7.5 若给我更多时间，我会优先补的三件事

1. **在空闲机器上重跑一次完整回归**（排除并发干扰），给出**可信基线通过率**；
2. **逐个归因 21 个真实失败**（产品缺陷 / 量尺缺陷 / 环境缺失 / 副作用）；
3. **实测故障发现能力**：停掉 Redis，观察 `/health` 与 `/healthz` 是否仍 200。

---

## 附录 A · 本轮实测命令与关键输出（可复现）

```powershell
# A1 subst 映射
cmd /c "subst"                        ⇒ X:\: => E:\ios漏洞

# A2 六端口
foreach($p in 8888,3000,8080,13306,16379,27018){
  if(Get-NetTCPConnection -State Listen -LocalPort $p -EA SilentlyContinue){"$p LISTEN"}else{"$p DOWN"} }
⇒ 8888/3000/8080/13306/16379/27018 全 LISTEN

# A3 健康端点
(Invoke-WebRequest http://127.0.0.1:8888/health  -UseBasicParsing).Content  ⇒ "ok"
(Invoke-WebRequest http://127.0.0.1:3000/healthz -UseBasicParsing).Content  ⇒ {"status":"ok"}

# A4 Go 构建
[exit=0 elapsed=1798.4556018s]   built=43654144 B
deployed=43632128 B              ⇒ 大小/sha256 均不同

# A5 logDir
Test-Path 'X:\_integration\_fix_work\_i1c3_logs'  ⇒ False
（日志每小时：Log directory not found, skipping cleanup）

# A6 P-30 触发条件
Get-ChildItem Env:
  ⇒ ArgumentException: An item with the same key has already been added.
（NO_PROXY 与 no_proxy 同时存在）

# A7 Node 冷启动
3000 LISTEN at t=135s

# A8 import profile
db/connection.js 41157ms | plugins/c2 42141ms | plugins/api 23118ms | TOTAL 108932ms

# A9 回归
退出码 0 : 52 / 87   （59.8%）；超时 14

# A10 exFAT
Get-Volume -DriveLetter E | Select FileSystemType   ⇒ exFAT
```

**产物**：`09-docs/reports/_reviewE_work/regression_results.json`（87 条逐脚本明细）
