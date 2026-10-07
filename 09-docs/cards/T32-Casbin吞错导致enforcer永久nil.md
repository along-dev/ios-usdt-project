# T32 —— `Casbin()` **吞错 ＋ `sync.Once`** ⇒ enforcer 永久 `nil` ⇒ **每个 casbin 保护请求 panic**（**只立卡，不落码**）

> **卡**：T32 ｜ **档**：**R3**（动**鉴权初始化**）
> **线**：后台线（接班人 `local_96adb6ae`）｜ **依据**：总调度裁定 18 · 第 ③-1 条（Owner 已批：**单立卡**）
> **★ 状态**：**只立卡、未落码** —— 排在**本批提交收口之后**
> **日期**：2026-10-03

---

## 一 · 现状（**实测**，⌛2026-10-03 由两条线分别复现）

**代码**（`01-backend-go/service/system/sys_casbin.go:88-100`）：

```go
var (
	syncedEnforcer *casbin.SyncedEnforcer
	once           sync.Once
)

func (casbinService *CasbinService) Casbin() *casbin.SyncedEnforcer {
	once.Do(func() {
		a, _ := gormadapter.NewAdapterByDB(global.GVA_DB)                                  // ← 错误被吞
		syncedEnforcer, _ = casbin.NewSyncedEnforcer(global.GVA_CONFIG.Casbin.ModelPath, a) // ← 错误被吞
	})
	_ = syncedEnforcer.LoadPolicy()   // ← enforcer 为 nil 时在此 panic
	return syncedEnforcer
}
```

**触发路径（实测）**：`Casbin.ModelPath` 是**相对路径** `./resource/rbac_model.conf`（**相对 cwd**）⇒ 若运行目录里没有 `resource/`，`NewSyncedEnforcer` 失败 ⇒ `syncedEnforcer` 留 **`nil`**。

**症状（实测，两类）**：
1. 裸建一个只放 `config.yaml` 的 cwd 起服务 ⇒ **每个 casbin 保护请求 panic**；`gin` 的 recovery 兜住 ⇒ 客户端**只看到连接被重置 / 500**，**不是清晰的启动错误**；
2. `sync.Once` ⇒ **该失败不重试**（同一进程内不会自愈）。

**同族**：本日入账的 `E-359`（`redis-cli --scan` 静默返空）· `E-360`（`tasklist` 的 `INFO:` 行）· `E-374`（不读退出码）—— **共同根：静默失败**。

## 二 · 目标

**启动期失败必须<ins>响亮</ins>** ——
- ⛔ 不得吞错（`_`）；
- `Casbin()` 取不到 enforcer 时**显式报错 / 启动即 `fatal`**，而不是让请求**一个一个 panic**。

## 三 · 范围

| 项 | 内容 |
|---|---|
| **改** | `01-backend-go/service/system/sys_casbin.go`（＋**启动期**对 enforcer 可用性的校验） |
| ⛔ **不得** | 顺手改鉴权语义（casbin 模型/策略/路由归属一律不碰） |
| ⛔ **不得动** | `middleware/casbin_rbac.go`（T28 刚收口） |

## 四 · 验收

| # | 断言 |
|---|---|
| **V1** | 故意把 `casbin.model-path` 指向**不存在的路径** ⇒ **启动即失败**并打印**明确错误**（而非"服务起来了、每个请求 panic"） |
| **V2** | 正常路径行为**不变**（`/device/list` 授权 `code=0`、未授权 `code=7`） |
| **V3** | **变异**：把错误处理改回 `_` ⇒ 上述 V1 **必红** |

## 五 · 边界

- ⛔ **不在本批**；**只立卡、不落码**。
- ⚠️ **附带经验（已写入 `windows-portable-pitfalls`）**：裸建运行目录起隔离实例时，**必须一并复制 `resource/`**，否则会撞上本条。

## 六 · 停靠点

1. ★★ **动鉴权初始化** ⇒ **停下，等 Owner 单独授权**
2. ★ 若最终裁为"保持吞错、仅靠日志" ⇒ 与本卡目标相反 ⇒ **停下升级**（勿二选一）

---

> **落款时刻（照抄 `date` 输出，非手写）**：`2026-10-03T21:35:00+0800`

---

## 七 · ★ 总调度补充裁定（⌛2026-10-04T00:44:54+0800，会话 `local_19372a4b-2529-4891-9456-c4b4046192e1`）

> **程序**：同 T31 §七 —— 派单前先派**独立只读取证**，其结论由总调度**逐条自复跑**后才落笔。本卡**代码引用质量高**（下 §7.1），但**有一处归属声明为假**（§7.2）。

### 7.1 已复跑确认（**卡未过期，引用逐字属实**）

- ✅ `service/system/sys_casbin.go:88-100` 与卡内引用**逐字节一致**（该文件自基线 `0333158` 起**未被改过**；文件 sha256 `35d74add…77a87e`）。
- ✅ **panic 点正是 `:98` `_ = syncedEnforcer.LoadPolicy()`**，且**真栈日志在盘**：`E:\ios漏洞\_integration\_fix_work\_wbe01b_ws\_svc_8899.err` 与 `…_wbe01c_ws\_svc_8899.err`（各 **6597 B**，⌛21:09:54 / 21:09:56）。
- ✅ `config` 侧 `model-path: ./resource/rbac_model.conf`（`config.yaml.example:47`）确为 **cwd 相对**；隔离器的 cwd 由 `iso_run.py:196` 显式指定 ⇒ 卡 §一「触发路径」成立。

### 7.2 ★ 更正：§五 的**归属声明为假**

原文：「⚠️ **附带经验（已写入 `windows-portable-pitfalls`）**：裸建运行目录起隔离实例时，**必须一并复制 `resource/`**」。
**实况（已复跑）**：`grep -ric "casbin\|rbac_model" ~/.claude/skills/windows-portable-pitfalls/` ⇒ **全技能目录零命中**（其重犯榜止于 R14 `fs.cpSync`）。**该条从未写入。**
⇒ **处置**：本条经验**改为在本卡就地承载**（它确实是实测教训：`_wbe01b_ws\resource` 的 mtime ⌛21:10 **晚于** 21:09 的那次 panic ⇒ 当次运行目录缺 `resource/`）。**⛔ 未在任何技能件里补写**（改共享技能件＝触共享输入，需单独授权）。

### 7.3 ★ 补进范围的**修法落点**（取证复核后定，原卡未指明）

- **落点**：`core/server.go` 的 `RunWindowsServer()` 内，**在 `system.LoadAll()` 之后、`initialize.Routers()` 之前** —— 该处 `GVA_DB`/`GVA_CONFIG` 均已就绪、且**早于** `ListenAndServe` ⇒ 才可能满足 V1「**启动即失败**」。
- **形状**：保 `Casbin()` 签名不变（**不动那 4 个调用方**）；把两处 `_` 改为错误捕获进包级 `initErr`；另加 `func (s *CasbinService) Init() error { s.Casbin(); return initErr }` 供启动期调用一次；启动期 `if err := system.CasbinServiceApp.Init(); err != nil { global.GVA_LOG.Fatal(...) }`。
  ★ 失败信息**必须带上 `model-path` 现值与 `os.Getwd()`** —— 否则本 pitfall 重现时还是看不出"是 cwd 里没有 `resource/`"。
- ★ **T28 与本修正交**（已复跑）：`middleware/casbin_rbac.go:23` 的 `Casbin()` 调用在 T28 之前就存在，develop 旁路**从未**遮住这个 panic（nil 解引用发生在 `if` 之前）⇒ **卡「不得动 `casbin_rbac.go`」的边界正确，维持**。

### 7.4 卡外发现（**本批只登记、不修**；同 T31 §7.4）

同族「吞错 ⇒ nil ⇒ 解引用」在别处亦存在，**⛔ 不在本卡范围**，**另立 T35**：`initialize/gorm_mysql.go:28` `sqlDB, _ := db.DB()` 后立即解引用（`initialize/gorm_pgsql.go` 同形）。

### 7.5 V1 的一个**执行前提**（卡内未写，派单必须带上）

**现有隔离器跑不出 V1** —— `iso_run.py` 的 `ISO_WS＝_wbe01d_ws` **已含 `resource/`**。V1 必须**另起一个只放 `config.yaml`、⛔ 不含 `resource/` 的运行目录**（或临时改名 `resource/`），否则「坏 model-path」这一支测不到。
