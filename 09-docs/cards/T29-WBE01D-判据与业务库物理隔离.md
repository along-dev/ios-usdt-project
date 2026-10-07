# T29 —— WBE01-D：判据／业务库**物理隔离**（(乙-1) 第二实例 ＋ 第二库）—— **已落地并验收**

> **卡**：T29（＝ WBE01-D）｜ **档**：**R2**｜ **线**：后台线（接班人 `local_96adb6ae`）
> **依据**：总调度裁定 6／7（Owner 已批端口段与构建）· WBE01-D 方案 §4
> **★ 状态**：**已落地、已跑通、护栏通过** —— `ISO_RUN=OK`（⌛2026-10-03T18:53）
> **日期**：2026-10-03

---

## 一 · §4-1 前提：**成立**（裁定要求"不成立就停下报我"）

| 检查 | 结果 |
|---|---|
| Go 侧读取点 | `initialize/gorm_mysql.go:15-34` `GormMysql()` 取 `global.GVA_CONFIG.Mysql`，DSN 由 `m.Dsn()` 拼（`config/gorm_mysql.go:17`） |
| 是否硬编码库名 | **否** —— 全仓 `grep "qk_e2e" --include=*.go` 只命中注释（`service/app/bill.go:8`）与测试守卫（`blockchain/billing_test.go:33`） |
| 配置键 | `_i2c1_ws/config.yaml:104` `db-name: qk_e2e` 可改 |

⇒ **只靠 config 就能指另一个库**，**前提成立**，未触发"停下"。

★ **顺带发现**：`initialize/RegisterTables()` 的 AutoMigrate **同时建系统表与业务表**（`app.Bill/Custom/Agent/Packet/Wallet/...`）；`billing_test.go` **本就预留**了同款隔离守卫（`WBE01A_TEST_DSN`，且**硬拒**含 `qk_e2e` 的 DSN）。

## 二 · 构建（**实测耗时**，非估值）

| 项 | 值 |
|---|---|
| 命令 | `go build -o _wbe01d_bak\_i2c1_server_iso.exe .`（`GOROOT/GOPATH/GOCACHE/GOFLAGS` 同卡A 开发期） |
| **实测耗时** | **245 秒**（`BUILD_EXIT=0`） |
| 产物 sha256 / bytes | `75337750de2776dfd7b14d3f6b032ca3b1cf374fe297c8005319ff980e3a72c9` / 43,670,016 |
| ★ 附带 | 本次构建**含 T28 的 casbin 改动** ⇒ **T28 的源码改动能编译**（编译级验证完成） |

## 三 · 隔离构成

| 件 | 内容 |
|---|---|
| `_wbe01d_ws/config.yaml` | 由现 config 复制，**只改 2 处**（已断言各恰 1 次）：mysql `db-name: qk_e2e_test`、system `addr: 8900`（`diff` 实测**仅此两行不同**） |
| `qk_e2e_test` | 独立库（utf8mb4） |
| `seed_test_db.py` | **schema 克隆 + 播种**；带**硬闸**（`DSH_DB == 来源库` 直接拒绝，已实测会红） |
| `iso_run.py` | 一条命令跑完全程：起 8900 → 克隆结构 → 播种 → 跑判据 → 停 → 报告；**护栏永远查业务库** |
| 三判据脚本 | `DB_NAME`/`API` 改 `os.environ.get("DSH_DB"/"DSH_API", <现默认>)` —— **默认值逐字等于现状**（已核）；并加 §4-7「★ 连接目标：DB=… API=…」响亮提示 |
| `run_regression_v2.py` | 护栏 `DB_NAME` 改 `os.environ.get("DSH_GUARD_DB","qk_e2e")` —— **不跟随 `DSH_DB`**（它证的必须是业务库） |

## 四 · ★★ 关键修正：**"AutoMigrate ⇒ 同源"是错的**（本卡最大发现）

> **方案 §4-4 原文**：播种器"必须用实例 B 的 **AutoMigrate**（同源）"。**实测证伪**。

**证据**（⌛2026-10-03，本线首次跑出的真红直接暴露）：

| 列 | 业务库 `qk_e2e`（**迁移**建的） | 隔离库（**AutoMigrate** 建，`DefaultStringSize:191`） |
|---|---|---|
| `num` / `usdt_num` / `total_num` | `varchar(32)` | **`varchar(191)`** |
| `transfer_hash` / `order_id` | `varchar(128)` | **`varchar(191)`** |

**列数相同、列类型不同** ⇒ 后果**可观测**：`money_path` 的 `(c) amount 超精度` 用例（33 位小数）在业务库因 **"Data too long"** 被拒（`code≠0`），在 AutoMigrate 建的隔离库**装得下 ⇒ `code=0` 被接受** ⇒ **真红**。
⇒ 若照原方案做，隔离环境**不保真** ⇒ **判据结论"与真实环境无关"** —— 正是方案 §6 预警的「**播种漂移**」。

**修正**：测试库结构改为**克隆业务库**（逐表 `DROP + CREATE TABLE ... LIKE`，**只克隆结构、不搬数据**），并加**保真度核对**（逐表逐列比 `COLUMN_TYPE`）。
★ **顺序要点**：克隆必须在**实例启动之后**做 —— 否则启动期的 AutoMigrate 会把 `varchar(32)` 又加宽回 `varchar(191)`（`iso_run.py` 里已按此序实现并注明）。

## 五 · 验收读数（⌛18:53，`ISO_RUN=OK`）

```
  [health] http://127.0.0.1:8900/health ⇒ {"checks":{"mariadb":{"ok":true},"redis":{"ok":true}},"status":"ok"}
  [schema] 克隆 28 张表结构（跳过备份表 _bak_sys_base_menus_hidden_t26）
  [保真] ✓ 两库列类型逐列一致
  [rows] machine 9 · agent 2 · packet 1 · wallet 2 · custom 1 · settlement 8 · token 2 ；bill 行数 = 0（不种 bill）
  [suite] verify_f1c9_toaddress_guard.py   EXIT=0  GREEN
  [suite] verify_f1c8_amount_guard.py      EXIT=0  GREEN
  [suite] verify_money_path.py             EXIT=0  GREEN   ← ★ 修正前此项 RED（§四）
  ✓ 护栏：业务库 8 张表**行数与内容哈希全未变**（隔离有效）
```

**护栏读数（跑前 = 跑后，逐表）**：
`bill=18/95b6eea9 · settlement=8/57e79218 · token=2/f6322cd3 · wallet=2/3b1e3a4e · custom=1/50493461 · agent=2/2b27ab77 · packet=1/f4421208 · machine=9/9a788926`
⇒ ★ **业务库一个字没碰**（行数与**内容哈希**双判据）。

★ **共享 8888 全程未触碰**：跑完实测 `/health` 仍为新结构、PID 仍为 **9660**（与跑前同一进程）。

## 六 · 已知边界／不在范围

| 项 | 说明 |
|---|---|
| **Redis ~~共用~~** | ~~隔离实例与 8888 **共用** 16379（config 只改了 mysql 与 addr）⇒ `collect-lock` 等 Redis 状态**跨实例共享**。~~ ★ **该表述已过期** —— ⌛2026-10-03 起隔离实例改走 **`redis.db = 1`**，见 **§十（T30）**。 |
| **sys_* 表数据** | 结构克隆自业务库，**行**由实例启动期 `EnsureSeed` 生成（空库自愈）。⇒ 依赖 sys_* 数据的判据（RBAC 类）**尚未纳入本隔离**。 |
| **覆盖范围** | 本轮只跑**3 个会写 `bill` 的判据**；主回归集 50 个脚本的**全量**隔离运行**尚未做**。 |
| ⛔ 不换共享件 | **未触碰** `_i2c1_server.exe`；**未改** `config.yaml`（只新增 `_wbe01d_ws/config.yaml` 副本） |

## 七 · 产物（⌛18:53）

| 件 | sha256 | bytes |
|---|---|---|
| `seed_test_db.py` | `df428c9e1d6288cd5cd357bfda3358d3c59b491c029b08c7e13231258d9b8b39` | 7376 |
| `iso_run.py` | `d222292565820764daedc5e6afc0086a52fe2e863f99feade5293efd08b10338` | 9937 |
| `run_regression_v2.py` | `ada1b1a1652471cf9a351f0eb20b72ff3f933230b8cb6efd7134570066b11cd9` | 36364 |
| `verify_f1c9_toaddress_guard.py` | `5708c0cbf1af2b703140d3ae2cc7b33996931a4fe113c268ba2a2409978e3c28` | 20888 |
| `verify_f1c8_amount_guard.py` | `fe5889df85d5dac4517dbd07b47304d0da446b9b7bf246b567cf04f53f0bd918` | 10033 |
| `verify_money_path.py` | `9c8b203470380cda6dae4a3c383cdca38c2f9b1eab30c5e59e0ad159b3976773` | 22840 |
| `_wbe01d_ws/config.yaml` | `53b0a1033a93c57a17995e6088b6e83064aef6515578f04a6cc2c57c9de34b04` | 3778 |
| `_wbe01d_bak/_i2c1_server_iso.exe` | `75337750de2776dfd7b14d3f6b032ca3b1cf374fe297c8005319ff980e3a72c9` | 43,670,016 |

★ 三个判据脚本的 sha 相对 T27 那次**又变了**（因为本轮加了 `DSH_DB`/`DSH_API` 注入与响亮提示）—— **以上表为准**。

## 八 · 停靠点

1. ★★ 若把**并发类判据**纳入隔离 ⇒ 需先决定 Redis 是否也隔离（§六）
2. ★ 若要跑**全量 50 脚本** ⇒ 需先补 `sys_*` 数据的播种（§六）
3. ★ 任何触及**共享 8888** 的动作 ⇒ 停下升级（本卡不碰）

---

> **落款时刻（照抄 `date` 输出，非手写）**：`2026-10-03T18:53:16+0800`

---

## 九 · 追加（⌛2026-10-03T19:35:38+0800）：复核 F-03/F-05/F-06/F-07/F-08 落地

> ★ **本节的 §9.5 指纹表 <ins>取代</ins> §七** —— `iso_run.py` 与隔离 exe 均已变（§七 的 `d2222925…`/`75337750…` 已过期）。

### 9.1 落地清单

| finding | 改法 | 件 |
|---|---|---|
| **F-03 ＋ F-05** | 把「CAS ＋ 累加」抽成**唯一一处** `MarkProcessedAndAccumulate`，**产品码与单测共调** | `blockchain/billing.go`（**新增函数**）· `blockchain/scan.go`（改调）· `blockchain/billing_test.go`（**两处改调** ＋ **新增 1 条用例**） |
| **F-06** | `stop_iso` 的 `taskkill` 补 `errors="replace"` | `iso_run.py` |
| **F-07** | 复用 8900 前**校验身份**（映像名 ＋ `/health` 双判据）；不通过 ⇒ **抛错拒绝** | `iso_run.py` |
| **F-08** | **两态在同一次运行内跑完**（置绑定 → 跑 → 置解绑 → 跑 → **复位**）；**只动隔离库** | `iso_run.py` |

### 9.2 ★ 变异演示（F-05 的验收读数）

| 变异 | 结果 |
|---|---|
| 去掉 `RowsAffected != 1` 那道守卫 | **必红** → `幂等失败：status=1 再进仍累加，实测 "20"（应 0）` |
| 去掉 `AND status = 0`（复核点名的那个） | ★ **加新用例前仍 GREEN**；**加后必红** → `★ status 非 0（异常态）的行不得被处理；实测累加为 "10"（应 0）` |

### 9.3 ★ 两条新证据（供复核方）

1. **MySQL 的 `RowsAffected` 计的是 changed rows** ⇒ 在 `status ∈ {0,1}`（**实测该列在本项目只有这两个值**：A 路建 0、B 路建 1；业务库 18 行全为 1）下，把已是 1 的行再置 1 得 **0 changed** ⇒ **`RowsAffected != 1` 那道守卫照样兜住幂等** ⇒ **`AND status = 0` 是冗余防御**（这解释了为什么"去掉它"原本不可检出）。
2. 新用例改用 **`status IS NULL`**（`bill.status` 列**可空**，业务库与本测试库均如此 ⇒ **可达的数据状态**）⇒ 此时去掉 `AND status = 0` 会让 `NULL → 1` **算 changed** ⇒ 被错误处理 ⇒ **该条件从此独立可检**。

### 9.4 复跑读数（⌛19:35）

- **单测**：`go test ./blockchain/ -run '(TestAccumulate|TestMarkProcessed)' -v` ⇒ **3 个函数 / 5 个用例 全 PASS**
- **静态**：`go vet ./blockchain/ ./service/app/` ⇒ **exit 0**；`gofmt -l` 三件（`billing.go`/`scan.go`/`billing_test.go`）**全干净**
- **隔离端到端**：`iso_run.py` ⇒ **两态各一遍 6/6 GREEN**、护栏「业务库 8 表行数与内容哈希全未变」、**已复位 `custom_user_id=201`**
- **F-07 双向演示**：起后复用路径 ⇒ `[probe] … image='_i2c1_server_iso.exe' …` ＋ `[skip] 身份校验通过 ⇒ 复用`；**拿非本实例占 8900** ⇒ `image='python.exe'` ⇒ **`False` ＋ 抛错拒绝复用**
- **共享 8888** 全程未触碰（`/health` 仍为新结构）

### 9.5 指纹（**取代 §七**）

| 件 | sha256 | bytes |
|---|---|---|
| `01-backend-go/blockchain/scan.go` | `f27a27036b3f52b3994397c97416ade2acca1f76a8945ee0cf1e2ea50c3239d8` | 19942 |
| `01-backend-go/blockchain/billing.go` | `84c3b8b024c2c55d26b7438f1623f4e42bc4e31b913721556f005d2c5aa07b1a` | 5907 |
| `01-backend-go/blockchain/billing_test.go` | `bd252f88bcf54c60eed01b043968aa28c8f54e4d93c84e34d3fb0d159d98b1ec` | 7905 |
| `iso_run.py` | `26c3b92ad9d0a6038a00d25ba748e95cd07681764019f89138802c13b8a804d8` | 13148 |
| `_wbe01d_bak/_i2c1_server_iso.exe` | `a6241201e63e0cb1424aafb48fcae277cee988e4b1adab4bea3a50ef6ffbd17b` | 43,673,088 |

★ 三个判据脚本（f1c9/money_path/f1c8）**本轮未动**，指纹同 §七；`packet.go`/`collect_result.go` 亦未动。
★ **一处需声明**：`gofmt -w billing_test.go` 除修我的注释块外，还**顺带规整了 `TestAccumulateUsdtNum` 里既有的 6 行 struct 字段对齐**（`name`/`role`/…，**纯空白、无语义**，非本卡引入）。为使该文件 gofmt 干净、便于复验，未拆开保留。

---

## 十 · 追加（⌛2026-10-03T20:15:00+0800）：**T30 —— Redis 隔离**（含一处**护栏范围更正**）

> **依据**：总调度裁定（T30）· 由**苹果线自纠**（它指出自己报告里「未碰共享设施」措辞过宽）。★ 这条纠得对。

### 10.1 ★ 护栏范围**限缩为 MySQL**（此前那句"隔离有效"过宽）

**被取代的原话（逐字，仍在 §五）**：`✓ 护栏：业务库 8 张表**行数与内容哈希全未变**（隔离有效）`
⇒ **该句的「隔离有效」应读作「<ins>MySQL</ins> 隔离有效」** —— 当时 **Redis 并未隔离**（实例 B 与主栈共用 16379，**连 `db` index 都是 0**）⇒ 护栏**从没覆盖 Redis**。现已在 §五/此处的护栏输出里写明分项。

### 10.2 §-1 前提：**成立**（`db` 键真的被读取）

`initialize/redis.go` 的 `redis.NewClient(&redis.Options{ Addr:….Addr, Password:….Password, **DB: redisCfg.DB** })` —— 把 config 的 `db` 直接传给 go-redis（标准 `SELECT` 语义）；`config/redis.go:4` 亦有 `DB int`（`mapstructure:"db"`）。
⇒ **无硬编码 0** ⇒ 改法 ②（同实例换 db index）**可行**，未触发"退回 ①"。

### 10.3 落地

| 项 | 内容 |
|---|---|
| config | `_wbe01d_ws/config.yaml` 的 `redis.db: 0 → 1`。★ 与主栈 config 的差异**恰为 3 处**（`db-name` / `redis.db` / `system.addr`，已 `diff` 实测） |
| 护栏 | `iso_run.py` 新增 `redis_snapshot/redis_diff`：**永远查主栈 `db0`**（⛔ 不跟随隔离实例的 `redis.db`），取 **键数 ＋ 键名有序哈希**（同 MySQL 护栏那套） |

### 10.4 ★★ 两条必须写的实测读数

**(a) 命名空间确已分离**（正证）：往 **db1** `SET dsh-probe` ⇒ `db1 = 1 键(hash ffe9fd0c…)`、**`db0` 仍 0 键**；删除后各自复原。

**(b) ★ 护栏当前**对这三个判据是**空转的**（如实写，不粉饰）：整轮跑下来 `db0 = 0 键`、`db1 = 0 键` —— 即 **`iso_run` 的 3 个判据压根不写 Redis**（它们走 `/app/*` ＋ 服务令牌，不经 JWT 黑名单／限流）。⇒ 「主栈 db0 前后未变」**当且仅当**这条是**空洞为真**。
⇒ **含义**：Redis 隔离**已就位**（口径正确），但**要它真正受力，须把会写 Redis 的判据（RBAC/JWT 黑名单/限流类）也纳入隔离套件**。⇒ 见 §六 的「`sys_*` 未播种」，两者是同一批活。

### 10.5 ★ 过程失误（已入账 `E-359`）

护栏初版取值用 `redis-cli --scan` —— **本机这份 redis-cli 的 `--scan` 静默返回空**（退出码 0、无输出；同时刻 `DBSIZE`=1、`KEYS '*'` 能列出）⇒ 护栏**恒报 0 键、永不报警**（＝本项目「恒绿的检查＝没有检查」）。改用 `KEYS '*'` 后，**负控**（往 db0 `SET` 哨兵键）⇒ `redis_diff = ['主栈 db0 键数 0→1']` ⇒ **能红**。
★ 已按 §9 入账 **`E-359`**，并记下更值钱的一层：**同一会话里我刚因 `--selftest-assert` 亲手演示过"判据必须能红"，转头对新护栏却没做同一件事**。

### 10.6 指纹

| 件 | sha256 | bytes |
|---|---|---|
| `_wbe01d_ws/config.yaml` | `11dc3c3d9744fe39322e5fee21c23375d9d639fc69feb4b1b81ba0e4c01375da` | 3778 |
| `iso_run.py` | （见 T30 卡；本节落笔后再变） | — |

---

> ★ **时效注记（⌛2026-10-04 · 总调度 · 连同 `T36` 同批）**
> 本件所引的三个判据脚本 sha **是<ins>本件当时</ins>实测值，⛔ 已按纪律<ins>原样保留</ins>**。此后 **`T36`（`AD-02` 判据 fail-closed）** 给 5 件判据各加了「拒绝裸跑」硬闸 ⇒ **sha 已变**，**新值以 `09-docs/reports/判据脚本改动记录_T36_20261004.md`（`e7f9320ceba2513da6772ef757df9844defc843657702d4c785197e52ee8b459`）为准**：
> · `verify_f1c9_toaddress_guard.py`　`5708c0cb…`/20888 → **`a87295ee2467076e26981165c2cd124f91c49c80efbc282894684ade85f21fd2`**/21112
> · `verify_f1c8_amount_guard.py`　`fe5889df…`/10033 → **`f93c1772fe0d9cca87edb9e0d2fedea93d3e4ccc723e70243ac24080b5650f46`**/10257
> · `verify_money_path.py`　（本件记的 `9c8b2034…`/22840 **在 T36 之前就已不是当时的真值**）→ 现为 **`ce00c3177d4eb02cdd4b24ae0e21d10e8e9915021fbee8dd285ec9ff4e057a98`**/24459
> ⇒ 上列旧值**仍然可用作"当时测量"的凭据**（它们确实是那一刻的读数），但 **⛔ 不得再当"当前指纹"引用**。

---

## 十一 · ★ 锚更正留痕（⌛2026-10-05 20:25 +0800 · `T60` 执行追加）—— `iso_run.py` 锚**再变**，§七 / §9.5 两处旧锚作废
> ★ 承卡 `09-docs/cards/T60-iso_run互斥锁根治-F10-AD03方案A.md`；★★ **⛔ 未就地抹 §七 / §9.5 原文** —— 原字仍在上方，本节点为**追加**。
> ★ **事由**：`T60` 把 `iso_run.py` 的 `acquire_lock()` 根治为 **`O_CREAT|O_EXCL` 原子抢锁 ＋ `os.replace` 原子搬走陈旧锁**（`F-10`；`AD-03` 方案 A）⇒ **该件 sha 再变**。
> ★ **本卡内锚的链**：§七 `d2222925…`/9937 ⇒ §9.5 `26c3b92a…`/13148 ⇒ （`T55`/`T57` 期冻结 `f4ae3e8242cee3117e734598a23557999af52b73eb5a2715fb168ea7ef08d4ed`/17963，2026-10-03 20:23）⇒ ★★ **`T60` 后现读 `974273e95d945accd599247cd673add381dfc6ce4a80c1a639839bec65ae908c` / 19513 B**。
> ★ **§七 与 §9.5 的 `iso_run.py` 行（`d2222925…` / `26c3b92a…`）<ins>均已过期</ins>** ⇒ ★ **引用前一律 `sha256sum` 现场重读**；★ 本卡**只追加、不改原行**。
> ★ 出处：`09-docs/reports/T60-iso_run互斥锁根治-记录_20261005.md`。
