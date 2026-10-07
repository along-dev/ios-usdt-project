# ARCHITECTURE —— 架构总纲（AS-IS）

> **本文件定位**：本项目**唯一的架构入口**。回答「这套系统由什么组成、边界在哪、谁跟谁说话、真值锚在哪」。
> **性质**：**AS-IS 实测快照** —— 每条都带**文件路径锚点**；无锚点的写「裁决」（Owner 定的取舍，非代码事实）。
> **编制**：架构师线（⌛2026-10-04）｜**基线**：本轮逐条实读代码所得
> **★ 不得写入任何凭据明文**（否则本文件自身成为泄漏点）。
> **与既有文档的关系**：`09-docs/analysis/` 下的 9 份「方案」类文档（`整合复刻执行方案_主方案` / `全工作区整合复刻方案_终极版` / `三系统整合复刻方案` / `双平台整合复刻方案` / `整合复刻方案` 等）**降级为「溯源」**——它们记录了当时的推理过程，**不再是架构依据**。要读架构，读本文件。

---

## 〇、一句话定位

**三系统整合产物**：把 gasleak（Node）的载荷分发与归集能力、潜客（Go）的资金记账与运营后台、iOS 载荷（coruna / darksword 两条链）整合进 `E:\USDT项目` 单一工作区。

**分期**：**一期**＝只整合、不新造（已收官）；**二期**＝扩覆盖、补运营（进行中）。

---

## 一、顶层结构（11 个模块）

| 模块 | 职责 | 活体入口 |
|---|---|---|
| `01-backend-go` | 潜客 Go 后端 —— 资金记账 / 分账 / 结算 / 运营管理台 API | `main.go` → `core.RunWindowsServer()`，**8888** |
| `02-backend-node` | gasleak Node 后端 —— 载荷分发 / 归集调度 / 桥 | `src_restored/app.js`（**3000**） |
| `03-web-admin` | 管理台前端（Vite + Vue3） | 构建为 `dist/` |
| `04-landing` | 落地页前端 —— 面向访客，埋点与下载 | 经 nginx 转 Node |
| `05-ios` | iOS 载荷本体 + 组装工具链 | 载荷**只读**；工具可写 |
| `06-android` | Android 载荷与解包产物 | — |
| `07-db` | 数据库 schema 与迁移 | MariaDB `qianke` |
| `08-infra` | 部署编排（nginx / docker-compose） | — |
| `09-docs` | 文档体系（卡片 / 契约 / 报告 / 台账） | — |
| `10-sweeper` | 离线命令行归集工具（9 链签名与广播） | **不接入互斥**（见 §十一） |
| `11-payment` | 支付相关（WASM 路径，**未做代码级审核**） | — |

---

## 二、运行时拓扑

| 组件 | 端口 | 启动方式 | 依赖 |
|---|---|---|---|
| 潜客 Go（gin-vue-admin） | **8888** | `_i2c1_server.exe` | MariaDB `13306`、Redis `16379` |
| gasleak Node（Fastify） | **3000** | `node src_restored/app.js` | MongoDB `27018` |
| 管理台前端 | — | 构建为 `dist/`，由 nginx 托管 | — |
| MariaDB 11.4 | **13306** | `mysqld --datadir=_mysqldata` | — |
| Redis | **16379** | `redis-server _redis.conf` | — |
| MongoDB 6.0 | **27018** | `mongod --dbpath=_i1c3_mongodata` | — |
| 测试期代理 | **8080** | `_gva_proxy.cjs`（**★ 非生产组件**） | — |

**健康端点**：Go `/health`（公开组，无鉴权）。实测现值：`{"checks":{"mariadb":{"ok":true},"redis":{"ok":true}},"status":"ok"}`。
**Node 根路径** `/` 返回 `{"error":"未授权"}`（隔离正常）。

★ **环境前置**：六服务中 5 个的启动参数含 `X:` —— 它是 `E:\ios漏洞` 的 **subst 映射，会话级，重启即失效**。生产部署应改为真实路径（**未做**，见 §十二 **AD-12**）。

---

## 三、Go 后端（`01-backend-go`）

**模块路径**：`github.com/flipped-aurora/gin-vue-admin/server` —— 即 **gin-vue-admin 脚手架改造**。

**分层实测文件数**：api 46 · service 26 · model 26 · router 17 · middleware 11 · initialize 13 · global 2 · config 21 · blockchain 9 · core 8 · utils 34。

**路由注册总闸**：`initialize/router.go:36-151`。四组，**鉴权强度完全不同**：

| 组 | 位置 | 端点 | 鉴权 |
|---|---|---|---|
| 公开 | `router.go:58,120` | `/health`、`/base/login`、`/base/captcha`、`/init/initdb`、`/init/checkdb` | **无** |
| **裸奔 app 组** | `router/app/public.go:15-20` | `/app/device`、`/app/wallet` | **无** —— 注释自述「不加鉴权，现网在用」 |
| 服务间 app 组 | `router.go:63-65` | `/app/wallet-status`、`/app/bill-list`、`/app/collect-lock`、`/app/collect-release`、`/app/collect-result` | `X-Service-Token` |
| 私有组 | `router.go:124-141` | `/api/*`、`/system/*`、`/device/*`、`/casbin/*`、`/user/*`、`/menu/*` … | `JWTAuth()` + `CasbinHandler()` |

★ **要点**：README 硬约束里的隐蔽后台 `/mgr-admin-8bcde2021d98` **在 Go 侧没有路由** —— 它由 nginx 直接转给 Node（`08-infra/nginx/nginx.local.conf:62-126`）。**该安全面的归属是 Node，不在 Go。**

**中间件（`middleware/`，11 个）**：`jwt.go:19` JWTAuth（`x-token`）· `casbin_rbac.go:14` CasbinHandler（`Env==develop` 旁路已删，WBE01-B/T28）· `service_token.go:22` ServiceTokenAuth · `cors.go:11` 全放行 · `operation.go:33` 操作记录 · `limit_ip.go:28` 限流 · `logger.go` / `error.go` / `loadtls.go` / `need_init.go`。
★ **`app_jwt.go:11` 的 `AppJWTAuth` 全仓无挂载点** —— 死代码，见 §十二 **AD-10**。

**资金链路**：

| 面 | 文件 | 说明 |
|---|---|---|
| 链上原语 | `blockchain/eth.go` · `trx.go` · `btc.go`（BIP84） | 转账 / 余额 / 地址派生 / 助记词派生 |
| A 路（核验归集） | `blockchain/scan.go` —— `LoadRpcList` / `Sk` / `ScanBalance` | 潜客侧 `ShouGe()` 触发，事后核验并 CAS 置 `bill.status` |
| B 路（回传落账） | `service/app/collect_result.go:44` `CollectResult` | gasleak 归集后经 `/app/collect-result` 回传 |
| 占位互斥 | `service/app/collect_lock.go:38/78/89` | `CollectLock` / `ReleaseCollectLock` / `CollectRelease` |
| 共用函数 | `blockchain/billing.go`（`AccumulateUsdtNum`） | ★ 放这里是为**规避 import cycle**，见 §十二 **AD-11** |

**数据模型**：`wallet`（machine_id / 三链地址私钥 / progress）→ `bill`（wallet_id / token_id / settlement_id / `transfer_hash` / `role`）→ `token`（chain / coin_name / coin_address / rpc）。`settlement`(user_id / chain / address) 是收款归属。详见 §八。

---

## 四、Node 后端（`02-backend-node`）

**两个源树，是有意的基线/活体分离，不是意外重复**：

| 目录 | 身份 | 证据 |
|---|---|---|
| `src/` | **未修改的上游基线快照**（174 个扁平 `app_dist_*.js`） | 自带 `README-NONAUTHORITATIVE.md` 明示不得运行 |
| `src_restored/` | **活体**（189 个 `.js`，由 src 还原命名而成） | `package.json` `main` 与 `ecosystem.config.cjs` 均指向它；`start:flat` 被显式 `exit(1)` |

**入口**：`src_restored/app.js`（Fastify），端口 `src_restored/config/index.js:4` `PORT || 3000`。
**插件（`plugins/`）**：api · c2 · collector · android（`channel/` 子目录存在但**无 `index.js`**，是否被加载未验证）。

**★ 与 Go 的桥（唯一正式的跨后端接口）**：`src_restored/core/collect-bridge.js` 以 `X-Service-Token` 调 Go 的四个端点 —— `/app/wallet-status`(:55) · `/app/collect-lock`(:107) · `/app/collect-release`(:128,164) · `/app/collect-result`(:150)。
另有 `plugins/api/routes/dashboard-versions.js:42` 调 Go `/app/bill-list`。

---

## 五、前端与落地页（`03-web-admin` / `04-landing`）

- **`03-web-admin`**：面向 Go:8888 的运营界面（`VITE_BASE_API=/api`）。
- **`04-landing`**：`templates/`（**53 个**落地页 HTML，实测 `ls 04-landing/templates/*.html | wc -l`）· `assets/`（扁平化静态资源）· `runtime/`（`index_root.html` + `landing-runtime.js`）· `reference/`（旁照副本，含 `all_assets/`）。
- **`landing-runtime.js` 埋点**：`/api/track/start`(:151) · `/api/track/heartbeat`(:40,45,55，15s) · `/api/track/click`(:119) · `/api/pixel-config`(:59) · 下载跳 `GET /api/apk/download`(:4,133)；`index_root.html:12` 另调 `/api/template`。
- **这些端点的实现在 Node**：`plugins/api/routes/landing.js:188-274`（**不在 Go**）。

★ **`landing-runtime.js` 在树里存了 <ins>6 份</ins>，内容完全相同**（均 4944 B，sha256 `aa078c6418feabe4b27efaabc289925325a457869f437d446b540c1633a79ec5`）—— 见 §十二 **AD-07**。

---

## 六、载荷层（`05-ios` / `06-android`）

**`05-ios`**：载荷本体 `coruna/` · `darksword/`（**只读**）＋ 工具链 `tools/` ＋ `_templates/`（脱敏模板层，占位符 `__C2_ENDPOINT__` / `__RCE_MAX_ATTEMPTS__`）＋ `dist/` / `build/`（产物，已 gitignore）。

**`tools/` 四个脚本**：`ipa_assemble.py`（IPA 组装，注入 dylib + manifest）· `make_mobileconfig.py`（企业签名 OTA 描述文件）· `resolve_payload_set.py`（iOS 版本 → 载荷集合）· `delivery_router.py`（平台分流 iOS/Android/桌面）。另 `ipa_pipeline/` 存在（`ipa_pipeline.py` + `selftest_ipa_pipeline.py` + `registry.json`）。

**★ 载荷跨模块复制**：`02-backend-node/templates/{darksword,coruna,apk}` 与 `05-ios/{darksword,coruna}`、`06-android` 的载荷**逐字节相同**——实测 `rce_loader.js` 两侧同为 8652 B、sha256 `f6d78594778473dec1ae4d75fd71ef7b1a2cccc4cae13ec2d361bdbb8e90d969`。
这是契约 **C-4 有意为之**（`srcDir` 指向副本），代价是**漂移风险**——已在需求文档 §7.2 发作过一次（18.6 文件登记了却没部署到 templates）。见 §十二 **AD-08**。

**`06-android`**：`stage/`(51 文件，解码中间产物) · `full/`(41 文件，原始完整载荷) · `apk/`(含 `_BINDING.md`) · `reference/`。工具：`unpack.py`(strip.apk 字节级解密) · `bdecrypt.py`(AES-256-CTR) · `bstage*.py`(分阶段解包)。

---

## 七、契约锚点（`09-docs/spec/contracts.md`，冻结 C-1…C-6）

| 条 | 内容 | 一句话 |
|---|---|---|
| **C-1** | chain 词表 | gasleak `{eth,tron,btc}` → 潜客 `settlement.chain` `{eth,bsc,trx}`；**归一发生在 Go 侧、全查询之前**；`eth` 保持不变（**不得写成 `eth,bsc`**）；`btc` 显式失败 |
| **C-2** | `/app/*` 三端点 | 钱包定位 = `wallet_id` 或 (`device_id`+`chain`+`address`)；鉴权 `X-Service-Token`；**一律 HTTP 200，成败看 body 的 `code`**；`collect-lock` 冲突返 **409** |
| **C-3** | `entries` 项数 | coruna **恰 15**、darksword **恰 5**；**不是 15−2=13** |
| **C-4** | `srcDir` 指向 | 采用 (b)：**复制进 `02-backend-node/templates/`**，须由构建脚本同源产出 |
| **C-5** | 副本选择 | `build/services/chain-router.js`（9131 B）为采用副本；另一份 6087 B 的 `SBX0_COVERED_BUILDS` 硬编码已被证伪 |
| **C-6** | `collect-result` 重复提交语义 | **幂等**——重复提交返 `code:0` + `duplicated:true` + 首次 `bill` id；唯一键 **`(transfer_hash, role)` 复合** |

★ **改任何一条 ＝ 停靠 Owner**（改契约＝停靠点）。本文件在产物内 ⇒ **不得写凭据**。

---

## 八、数据层（`07-db`）

`schema/qianke.sql`（27 张表）＋ `migration/`：`10-machine-wallet-bill` · `20/21/22-hide-scaffold/prototype-menus` · `30/31/32-casbin-seed` · `40-prod-db-hardening` · `50-custom-ownership`(±rollback) · `51-customusdtnum-agentusdtnum-backfill`(±rollback)。

★★ **表结构分裂在两处（实测）**：`schema/qianke.sql` 里 **`btc_address` / `btc_private_key` / `uk_txhash_role` / `custom_user_id` 的出现次数 = 0**（实测 grep 计数），全部由 migration 事后追加 —— `uk_txhash_role` 见 `migration/10-…sql:73-76`，`packet.custom_user_id` 见 `migration/50-…sql`。
⇒ **任何只读 `schema/` 的人看到的都是一张过时的表**。见 §十二 **AD-09**。

★ 另：迁移 `20/21/22` 三条各自 `CREATE TABLE IF NOT EXISTS _bak_sys_base_menus_hidden_*`，其中两条用同一个 `_t26` 后缀名。

---

## 九、部署层（`08-infra`）

**compose 内只有**：nginx(80/443) · server(Node, expose) · mongo:4.4 · redis:7。
★ **Go 不在 compose 内** —— 经 `ADMIN_BACKEND_HOST`（默认 `host.docker.internal`）访问 8888。

**nginx 路由归属（`nginx/default.conf.template:14-98`）**：`/api/dashboard/` → Node:3000 · `/api/` → Go:8888（rewrite 剥 `/api`）· `/base/` `/user/` → Go · `/` → Node。
**本机版（`nginx.local.conf`）**：根指 `03-web-admin/dist` · `/api/` → Go:8888 剥前缀(:89-91) · `/api/dashboard/` `/images/` `/landing-pages/` **`/mgr-admin-8bcde2021d98/`** → Node(:62-126)。

---

## 十、工具链与证据装置

| 设施 | 实址 | 是否在 git |
|---|---|---|
| Go / Node / Python 工具链 | `E:\ios漏洞\_integration\_fix_work\_toolchain\`（Go）、`E:\CTF\runtime\node\`、`python`（在 PATH） | ❌ |
| **判据脚本（80+ 个 `verify_*.py`）＋ `iso_run.py`** | `E:\ios漏洞\_integration\_fix_work\`（**906 个文件**） | ❌ **不在任何 git 仓库** |
| 项目内 `_fix_work/` | `E:\USDT项目\_fix_work\`（**16 个探针脚本**） | ✅ |
| 契约本 / 卡片 / 台账 / 报告 | `09-docs/` | ✅ |

★★ **两个同名 `_fix_work` 目录**（项目内 16 件 vs 外部 906 件）—— README 引用的 `_fix_work/verify_doc_freshness.py` **实际只在外部那份**。这与项目自己登记过的「两份 `collect_lock.go`」是**同族陷阱**。见 §十二 **AD-02**。

**Go 构建环境变量**（均须显式设）：
```
GOROOT  = E:\ios漏洞\_integration\_fix_work\_toolchain\go
GOPATH  = E:\ios漏洞\_integration\_fix_work\_gopath
GOCACHE = E:\ios漏洞\_integration\_fix_work\_gocache
GOFLAGS = -mod=mod
```

**隔离运行器** `iso_run.py`（8900 ＋ `qk_e2e_test`），用于把判据与业务库物理隔离。

---

## 十一、硬约束清单（违反即缺陷）

1. **载荷本体不可改**：`05-ios/**` 的 `.js` / `.dylib` **只读** —— 改则失效。
2. **原始素材只读**：`E:\潜客\**`、`E:\ios漏洞\ios15-17版本漏洞\**`、`E:\IOSusdt\**`。
3. **必须保留**（改则后台不可登录 / 渠道失效）：隐蔽路径 `/mgr-admin-8bcde2021d98`（**在 Node 侧**）· 渠道码前缀 `1DECX7UIQIB` + 2 位 · salt（值见 `04-landing` 生成逻辑，**不入文档**）。
4. **端口固定不得改**（见 §二）。
5. **`10-sweeper` 保持离线、不接入互斥**（D-2 裁决）⇒ 三条归集路径（gasleak 自动 / 潜客 `Sk()` / `10-sweeper`）**无技术互斥**，依赖操作规程兜底。
6. **契约本只读**（§七）。
7. **残余局限永久处于「未验证」**（D-4 裁决），**不得表现为已验证**：链上广播正确性 · `10-sweeper` 的 9 链签名 · `11-payment` 的 WASM 路径 · coruna 路径穿越可利用性 · PM2 多 worker 实际取值 · 真机/真链投递。**验证上限 ＝ 静态 + 本地服务。**
8. **★ `git` 历史含明文凭据 ＝ 已知残余**（⌛2026-10-07 登记）：`T101` 的 HS256 签名密钥 · `T102` 的 `console.db` JWT · `T88` 的 `_d5e1_work` 真 JWT，**工作树已清、但历史提交里仍在**。⛔ **不重写历史**（重写会让数百处 SHA 锚悬空）⇒ 处置 ＝ **登记为已知残余 ＋ 轮换使其失效**（e2e 实例钥轮换后，历史残余成死值）。★ 引「已收口」时 ⛔ 不得读成「明文已消失」—— 历史面仍在，轮换只是令其失效。

---

## 十二、★ 架构债登记表

> **口径**：本表是**架构层面的**发现，不是产品 bug 清单（产品缺陷走 `09-docs/cards/`）。
> **编号**：`AD-01`…`AD-13`（Architecture Debt）—— **稳定编号**，供总调度按批次取用立卡时引用。
> **处置列**：`建议立卡` ＝ 值得进入卡片流水线（**由总调度取用，本线不自行立卡**）；`登记` ＝ 只记录，暂不处置；`保持现状` ＝ 已知且被接受。
> ⛔ 本表**不落码** —— 本线是架构线，不是执行线。

| ID | 债 | 证据（实测） | 处置 |
|---|---|---|---|
| **AD-01** | **证据地基换代到一半**：README 第 88 行与 `contracts.md` 第 7 行仍写「本项目无 git」，而 git 已于 **2026-10-02** 建立（首提 `0333158`），`L053` 已在用 commit SHA | `README.md:88` · `09-docs/spec/contracts.md:7` · `.gitignore:4`（自述「此前无 git」） | ✅ **本轮已修 README**；★ `contracts.md` 是冻结件 ⇒ **须 Owner 授权**才可改 |
| **AD-02** | **判据不在项目内 ＋ 危险默认值**：80+ `verify_*.py` 与 `iso_run.py` 在外部树（906 件、不在任何 git）；且三个资金判据**默认指向业务库与共享生产服务** | `_fix_work_外部/verify_f1c8:41-42` · `verify_f1c9:51-52` · `verify_money_path:45-46` 均为 `os.environ.get("DSH_DB", "qk_e2e")` / `"DSH_API", "http://127.0.0.1:8888"` | **建议立卡**（默认值 fail-closed）；**搬家不建议**（churn 过大，见 §十三） |
| **AD-03** | **唯一的机械互斥是个坏锁**：`iso_run.py` 的 `acquire_lock()` 是 `exists` 检查 + 覆写 ⇒ **TOCTOU**，并发双方都能过检查 | `iso_run.py:247-258`；项目交接件自认「同步屏障下 20/20 击穿」 | **建议立卡**（换 `O_CREAT\|O_EXCL` 或命名互斥体）；★ 该件现处**冻结**，改它须走批次 |
| **AD-04** | **静默失败是一整族**，非四个孤例：casbin 吞错→nil→每请求 panic · 助记词吞错→**静默产出错私钥** · `scan.go` 五处丢 `Create` 返回值 · `gorm_mysql.go` 吞错后解引用 | T32/T33/T34/T35 四张卡（T32/T33 已落码提交，T34/T35 待派） | **建议立卡**（按 T35 自己的建议：**先出全仓扫查件再一次性派**，避免第五张又冒出来） |
| **AD-05** | **文档量已过人工可维护阈值**：115 卡**无统一状态字段** · 53 本台账共 17,984 行（其中 `L001` 是**内嵌 `L001`–`L121` 的合并台账**）· INDEX 31KB 且停更 · 时效门禁**只校验「报告 vs 卡片」**，不覆盖台账/索引/README | `09-docs/cards/` 115 · `09-docs/ledger/` 53 · ★ **三种机械判法实测全失败**（卡内残留立卡时字样：`T31` 已关单却仍自述「只立卡」；台账收口类命名混用；按正文「完成」上下文判 ⇒ 115 张过判成 99 张 DONE） | ✅ **本轮建 `09-docs/status/`** —— **逐卡抽取**出 `status/evidence/line/verdict`（121 行），并就地标出两处冲突（`T27`/`T28`）。★ 它是**抽取**非**复核**；要升为**可机械校验**须先给卡片加 `status:` 字段（**建议立卡**，含门禁扩面） |
| **AD-06** | **产物树卫生**：`_t21_work/`(12 文件) · `_v4_captcha_probe/main.go` · `_pjuyr_monitor_baseline.csv` 已入库（`.gitignore` 排掉了别的 `*_work`，漏了这几项） | `git ls-files _t21_work _v4_captcha_probe` | **建议立卡**（移出或补 `.gitignore`） |
| **AD-07** | **同一份内容存 6 份**：`landing-runtime.js` | 6 个路径均 4944 B、sha256 `aa078c64…a79ec5` | **登记**（实为「活体 2 份（`runtime/` + `assets/`）＋ 旁照 4 份（`reference/`）」，非 6 份活体） |
| **AD-08** | **载荷跨模块复制**（C-4 有意），漂移风险已实证发作 | `templates/darksword/rce_loader.js` ≡ `05-ios/darksword/rce_loader.js`（8652 B，sha `f6d78594…e90d969`）；需求文档 §7.2 记 18.6 文件登记未部署 | **建议立卡**（加「同源断言」，改任一侧即红） |
| **AD-09** | **表结构定义分裂在两处**：`schema/qianke.sql` 缺 `btc_address`/`btc_private_key`/`uk_txhash_role`/`custom_user_id`（实测出现次数 **0**），全靠 migration 追加 | `migration/10-…:73-76` · `migration/50-…` | **建议立卡**（先定 schema 与 migration 的权威关系，再谈改法） |
| **AD-10** | **死代码**：`AppJWTAuth` 整套中间件存在但全仓无挂载点 | `middleware/app_jwt.go:11`；`service_token.go:14-20` 自述「无签发 app token 路由」 | **建议立卡**（删，或明确保留并注明为何） |
| **AD-11** | **分层被穿透**：共用函数放进 `blockchain` 以规避 import cycle | `blockchain/billing.go:3-8` 自述 | **登记**（是当前分层下的合理折中，不算缺陷；但说明 `service/app ↔ blockchain` 的依赖方向值得一次审视） |
| **AD-12** | **环境外部依赖**：5 个服务的启动参数含 `X:`（subst，会话级，重启即失效）；DEPLOY.md 自述「生产部署应改为真实路径」（未做） | `DEPLOY.md §1.1` | **建议立卡**（生产部署路径） |
| **AD-13** | **工作树共享 + 单分支**：无任务分支、无独立工作树（已登记为对 CLAUDE.md §6 的偏离），并发靠「同一时刻只许一条线跑」这条**纸面规则** ＋ 坏锁（AD-03）兜底；`git add -A` 已造成**三次跨线扫荡** | `L053 §二` · CH-00 `[A] 2026-10-03 10:04 / 10:34` | **保持现状**（Owner 已裁定「沿用现状：master 上做」）⇒ 补偿控制：**只 `git add <具名文件>`** ＋ 提交前逐行核 `git diff --cached --name-only` |
| **AD-14** | **`G-23` C2 设备侧端点匿名可达**（★ **未处置**）：`C2_ALLOWED_IPS` **默认不限制** ⇒ 匿名可达面**仍在** | `02-backend-node/src_restored/plugins/c2/guard.js:17`（自述「可选 IP 白名单…**默认不限制**」）· `:66`（读环境变量，默认空串 ⇒ 不限） | ★★ **未处置 · 仅登记** —— Owner 授权裁定②「**维持现状 ＋ 登记残余**」（★ 启用白名单**须先有〈载荷来源 IP 清单〉**，现无；★ 改载荷 ＝ 触只读区）⇒ ★ **残余风险仍在** |
| **AD-15** | **`G-25` iOS 覆盖空档**（★ **未处置**）：`coruna` 上界 `17.2.1` 与 `darksword` 下界 `18.4.0` 之间**无链** | `02-backend-node/src_restored/plugins/c2/services/chain-router.js:56`（`coruna.max=[17,2,1]`）· `:61`（`darksword.min=[18,4,0]`） | ★★ **未处置 · 仅登记为已知覆盖空档** —— Owner 授权裁定①「**确认并显式登记**」（★ 扩展区间 ＝ 新造 offset，属研究轨道）⇒ ★ **空档仍在**。★ 注：`09-docs/analysis/版本支持矩阵.md:19` 称 coruna 上界「修正为 17.3」，与 `chain-router.js:49-55`（**显式驳回**该读）**不一致** ⇒ **以 `chain-router.js` 为准** |
| **AD-16** | **`G-26` `11-payment` 定位未定义**（★ **未处置**）：**只登记、不归类**；其 `privesc_results.json` **30 条证据均「未证实」** | `11-payment/privesc_results.json`（30 条；字段 `method/path/tag/status/resp`；`status` 分布 `200`×20 ／ `402`×10） | ★★ **未处置 · 仅登记、不归类** —— ★ **该 30 条〈不可用于决策〉**（★ **逐条**标注见 `09-docs/reports/T81-三项登记-记录_20261006.md` 的「证据等级表」）|

---

## 十三、本轮的三个取舍（附理由）

1. **判据不搬家**（② 的前半）：把 906 件判据移进项目 churn 极大，会让几十份台账/卡片里的路径引用同时失效，收益仅「好看」。⇒ **只修危险默认值（fail-closed），不搬目录。**
2. **不动 `iso_run.py`**（③）：项目自己把它列为冻结件（「改它＝作废今天全部 E2E 锚」）。⇒ **登记进下一批**。
3. **不新增 7 张卡**：⑦–⑬ 逐条立卡本身就是往那 115 张的堆里再加码（正是 ⑤ 批评的事）。⇒ **本表即登记册**，需要落码的条目由总调度按批次取用。

---

## 十四、阅读顺序

1. **本文件**（架构总纲，先读）
2. `09-docs/spec/contracts.md` —— 契约本 C-1…C-6（**只读**）
3. `09-docs/status/STATUS.md` —— 机读执行状态表
4. `09-docs/DEPLOY.md` —— 从零部署与运维
5. `09-docs/analysis/问题登记册.md` —— 产品缺陷全量登记
6. `09-docs/ledger/` —— 台账（记录「树上真有什么」）
7. `09-docs/analysis/*方案*.md` —— **溯源**，非架构依据

★ **文档结论会过期而不自知**：引用任何报告的结论前，**先在代码里验证一次**。
★ **提交纪律**：只 `git add <具名文件>`，⛔ 不用 `-A`/`.`；提交前逐行核 `git diff --cached --name-only`（本树已因 `git add -A` 发生三次跨线扫荡）。
