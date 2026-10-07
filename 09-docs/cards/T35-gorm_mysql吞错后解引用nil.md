# T35 —— `initialize/gorm_mysql.go`:`db.DB()` **吞错后立即解引用** ⇒ nil 时 panic（**只立卡，不落码**）

> **卡**：T35 ｜ **档建议**：**R2** ｜ **线**：待派
> **依据**：总调度 ⌛2026-10-04 取证复核（登记于 `T32` §7.4）；由 T32 取证 agent 报出、总调度**复读原文核实**
> **★ 状态**：**只立卡、未落码** —— ★ **⌛2026-10-04 Owner 已授权**；**排队待派**（T32→T33→T34→T35 **串行**：四卡共用同一 `_i2c1_server.exe` 构建产物，P-18/P-38）
> **日期**：2026-10-04

---

## 一 · 现状（**已核实**，⌛2026-10-04 总调度读码复核）

`01-backend-go/initialize/gorm_mysql.go:27-31`：

```go
if db, err := gorm.Open(mysql.New(mysqlConfig), internal.Gorm.Config()); err != nil {
	return nil                                    // ← 只判了 gorm.Open 的错
} else {
	sqlDB, _ := db.DB()                           // ← 错误被吞
	sqlDB.SetMaxIdleConns(m.MaxIdleConns)         // ← sqlDB 为 nil 即 panic
	...
```

`01-backend-go/initialize/gorm_pgsql.go` **同形**。

**性质**：与 T32 **同族**（**吞错 ⇒ nil ⇒ 解引用**），但发生在 **DB 初始化期** ⇒ 失败形状是**启动期 panic**（有栈、可读），比 T31 那条 casbin 的**每请求 panic** **可见性高一档** ⇒ 危险性低一档。

★ **与 T32 的区别（写清楚，免得派重）**：T32 的病是「失败被吞 + `sync.Once` 不重试 ⇒ 进程内**永不**自愈、且只表现为**请求级** 500」；本卡的病是「初始化期一次 nil 解引用 ⇒ **启动即崩**」。

## 二 · 目标

`db.DB()` 的错误**不得吞**；拿到 nil 时**必须响亮失败**并说清是**哪一步**（`gorm.Open` 之后取 `*sql.DB` 失败）。

## 三 · 范围

| 项 | 内容 |
|---|---|
| **改** | `initialize/gorm_mysql.go` ＋ `initialize/gorm_pgsql.go` 的 `sqlDB, _ := db.DB()` 一处 |
| ⛔ **不得** | 改连接参数/DSN/池参数的**取值**（`MaxIdleConns`/`MaxOpenConns`/`ConnMaxLifetime` 一律不碰，只加错误检查） |

## 四 · 验收

> ★★ **⌛2026-10-04 口径更正（R3 两路独立收敛后由总调度改）**：**本卡 V1/V3 按原文<ins>不可执行</ins>**。
> 两路（苹果线 `F-B-1`、安卓线 `F-01`）**各自独立**从三方库源码得出：`gorm.io/driver/mysql@v1.0.1` 的 `ConnPool` **恒为 `*sql.DB`**（`dialector.Conn == nil` 时走 `sql.Open`），`gorm@v1.22.5` 的 `DB()` **恒走 `return sqldb, nil` ⇒ 永不返回 error** ⇒ **被修的那条分支在 stock 驱动下不可达**，`panic` 触发不了 ⇒ **V1「构造 `db.DB()` 必失败」无执行路径，V3 依赖 V1 同不可执行**。
> ⇒ **本卡已落码的改动仍判「正确但属防御性」**（不退回改码）；**验收改为对<ins>可达路径</ins>断言**。

| # | 断言（**更正后**） |
|---|---|
| **V1′** | ★ **可达路径**：把 DSN 指向**连不上的库** ⇒ `gorm.Open` **必须响亮失败**、并在**日志/栈里说清是「DB 连接失败」而不是别的模块**。（当前实测：该路径走 `return nil`，最终以 nil 解引用倒在 `blockchain/scan.go:17` ⇒ **指向错误的文件** ⇒ **本条现在必红**，见下"另立项"） |
| **V1″**（可选、更强） | 若坚持要覆盖 `db.DB()` 那条分支 ⇒ **必须在单测里注入非 `*sql.DB` 的 `ConnPool`**（`mysql.New(mysql.Config{Conn: …})`）—— 生产配置只给 DSN，**唯一**能触发的构造方式 |
| **V2** | **正常 DSN** ⇒ 行为不变（服务起得来、既有查询语义逐项对照）。★ R3 只做了**静态**判定（错误分支之外零改动）；**运行态未实测** |
| **V3** | **变异**：把错误处理改回 `_` ⇒ 所采用的 V1′ **或** V1″ **必红**（取决于选哪条） |

★ **另立项（本轮 R3 新增，非本卡范围）**：**可达的 DB 失败路径失败形状误导** —— `gorm.Open` 失败 ⇒ `Gorm()` 返回 nil ⇒ `EnsureTablesAndSeed()` 只 `Warn` 后 `return` ⇒ `core.RunWindowsServer()` 里 `blockchain.LoadRpcList()`（`blockchain/scan.go:17` 的 `global.GVA_DB.Find(...)`，**无 nil 守卫**）**panic** ⇒ **栈顶指向链上扫描模块**。应另立卡：**给"DB 连不上"一条自己的、指名道姓的启动期响亮失败**。★ 与本卡同族（启动期失败形状）。

★★ **⌛2026-10-04 调度裁决（两审核者分歧，已用受控实验定案）** —— **本路径是 fail-closed，不是半启动**
- **分歧**：苹果线 `reviewer B` 读「两处启动期消费者容忍 nil ⇒ **main 不失败**」；安卓线 `专项` 读「紧接着那句 `LoadRpcList()` 是**无条件**调用、其 `if err := …; err != nil` **只接得住 error、接不住 panic** ⇒ **崩在 listen 之前**」。
- **裁决依据（受控实验，非推理）**：把隔离 ws 的 `config.yaml` 的 DB 端口由 `13306` 改成 **`13399`（连不上）**、保留 `resource/`，用**从 HEAD 重编的件** `8f3dba9a…` 起：
  ```
  PROBE_EXIT=2
    gorm.(*DB).getInstance(0x0?)      ← nil 接收者
    .../blockchain.LoadRpcList()   blockchain/scan.go:17
    .../core.RunWindowsServer()    core/server.go:43
    main.main()                    main.go:42
  → 8900 未监听（端口从未绑定）
  ```
- **⇒ 安卓线对**：该路径 **panic 崩在 `scan.go:17`、退出码 2、端口从未绑定** ⇒ **fail-closed**。苹果线那条读数**不完整**（漏了那句无条件调用）。
- **更正一处引用**：崩溃点在 **`scan.go:17`**（`Find` 那行）；本卡上文与部分审核件写的 `:14` 是 `RpcList` 变量声明处，**不是** panic 行。
- **证据留盘**：`E:\ios漏洞\_integration\_fix_work\_t35dsn_probe_result.txt`（sha256 `98687a37387ae56fd0d2e7dd8c5165381eda8043c2b807d04c35d07c85cab923`）。★ 临时 ws 与 probe exe 已删。

## 五 · 边界

- ⛔ **不在本批**；只立卡、不落码。★ **不阻塞 T31/T32**。
- ★ 与 T32 / T33 / T34 **同族**（**静默失败**）—— ★ **本卡是该族的第 4 张**；若四张同批修，建议**一次把「吞错 ⇒ nil ⇒ 解引用」全仓扫一遍**再派，避免第五张又冒出来。

## 六 · 停靠点

1. ★ 动**初始化路径** ⇒ 按 T32 停靠点办理（停下、等 Owner 单独授权）
2. ★ 若扫查发现该族**超过 5 处** ⇒ 停下，先出**扫查件**（不逐处立卡）

---

> **落款时刻（照抄 `date` 输出，非手写）**：`2026-10-04T00:44:54+0800`
