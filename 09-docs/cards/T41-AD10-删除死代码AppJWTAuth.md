# T41 —— `AD-10` 删除死代码 `AppJWTAuth` 整套中间件（＋并死的 `utils.NewAppJWT`）

> **卡**：T41 ｜ **承**：`ARCHITECTURE.md` §十二 `AD-10` ＋ `09-docs/reports/AD-10-AppJWTAuth死代码确认_20261004.md`（`aee905df…`/6553 B）
> **档**：**R2**（删产品码；虽"删死码"风险低，但**触鉴权文件** ⇒ 不按 R1 放行）｜ **授权**：★ Owner ⌛2026-10-04「按照这个顺序做完」（⑤ 的 AD-10）
> **执行**：待派（建议后台线·新）｜ **收口/提交/复核**：总调度第三任
> **★ 状态**：**已立卡、待派** ｜ **日期**：2026-10-04

---

## 一 · 事实（**AD-10 方案件已确认**）

`middleware/app_jwt.go` 的 **`AppJWTAuth`** 全套：**挂载点 0 处**，其**全部出现皆为注释** ⇒ **死代码**。
`utils.NewAppJWT`（`service_token.go:14-20` 自述"无签发 app token 路由"）**仅被它调用** ⇒ **一并死**。

## 二 · ★★ 一条**必须遵守**的更正（AD-10 方案件查出，勿误判）
**`config.AppJWT` <ins>不是</ins>整块死配置** —— **`middleware/service_token.go:24`** 的 `ServiceTokenAuth()`（**活代码**）**在读 `global.GVA_CONFIG.AppJwt.ServiceToken`**（服务间共享密钥，gasleak → 潜客 归集回传桥的 `X-Service-Token`）。
⇒ **删 `AppJWTAuth` 时<ins>必须保留</ins> `config.AppJWT.ServiceToken`**（及其结构体字段与配置键）。
★★ **⌛2026-10-04 路径更正（执行者查出）**：本卡原文写的是 `service/system/service_token.go:24` —— ★ **该文件<ins>不存在</ins>**；真身是 **`middleware/service_token.go:24`**（**正是本卡 §三 列为"不得动"的那一份**）。已按真身更正。

## 三 · 范围
| 项 | 内容 |
|---|---|
| **删** | `01-backend-go/middleware/app_jwt.go` 的 `AppJWTAuth`（整个函数及其专属辅助）· `utils.NewAppJWT`（若确无其它调用者） |
| ★ **保留（硬要求）** | `config.AppJWT` 结构体与 `ServiceToken` 字段 · `.env`/`config.yaml` 里 `app-jwt.service-token` 键 · `middleware.ServiceTokenAuth`（**那是活的**，与 `AppJWTAuth` 是两码事） |
| ⛔ **不得** | 动 `middleware/jwt.go`（`JWTAuth`，活代码）· 动 `middleware/service_token.go`（活）· 改任何鉴权语义 |
| ★ **停止条件** | 若删除牵出**其它引用**（含测试/配置文件/文档/生成物） ⇒ **先列清单报总调度**；若发现它其实**被动态引用**（反射/插件注册） ⇒ **停手报总调度** |

## 四 · 验收
| # | 断言 |
|---|---|
| **V1** | ★ **删前先证"确实无调用者"**：全仓 grep（含 `*.go`、配置、文档、脚本）**逐条列出全部命中**，并逐条判"是注释还是真调用"（★ 方案件已给：**全部出现皆为注释** —— **你要自己复跑确认，别采信转述**） |
| **V2** | 删除后：`go build ./...` **EXIT=0** ＋ `go vet ./...` **EXIT=0**（若有未用 import/符号，这里会红） |
| **V3** | ★ **`ServiceToken` 那条路不被误伤**：`grep -n "ServiceToken" service/system/service_token.go` 仍命中；且 `go test ./...` **EXIT=0** |
| **V4** | ★ **行为不变**：`/device/list` 未授权仍 `code=7`、授权仍 `code=0`（现存判据件 `t32_device_list_judge.py` 可复用；★ 但它**必须先过 `T36` 的 fail-closed 闸** ⇒ 须走 `iso_run` 或显式注入 `DSH_*`） |

## 五 · 边界与停靠点
- ⛔ 不直连业务库；⛔ 不做 git 写操作；⛔ 同一时刻只许一人改/编/跑本仓 Go；⛔ 不碰 `8888` 主栈。
- ★ **判据走隔离实例**（8900 ＋ `qk_e2e_test`）；★ 改后按 P-18 **重编译**；取码**不接管道**。

---

> **落款时刻（照抄 `date` 输出，非手写）**：`2026-10-04T17:0x+0800`
