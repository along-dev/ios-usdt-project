# T44 —— `T39` `F-1` 重裁落地：`Sk` 返回 error、`ShouGe` 上报（让中止**真正传播**）

> **卡**：T44 ｜ **来源**：`T39` 追补审核 `F-1`（**P1 阻断**，**两路独立**：安卓线 ＋ 苹果线均自达）
> **档**：**R3**（触**资金路径**）｜ **授权**：★ **总调度第四任 ⌛2026-10-04 重裁**（承 Owner 令「继承并继续任务」；钱包均为交付范围内测试数据，不按真实事故升级）
> **执行**：后台线（新）`local_d91c3753-4ab3-4128-93d3-9df12ffc3a4d` ｜ **收口/提交/复核**：总调度第四任
> **★ 状态**：**已立卡、待派** ｜ **日期**：2026-10-04

---

## 一 · 缺陷（**总调度第四任现读，非转述**）

`blockchain.Sk(walletId int)` **无返回值**；其**唯一调用者** `QianKeService.ShouGe` 在 `:160` 调它之后**无条件 `return nil`**：

```go
// service/system/sys_qianke.go:160
blockchain.Sk(walletId)
return nil
```

⇒ `Sk` 的内部**中止**（尤其是 `scan.go:45` 的 `Save(progress=1)` 失败 ⇒ **本次收割未发起**）**无法传播** ⇒
**`POST /device/shougei` 仍回 `response.Ok(c)`**，用户看到"收割成功"，实际**未开始**。

**全链（受审 SHA `a237d1f` 上实读）**：
`router/system/sys_qianke.go:23` `deviceRouter.POST("shougei", qkApi.ShouGe)`
→ `api/v1/system/sys_qianke.go:377` `qiankeService.ShouGe(req.WalletId)`
→ `service/system/sys_qianke.go:160` `blockchain.Sk(walletId)`（**其后无条件 `return nil`**）
→ `blockchain/scan.go:21 func Sk(walletId int)`（**无返回值**）。

★ **调用面只有 1 处**：`git grep -n "Sk(" -- 01-backend-go/` ⇒ 仅 `scan.go:21`（定义）＋ `sys_qianke.go:160`（调用）。
★ **`Sk` 是同步的**（转账内联执行）；`scan.go:302` 的 `go func()` 只是 **2 分钟后的状态核对**，不改变"中止不可传播"这一事实。

---

## 二 · 目标

**`Sk` 的"中止本次收割"必须让调用方可见** ⇒ `Sk` 返回 `error`，`ShouGe` **原样上报**，接口如实回失败。
★ **不得改变成功路径行为**（成功时 `ShouGe` 仍 `return nil`、API 仍 `Ok`）。

---

## 三 · 范围

| 项 | 内容 |
|---|---|
| **改** | `01-backend-go/blockchain/scan.go`：`func Sk(walletId int)` ⇒ **`func Sk(walletId int) error`** |
| ★ **逐处 return** | `:26`（`wallet.ID == 0`）与 `:32`（无余额）⇒ **`return nil`**（**合法空操作，不是错误**）· `:45`（`Save(progress=1)` 失败）⇒ **`return fmt.Errorf("Sk 标记 progress=1 失败，中止本次收割: %w", err)`**（**保留既有响亮日志**）· **函数尾**（`scan.go` 中 `Sk` 的闭合 `}` 之前）⇒ **`return nil`** |
| **改（连带，1 处）** | `01-backend-go/service/system/sys_qianke.go:160`：`blockchain.Sk(walletId)` ⇒ **`return blockchain.Sk(walletId)`** |
| ⛔ **不得** | 改 `Sk` 内的**转账／分账／记账语义**（金额、比例、归属）· 改 `ShouGe` 除该行外的任何逻辑 · 改 `collectMode()` 互斥判据 · 把成功路径的 `return nil` 改成 error |
| ★ **停止条件** | 若发现 `Sk` 内**除 `:45` 外**还有**应中止并上报**的失败点（须改变现有"记日志 ＋ continue"语义）⇒ **停下报总调度**（那属扩大，须另裁）；⛔ 本卡**只做**"让 `:45` 的中止可见"这一件 |

---

## 四 · 验收

| # | 断言 |
|---|---|
| **V1** | ★ **主断言（可构造）**：构造 `Save(progress=1)` **必失败** 的调用（如：单测里以 **sqlmock／fake driver** 让 UPDATE 报错；或最简——**直接调用 `Sk` 并让其前置 UPDATE 失败**）⇒ **`Sk` 返回非 nil error**，且 **`ShouGe` 把它传出去**（API 层回 `FailWithMessage`）。★ 若本仓无 sqlmock（`go.mod` 现状：mysql ＋ testify）⇒ 用**临时 Go 测试 ＋ 可控 driver**，或**明写"未构造 ＋ 为什么 ＋ 等价静态依据"**（依据：`Sk` 的返回值类型 ＋ `ShouGe` 的 `return blockchain.Sk(...)` 已是**语言级**可证的传播链）。 |
| **V2** | **成功路径不变**：`Save` 成功 ＋ 有余额 ⇒ `Sk` 返回 `nil`、`ShouGe` 返回 `nil`、API 回 `Ok`（逐处对照，控制流只有错误分支变了）。 |
| **V3** | **变异**：把 `ShouGe` 的 `return blockchain.Sk(walletId)` 改回 `blockchain.Sk(walletId); return nil` ⇒ **V1 必红**（API 仍回 Ok）。★ 变异后**按字节精确还原**。 |
| **V4** | `gofmt -l`（2 件）空 · `go build ./...` 真退出码 · `go test ./blockchain/` 真退出码；★ 改后按 **P-18 重编译**。★ **取码不接管道**。 |

---

## 五 · 边界与停靠点

- ★ 判据走隔离实例（8900 ＋ `qk_e2e_test`）；⛔ 不直连业务库；⛔ 不做 git 写操作（提交权在总调度）；⛔ 同一时刻只许一人改/编/跑本仓 Go；⛔ 不碰 `8888` 主栈。
- ★ **触资金路径 ＋ 鉴权面**（`ShouGe` 在 `qianke` 路由组下）⇒ 本卡改动**只是让既有中止可见，不改任何金额/分账/归属语义**；若执行中发现**需要改语义**（例如"失败应当回滚已建 bill"）⇒ **停下报总调度**。
- ★ **同期约束**：`T40`（`BcryptHash` 签名根治）已由后台线完成、**待复核后由总调度提交** ⇒ 本卡**不得**去动 `utils/hash.go`／`service/system/sys_user.go`／`source/system/user.go`（避免与 T40 的工作区改动相撞）。
