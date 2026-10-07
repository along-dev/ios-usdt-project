# AD-10 方案件 —— `AppJWTAuth` **死代码确认** ＋ 删/留建议

> **编号**：`AD-10`（承 `09-docs/ARCHITECTURE.md` §十二 架构债登记表）｜ **性质**：**只出件，⛔ 不落码**
> **件**：`01-backend-go/middleware/app_jwt.go` 等（**本仓内产品码**）
> **产件**：后台线（接班人，本会话）｜ **时刻**：⌛2026-10-04 15:26:37 +0800
> **★ 全部 sha 均为本件落笔时【现算】，64 位全长**；所有 grep 均为**本件实读**（命令随附）。

---

## 一 · 事实（**实读，非转述**）

| 件 | sha256（现算） | 字节 |
|---|---|---|
| `01-backend-go/middleware/app_jwt.go` | `c1a0cc1357a7c5fab48be9464bf05cc53f19237033798998067ef49ec37d919e` | 3020 |
| `01-backend-go/utils/app_jwt.go` | `4c43ed4011d7c64255c8979a0f06b00323837e3ed895a426aab8c4b1d32333bb` | 4558 |
| `01-backend-go/config/jwt.go` | `c2daa2d14a980d381dfaa98e32ef6738795a8dc0c15f3ec57f96b3a169b77006` | 1592 |
| `01-backend-go/middleware/service_token.go` | `44488c460143e8b9cbf84228b63e538c270cbd53744fffdc35f2b41eea17ccc7` | 1557 |
| `01-backend-go/initialize/router.go` | `056c881ac8ea0cff4bd8c65ba992238db2471edb2659e066d0517049277a957f` | 5979 |
| `01-backend-go/api/v1/app/public.go` | `f35f81d8346b966f5b09029bd4b895e1742f44ad08cf3f70a2088dac3054e0fc` | 2847 |

### 1.1 定义

```go
// middleware/app_jwt.go:11
func AppJWTAuth() gin.HandlerFunc {
    return func(c *gin.Context) {
        accessToken  := c.Request.Header.Get("access-token")
        refreshToken := c.Request.Header.Get("refresh-token")
        j := utils.NewAppJWT()                       // ← 唯一调用点（:15）
        ...                                          // 解析 token + 查 Redis 存在性 + 刷新
    }
}
```

### 1.2 ★ 挂载点：**0 处**

实读：`grep -rn "AppJWTAuth" 01-backend-go --include=*.go | grep -vE ":\s*//" | grep -v "func AppJWTAuth"` ⇒ **空输出**。

`AppJWTAuth` 的全部出现处**都是注释**：

| 位置 | 原文（摘） |
|---|---|
| `config/jwt.go:16` | `// ★ 与 SigningKey 用途不同：SigningKey 签 App 用户 JWT，仅 app_jwt 中间件使用；` |
| `config/jwt.go:18` | `//   不用 AppJWTAuth 的原因：本仓无 app token 签发路由（tokenNext 已注释），` |
| `middleware/service_token.go:14` | `// 为什么不用 AppJWTAuth：` |
| `middleware/service_token.go:17` | `//  2. AppJWTAuth 还要求 token 同时存在于 Redis（app_jwt.go 的 GVA_REDIS.Get），` |
| `middleware/service_token.go:19` | `//  3. 调用方 gasleak 是【服务端】而非 App 用户，AppJWTAuth 是给设备侧设计的。` |

★ **`tokenNext` 确已整段注释**（实读 `api/v1/app/public.go:54` 起）：

```go
//// 登录以后签发jwt
//func (p *PublicApi) tokenNext(c *gin.Context, user *app2.User) {
//	j := &utils.AppJwt{SigningKey: []byte(global.GVA_CONFIG.AppJwt.SigningKey)}
//	...accessToken / refreshToken...
//	response.OkWithDetailed(response.AppLoginResponse{ ... })
```

⇒ **本仓确无"签发 app token"的路由** ⇒ 即便挂上 `AppJWTAuth` 也**无合法 token 可用**（这正是 `config/jwt.go:18` 的理由）。

### 1.3 实际挂载的中间件（**实读 `initialize/router.go`**）

| 中间件 | 挂载处 | 作用域 |
|---|---|---|
| `Cors()` | `router.go:51` | 全局 |
| `ServiceTokenAuth()` | `router.go:64` | 归集回传桥（`AppAuthGroup`） |
| `JWTAuth()` ＋ `CasbinHandler()` | `router.go:125` | `PrivateGroup`（管理台） |
| `OperationRecord()` | 各 `router/system/*.go`（实读 **75 处**） | 各 system 子路由组 |

引擎＝`gin.Default()`（`router.go:37`）⇒ 自带 gin 的 `Logger()` / `Recovery()`。

**同批"定义但未挂载"的还有**（实读计数，非注释、非定义）：`CorsByRules`（`:52` 注释）· `LoadTls`（`:48` 注释）· `DefaultLimit` · `GinRecovery` · `DefaultLogger` · `NeedInit`。
★ **本件只主张 `AppJWTAuth` 一件**（其余各自成因不同，另案）。

---

## 二 · 结论

★★ **`AppJWTAuth` 是死代码** —— 无任何挂载点 ⇒ **从不执行**；且其依赖 `utils.NewAppJWT()`（`utils/app_jwt.go:24`）
**只被 `app_jwt.go:15` 调用**（实读：`grep -rn "NewAppJWT" 01-backend-go --include=*.go` ⇒ 仅 2 处命中：定义 + 上述调用）
⇒ **一并死**。

---

## 三 · 删/留建议

### 方案 A ★ 推荐：**删中间件 + 删其专用 utils，但保留 `config.AppJWT` 的 `ServiceToken`**

理由（**关键**：`config.AppJWT` **不是**整块死配置）：

```go
// middleware/service_token.go:24  ← 【活的】挂载在 router.go:64
want := global.GVA_CONFIG.AppJwt.ServiceToken      // ★ ServiceToken 字段在用
```

- ✅ 删：`middleware/app_jwt.go` 全文 ＋ `utils/app_jwt.go` 的 `NewAppJWT/CreateToken/…`（死链闭合）；
- ⚠️ **必留**：`config.AppJWT.ServiceToken`（`service_token.go` 读它）；
- ⚠️ **需一并处理**：`middleware/service_token.go` 的 3 处注释**指向 `AppJWTAuth`** ⇒ 删后注释会指向不存在的符号，**须同步改写**（否则留下"注释引用死符号"）。
- ⚠️ **`api/v1/app/public.go:54` 的注释块**已是注释，**无需动**（但可作为"曾经计划"的证据保留）。

### 方案 B：**留**（若路线图上确有 App 端 JWT 计划）

`config/jwt.go:18`（"tokenNext 已注释"）暗示**曾计划**。若保留：
- 至少加**死代码标记注释**（"当前未挂载，无签发路由"）；
- 并**建一条"未挂载中间件"登记判据**（扩 `AD-04` 族）—— 否则死代码会**再次**因"看不出没人用"而累积。

### ★ 本件边界

删/留**都超本线 `allowed_paths`**（改产品码须**立卡 + Owner 口径**）⇒ 本件**只出建议**，**不落码**。

---

## 四 · 未能验证（**如实声明**）

1. **未做"改坏它必须红"的负控** —— 它**没挂载**，改它**不影响任何路由** ⇒ **无判据可红**（这是本件的性质，不是遗漏）；
2. **未查部署期配置**：本仓**无 `config.yaml`**（实读：`find . -maxdepth 4 -name config.yaml` 在仓内 **0 命中**；`core/server.go` 注释亦称该文件"在产物外，见 DEPLOY.md §2.4"）⇒ **无法**核实 `app-jwt.service-token` / `app-jwt.signing-key` 是否仍配 ⇒ 「删配置项的连带影响」**未查**；
3. **`tokenNext` 是否"曾经可用"** 未考据（只读到"现在被注释"）；
4. **未扫前端/其它语言**是否读取 app JWT 相关端点（实读 `03-web-admin` 等 grep **未做**，本件只扫了 Go 侧）。
