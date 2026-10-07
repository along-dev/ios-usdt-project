---
id: D0-C4
mode: 实施
wave: P0
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  ★ **命中真高危路径**：`01-backend-go/service/app/wallet_resolver.go`
  （路径清单明列"真高危 → 命中即 R3"）。
  本卡改的是【钱包定位】—— 它决定后续 lock/release/bill 落账作用于哪个 wallet。
  缺陷性质：wallet_id 直传分支【无条件信任】，而服务间是【单一共享 token】
  ⇒ 持 token 者可对任意 wallet 执行 lock / release / report。
  ★ 属"权限"类（路径清单 §停靠点明列"触碰资金、权限"须停靠）
  ⇒ **R3**。
  门禁强度自知：判据含结构断言 ⇒ 必须补【真 HTTP 越权尝试】的运行时断言。
来源: 补审报告_R3C1与P1复核 §6.2（P1-5 残余）
      + 调度本轮实测（分支体确为 `return walletId, nil` 单行）
      + Owner 裁决 (a1)（交叉一致性校验）
base:
  - path: 01-backend-go\service\app\wallet_resolver.go
    sha256: ee5a913fd1a8c84d4b97e9593817a99a38167e37b8ec6283aa770b154a8c9ccb
    bytes: 2367
    eol: LF
allowed_paths:
  - 01-backend-go\service\app\wallet_resolver.go
  - E:\ios漏洞\_integration\_fix_work\verify_d0c4_walletid_owner.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "01-backend-go\\model\\**（★ 本卡【不得】改 DTO —— 契约 C-2；见停靠点 2）"
  - "01-backend-go\\service\\app\\collect_lock.go、collect_result.go（调用点不得改 —— 校验须在 resolver 内做）"
  - "01-backend-go\\api\\v1\\app\\wallet_status.go（同上）"
  - "01-backend-go\\blockchain\\**（D0-C3 的范围）"
  - "E:\\潜客\\**、E:\\ios漏洞\\ios15-17版本漏洞\\**、E:\\IOSusdt\\**（只读素材）"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d0c4_walletid_owner.py    # ①动前：须【红】，退出码 != 0
  - python _fix_work\verify_d0c4_walletid_owner.py    # ②动后：须【绿】，退出码 0
  - go build ./...                                    # 退出码 0
  - go vet ./service/app/                             # 退出码 0
packages: {}
---

# D0-C4 [R3] `ResolveWalletId` 的 `wallet_id` 直传分支无任何归属校验

## 目标

让 `wallet_id` **与** `device_id`+`address` **同时提供**时，
三者必须**指向同一个 wallet**；不一致则**拒绝**。

## ★ 缺陷事实（调度实测确证）

### 分支体确为**无条件直取**

```go
// wallet_resolver.go:36-38
if walletId > 0 {
    return walletId, nil          // ★ 分支体只有这一行（实测）
}
```

**而反查路径（:48-55）有约束**：

```go
Joins("left join machine on machine.id = wallet.machine_id").
Where("machine.device_id = ? AND wallet."+col+" = ?", deviceId, address).
```

**⇒ 两条路径的严格性不一致**：反查严格，直传**完全信任**。

### 危害（如实登记）

- 服务间鉴权是**单一共享 token**（`X-Service-Token`），**非按调用方区分**
  ⇒ **持该 token 者可对任意 `wallet_id` 执行 lock / release / report**。
- ★ **缓解因素**：`ServiceTokenAuth` 是 fail-closed（未配置即拒绝），
  且该 token 仅 gasleak 服务持有 ⇒ **利用门槛 = 先取得服务间密钥**。
  ⇒ 严重度 **P1**（非 P0）。

### ★ 为何当前接口设计下"真正的归属校验"不可实现

**DTO 无调用方身份字段**（实测）：

```
ReqCollectResult / ReqCollectLock / ReqCollectRelease 的字段仅：
  wallet_id / device_id / address / chain (/ tx_hash / amount / to_address / collected_at)
```

**无 `machine_id` / `agent_id` / 调用方身份** ⇒
"校验 wallet 属于调用方"**在改契约前不可行**。

### ★ 但 (a1) 可行（Owner 已裁）

**4 个调用点【全部】同时持有 `wallet_id` 与 `device_id`+`address`**（实测）：

| 调用点 | 传参 |
|---|---|
| `service/app/collect_lock.go:54` | `req.WalletId, req.DeviceId, chain, req.Address` |
| `service/app/collect_lock.go:87` | `req.WalletId, req.DeviceId, req.Chain, req.Address` |
| `service/app/collect_result.go:62` | `req.WalletId, req.DeviceId, chain, req.Address` |
| `api/v1/app/wallet_status.go:41-42` | `walletId, c.Query("device_id"), c.Query("chain"), c.Query("address")` |

★ 且 `wallet_status.go:38` 的注释印证设计意图：
> `wallet_id 与 device_id+chain+address 二选一：gasleak / sweeper 侧不持有 wallet id`

**⇒ 设计上是"二选一"，但实现允许"都传且不校验一致性"** —— **这就是缺口**。

## 规格

### (a) 在校验分支内做交叉一致性

**位置**：`wallet_resolver.go` 的 `walletId > 0` 分支。

**语义**：

```
当 walletId > 0：
  · 若 deviceId 与 address 【均非空】⇒ 校验该 walletId 指向的 wallet
    是否满足 (machine.device_id == deviceId AND wallet.<col> == address)；
    不满足 ⇒ return 0, error（拒绝）
  · 若 deviceId 或 address 缺省 ⇒ 保持既有语义（直接返回 walletId）
```

★ **第二点是硬要求**（防改过头）：**不得**因为缺省参数就拒绝，
否则会破坏 `wallet_status.go` 等既有调用。

### (b) 复用既有的列白名单

`chain → 地址列`的映射已有 `walletAddressColumns`（`:26-32`）。
**必须复用**，**不得**新造映射（避免 SQL 注入面与分叉）。

★ **不支持的 chain** 在直传路径下的处置：
- 若 `deviceId`/`address` 缺省 ⇒ 不校验（保持既有语义，**不因 chain 不支持而拒绝**）；
- 若两者**均非空** ⇒ chain 不支持则应拒绝（因为无法完成校验）。

### (c) 错误信息须可诊断

拒绝时应给出可定位的信息，例如：
```
fmt.Errorf("wallet_id=%d 与 device_id/address 不一致", walletId)
```
**不得**泄漏敏感信息。

## ★ 判据先于实现（判据 9）

`verify_d0c4_walletid_owner.py`（已写，**先红**）：

| # | 断言 | 红态 |
|---|---|---|
| C1 | `walletId>0` 分支内引用 `deviceId` 与 `address` | 缺 ⇒ **红** |
| C2 | 分支内有「不一致 ⇒ 拒绝」出口 | 缺 ⇒ **红** |
| C3 | 校验以「两者均非空」为前提（兼容只传 wallet_id） | 缺 ⇒ **红** |
| C4 | 反查路径（`machine.device_id`）保持可用 | 绿 |
| C5 | 3 个调用文件仍传 `device_id`/`address` | 绿 |
| C6 | **DTO 未新增归属字段**（未触碰契约 C-2） | 绿 |

## ★ 必须补的真 HTTP 运行时断言（门禁越弱审核越深 · R3 要求）

结构断言**不足以**证明越权已被阻断。执行者须起服务（Go **8888**）实测**至少 3 例**：

| 例 | 请求 | 期望 |
|---|---|---|
| **R1** | `wallet_id=<存在的> + device_id/address 均正确` | **通过**（`code=0`） |
| **R2** | `wallet_id=<存在的> + device_id/address 均错误` | **拒绝**（`code!=0`） |
| **R3** | `wallet_id=<存在的> + 不传 device_id/address` | **通过**（兼容既有语义） |
| **R4** | `wallet_id=<不存在的>` | 拒绝（明确报错，非静默） |

★ 遇服务未起/DB 不可用 ⇒ **如实说明并跳过**，不得编造。

## 不在范围

- **不改 DTO**（契约 C-2 只读）—— 若你认为必须改 ⇒ **停下升级**（停靠点 2）
- 不改调用点（校验须在 resolver 内做）
- 不改 `blockchain/**`（D0-C3 范围）
- 不改 `_manifest.sha256`

## 证据要求

- `verify_d0c4_walletid_owner.py` 改前红 / 改后绿两次真实退出码
- `wallet_resolver.go` 改前 / 改后 sha256
- `go build ./...` 与 `go vet ./service/app/` 真实退出码
- ★ **R1–R4 的真 HTTP 响应原文**（含 `code` 与 `msg`）
- ★ 明确声明：**未改 DTO、未改调用点**

## 停靠点

1. 若发现**除 wallet_id 外还有其他绕过路径** ⇒ 停下升级
2. 若必须改 DTO 才能实现 ⇒ **停下升级**（触契约 C-2）
3. 若 R3 例（不传 device_id/address）**无法保持通过** ⇒ 停下升级（会破坏既有调用）
4. 若实测发现现网数据**不满足**新校验（如 wallet 的 device_id 与传入不一致）
   ⇒ **停下升级**（可能是既有数据问题，不是本卡能解决的）
