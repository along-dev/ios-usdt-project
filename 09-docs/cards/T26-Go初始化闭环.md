---
id: T26
mode: 实施
wave: 审核修复·批次2
depends: [T25]
task_branch: 无
review_level: R3
状态: ★ **Owner 已裁决**：「继续批次 2」
定档理由: |
  ★★★★ **审核 B 的 B-01/02 [Blocker]**：**Go 初始化体系是死代码**。
  ★★ **调度取证（决定性）**：
    · `main.go` **仅 30 行**，**零行**调用 `RegisterTables()` 或 `InitDB()`
    · **`RegisterTables()` 全仓零调用点**（只有定义）
    · `/init/initdb` 因 `GVA_DB != nil` **恒短路**（`sys_initdb.go:23-27`）
    · ⇒ **空库启动：连表都不建、无 admin**
  ★★ **且这是 C-2 的前置**（**casbin 无策略**）⇒ **R3**（**涉部署正确性**）。
  门禁强度自知：**须在【空库】上实测**（**不得只在现库上试**）。
来源: ★★★★ **审核 B**（B-01/02）
      + ★★ **审核 C**（C-2：casbin 为空）
      + ★★ **Owner 裁决**（**批次 2**）
      + ★★★ **调度取证**（**见下**）
base:
  - path: 01-backend-go\main.go
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
  - path: 01-backend-go\initialize\gorm.go
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
allowed_paths:
  - ★ 01-backend-go\main.go（★ **加初始化调用**）
  - ★ 01-backend-go\initialize\**（★ 加自愈逻辑）
  - ★ 01-backend-go\cmd_seed\**（★ 独立 seed 工具，**新目录**）
  - ★ 09-docs\reports\上线加固清单.md（★ 更新）
  - 09-docs\reports\残余暴露面登记.md（★ 更新 R-15）
  - E:\ios漏洞\_integration\_fix_work\verify_t26_init.py
forbidden_paths:
  - "★ 01-backend-go\\middleware\\casbin_rbac.go（★ C-2 留批次 2 后半）"
  - "★ 02-backend-node\\**（★ 批次 2 不含 Node）"
  - "03-web-admin/**、04-landing/**、05-ios/**、06-android/**"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_t26_init.py    # 动前红 / 动后绿
packages: {}
---

# T26 [R3] Go 初始化闭环（**B-01/02 + C-2 前置**）

## ★★★★ 调度取证（**决定性**）

### `main.go`（**仅 30 行**）

```go
:22  func main() {
:23      global.GVA_VP = core.Viper()            // 初始化Viper
:24      global.GVA_LOG = core.Zap()             //
:25      zap.ReplaceGlobals(global.GVA_LOG)
:26      global.GVA_DB = initialize.Gorm()       // ★ 只连库，不建表
:28      initialize.Timer()
:29      core.RunWindowsServer()
     }
```

### `RegisterTables()` **全仓零调用**

```
initialize\gorm.go:28  func RegisterTables(db *gorm.DB) {   ← 只有定义
全仓 grep "RegisterTables" ⇒ 2 处（都是定义/注释）
```

### `/init/initdb` **恒短路**

```go
// api/v1/system/sys_initdb.go:23-27
if global.GVA_DB != nil {
    global.GVA_LOG.Error("已存在数据库配置!")
    response.FailWithMessage("已存在数据库配置", c)
    return                                    ← ★ main.go:26 总会赋值 ⇒ 恒短路
}
```

**★ 实测**：`POST /init/checkdb` ⇒ `{"needInit":false}`（**系统自认"无需初始化"**）

### ★★ 且 `CheckDB` 的判据**不足**

```go
// sys_initdb.go:54
if global.GVA_DB != nil { needInit = false }   ← ★ 只看连接，不看表是否有数据
```

---

## ★★ 规格（**三层**）

### (1) ★★ 修 `main.go`：**加初始化调用**

```go
func main() {
    global.GVA_VP = core.Viper()
    global.GVA_LOG = core.Zap()
    zap.ReplaceGlobals(global.GVA_LOG)
    global.GVA_DB = initialize.Gorm()

    // ★ T26（B-01/02）：以下调用缺失导致【空库启动不建表】。
    if global.GVA_DB != nil {
        initialize.RegisterTables(global.GVA_DB)   // ★ 建表（幂等，AutoMigrate）
    }

    initialize.Timer()
    core.RunWindowsServer()
}
```

★ **`RegisterTables` 是 `AutoMigrate`（幂等）⇒ 对已有库安全。**

### (2) ★★ 写**空库自愈**（`initialize/ensure_seed.go`）

**检查关键表是否为空 ⇒ 若空则跑 seed。**

★ **须复用既有 `source/system/*` 的 `SubInitializer` 体系**
（**`InitDBService.InitDB()` 是唯一驱动，但它会 `EnsureDB` + `WriteConfig`**）。

**★ 更可控的做法**：**直接调用各 initializer 的 `MigrateTable` + `InitializeData`**，
**但 `initializers` 注册表未导出** ⇒ **须在 `service/system` 包内加一个导出函数**：

```go
// service/system/sys_initdb.go 追加
// ★ T26：供空库自愈使用 —— 只跑 seed，不建库、不改配置。
func (initDBService *InitDBService) SeedOnly() error {
    ctx := context.TODO()
    ctx = context.WithValue(ctx, "db", global.GVA_DB)
    sort.Sort(&initializers)
    if err = createTables(ctx, initializers); err != nil { return err }
    for _, init := range initializers {
        if init.DataInserted(ctx) { continue }
        if ctx, err = init.InitializeData(ctx); err != nil { return err }
    }
    return nil
}
```

★ **且 `ensure_seed.go` 须判断"是否真的空"**（**不能每次都跑**）：
**检查 `sys_users` 是否有记录** ⇒ **有则跳过**。

### (3) ★ 独立 `cmd_seed` 工具

**`01-backend-go/cmd_seed/main.go`**：**命令行触发 seed**（**便于运维**）。

★ **用法**：`go run ./cmd_seed` 或编译成 `_seed.exe`。

---

## ★★ 判据要求

| # | 断言 |
|---|---|
| **V1** | ★★★ **空库测试**：**在一个【新库】上启动 Go ⇒ 表被自动创建**（**`sys_users` 等 13 张表存在**）|
| **V2** | ★★★ **空库启动后 `sys_users` 有 admin**（**或明确说明 seed 由谁跑**）|
| **V3** | ★★ **已有库启动不变**（**幂等：不重复插入、不破坏数据**）|
| **V4** | ★ **`go build ./...` EXIT=0** |
| **V5** | ★ **既有功能未回归**（**`/health` 200、`/app/wallet-status` 带 token 200**）|
| **V6** | ★ **`上线加固清单.md` 的 §三-4/§三-5 已更新**（**casbin 前置关系**）|
| **V7** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **V1+V2 是核心**（**证明"从空库能起来"**）。
★ **V3 是"不破坏现有"的证据**（**幂等**）。

## ★ 不在范围

- ★★ **不改 `casbin_rbac.go`**（**C-2 的后半，需先有 casbin 数据**）
- ★ **不改 Node**
- ★ **不动 `config.yaml` 的 `env`**

## ★ 证据要求

- ★★★ **V1 的空库实测**（**新建库名 + 表清单**）
- ★★ **V2 的证据**
- ★ **V3 的幂等证据**（**跑两次，第二次无变化**）
- ★ **V4 的 `go build` EXIT**（**★ 注意：需 ~30 分钟**）
- ★ **V5 的回归证据**
- ★ 判据真实退出码（动前红 / 动后绿）
- ★ 声明：**未改 `casbin_rbac.go`、未改 Node**

## 停靠点

1. ★★ **若 `RegisterTables` 在现有库上会失败**（**如视图冲突**）⇒ **停下报告**
2. ★★ **若空库 seed 需要用户输入**（**如 `InitDB` 的请求体**）⇒ **停下报告**
3. ★★ **若改 `main.go` 影响其他初始化顺序** ⇒ **停下报告**
4. ★ **若 `go build` 超过 40 分钟** ⇒ 停下报告

## ★★ 环境提示（**关键**）

```
★ 本机【无 pwsh】，用 powershell
★ Go: E:\ios漏洞\_integration\_fix_work\_toolchain\go\bin\go.exe
★ Go 环境变量：
    GOROOT  = X:\_integration\_fix_work\_toolchain\go
    GOPATH  = X:\_integration\_fix_work\_gopath
    GOCACHE = X:\_integration\_fix_work\_gocache
    GOFLAGS = -mod=mod
★★ 【go build 需 ~30 分钟】（E-01 实测 1798 秒）⇒ 用 Start-Job 后台跑
★★ 构建产物：X:\_integration\_fix_work\_i2c1_server.exe
★★ 【改 exe 前必须备份】（P-43：T22 曾丢失 exe）
★ 服务 8888 由 _i2c1_server.exe 提供，cwd = X:\_integration\_fix_work\_i2c1_ws
★★ 【启动 Node 需等 135 秒】（P-44）—— 本卡不涉及 Node，但重启 8888 后需等
★ MariaDB: 127.0.0.1:13306 root 无口令（--skip-grant-tables）
★ 新建测试库：qk_t26_empty（用后按需保留/删除）
```
