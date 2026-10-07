# L054 · WBE01 另批 · T32 casbin 初始化失败必须响亮 · 关单台账 [R3]

> **卡**：`09-docs/cards/T32-Casbin吞错导致enforcer永久nil.md`（含派单前总调度 §七 裁定）
> **执行**：总调度**指派的独立子 agent**（后台线前任 01:28 被 Owner 中断、半成品由他人补完）｜ **收口/提交/复核**：总调度第三任 `local_19372a4b-…`
> **落盘时刻**：⌛2026-10-04T15:37:16+0800

## 一 · 档位与理由
**R3**。命中：**动鉴权初始化**（casbin enforcer 构造与启动期可用性）。**门禁强度**：verify 含真实行为断言（V1 启动即失败／V2 正常路径两读数／V3 变异）。★ **但编译门只有执行者单方跑过**（审核者与被禁编译）—— 已列入局限。

## 二 · 内容 SHA
| 位置 | 值 |
|---|---|
| **派审（＝TESTED）** | `65defe788a7cdab730be2e9fb8304c018e8d0cd3`（父 `c6a746c632b939871d3f6541f12f274710745b46`） |
| **审核（三路）** | 三路 `reviewed_sha` **全等于** `65defe7…` |
| **批准** | `65defe7…` |
| **HEAD 后续** | `fcb3bac8b5701f9169d731954212c38df9db58b3`（**纯 gofmt**：只动 import 一行 ⇒ 产品语义与 `65defe7` 逐字节等价，已核 diff） |

## 三 · verify 证据（★ 总调度独立复跑，取码不接管道）
- **V1**（无 `resource/` 的裸目录起）：**退出码 1** ＋ `fatal core/server.go:55 casbin 初始化失败，服务拒绝启动`（带 `model-path` 与真实 cwd）；★ 该行**早于** `initialize.Routers()` 与 `ListenAndServe`。
- **V2**（8900 ＋ `qk_e2e_test`）：`UNAUTH(1234)=code 7` / `AUTH(888)=code 0` ⇒ **GREEN，退出码 0**。
- **V3 变异**：**我未复跑**，采信执行者（改回吞错 ⇒ 进程能起、每请求 500）。
- **业务库护栏**（`iso_run.py`）：8 张表行数与内容哈希**跑前跑后全未变**。

## 四 · Finding 与分歧
**三路全 APPROVED、阻断 0**（A／B／专项）。主要条目：
- **A-1（P2）** 并发捕获分支未调 `ReleaseCollectLock`，与串行分支不对称 ⇒ ★ **调度裁决：降 P3、不阻断**（卡 §四 验收不含该项；可达性极低；占位生命周期归 `/app/collect-lock` 与 `/app/collect-release`；正常同 wallet 无泄漏）—— REMEDIATION 原样入下一批。
- **★ 三路独立收敛**：`isDuplicateKey` 只判 `Number==1062`、**不校验键名**（A-3／B-1／F1）⇒ 登记 P3。
- **F2／A-4**：`:114 _ = syncedEnforcer.LoadPolicy()` **仍吞错**（BASE 既有行、§7.3 只点名"两处 `_`"）⇒ 登记 P3。
- **A-3**：`os` import 排序 → **gofmt 违规**（★ **由调度实测发现**，非审核者报）⇒ 已修（`fcb3bac`）。
- **B-2**：`GVA_DB == nil` 时 `Init()` 无 nil 守卫 ⇒ 前提**已核实**（`gorm_mysql.go:17-18` 确 `return nil`）；运行态**未验** ⇒ 登记 P2。
- **F3**：报错含 cwd/model-path，`%w` 上浮的 DSN 片段**未证实**。
★ **无阻断级分歧**（三路同判 APPROVED）。

## 五 · 规模与余量
被审件 **2 个 · +45/−2**（`core/server.go` +10/−0 · `sys_casbin.go` +37/−2）；`fcb3bac` 另 +1/−1。台账目录余量充裕，**无需拆件**。

## 六 · 局限（如实）
① **编译门未独立复跑**（审核者与调度均被禁编译）⇒ `go vet`/`BUILD_EXIT=0` 只有执行者单方读数；② **未部署**（8888 仍跑 `a293fc95…`）；③ V3 未复跑；④ 三路**均不能连库** ⇒ 运行态靠静态推演。
