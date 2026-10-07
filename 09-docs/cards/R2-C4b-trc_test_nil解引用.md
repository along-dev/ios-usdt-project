---
id: R2-C4b
mode: 实施
wave: P0-收口
depends: [R2-C4]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R1
定档理由: |
  改 `01-backend-go/blockchain/trc_test.go` —— **测试文件**，不参与运行时数据流，
  且不触资金路径 ⇒ **R1**（非 R2/R3）。
  门禁强度自知：须有【go vet 该条消失】+【go test 仍可编译】两条断言；
  ★ 且**不得改变既有测试语义**（只加 err 检查）。
来源: 全量审核报告_更新后 §七 #1（我复核后确认：R2-C4 是【有意保留】该条，非遗漏）
      + L033 台账 §1（`verify_r2c4_govet.py:159` 明写"卡外，有意保留"）
base:
  - path: 01-backend-go\blockchain\trc_test.go
    sha256: 274ce3867422d42582e6adf716c62684f2cd34a59e5c9a198b0fb666f4327373
    bytes: 11934
    eol: LF          # ★ 实测 CRLF=0 LF=413
allowed_paths:
  - 01-backend-go\blockchain\trc_test.go
  - E:\ios漏洞\_integration\_fix_work\verify_r2c4b_trc_nil.py   # 新建判据
forbidden_paths:
  - "01-backend-go\\blockchain\\scan.go、eth.go、trc.go 等【非测试】文件（本卡只动测试）"
  - "01-backend-go\\blockchain\\erc_test.go（无同类问题，见「不在范围」）"
  - "E:\\ios漏洞\\_integration\\_fix_work\\verify_r2c4_govet.py（★ 它断言该告警【仍在】⇒ 其 V2 须同步更新）"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - go vet ./blockchain/      # ①动前：须报 trc_test.go:386「using res before checking for errors」
  - go vet ./blockchain/      # ②动后：该条【消失】（其余告警数不变）
  - go test ./blockchain/ -run TestGetErrInfo   # 须可编译（未设 key 时应 t.Skip）
packages: {}
---

# R2-C4b [R1] `trc_test.go` 的 `res` nil 解引用

> ## ⚠️ 执行后勘误（2026 本轮，执行者实测反馈）
>
> **本卡 §(d) 有重大遗漏 —— 只提了改 `verify_r2c4_govet.py` 的 L159，漏了 V6。**
>
> | # | 卡文原文 | **实际** |
> |---|---|---|
> | 1 | §(d)「同步更新 `verify_r2c4_govet.py` 的 `L159` 断言」 | ❌ **漏了 V6** —— 该脚本 **V6 断言 `blockchain/**` 7 个文件 sha256 全未变**，**其中包含 `trc_test.go`** ⇒ **只改 L159 则 V6 必炸**（V6 才是先炸的那条） |
> | 2 | §(d) 未说明 V6 的处置 | 执行者按**最小必要原则**处置：**V6 中仅 `trc_test.go` 基线更新为改后值**，**其余 6 个文件仍断言逐字节不变** ⇒ **保住了 R2-C4「未改卡外文件」的结论** |
>
> **执行结果**：判据 **8/8 PASS**；`go vet ./blockchain/` **1 条 → 0 条**；`go test TestGetErrInfo` **SKIP → PASS**（EXIT=0）。
> `trc_test.go`：`11934B → 12076B`，**LF 保持**（CRLF=0）。
> 改后 sha256：`ab05302c5a44415b9fb0d46d591778cdf6e359d0472096156bcaf71d32912925`。
>
> **复核**（本会话独立跑）：`go vet`=EXIT 0、`go test`=SKIP/PASS、sha256/bytes/EOL **与自报逐位一致**、
> `blockchain/` 下**仅 `trc_test.go` 被改** ✅
>
> **★ 待 Owner 裁定**：V6 基线的更新属**卡外决策**（影响其他卡的判据链）。
> 执行者的处置（仅更新本卡显式修改的那 1 个文件、其余 6 个不变）**在工程上合理**，
> 但**「卡外基线能否随卡更新」应成文**（见 §停靠点 4）。

---

## 目标

消除 `go vet` 报的 **`using res before checking for errors`** ——
`err` 被丢弃后直接用 `res.Body`，**err 非 nil 时 `res` 为 nil ⇒ panic**。

## 缺陷事实（本轮实读，**逐行确认**）

`01-backend-go/blockchain/trc_test.go:378-395`：

```go
if ankrURL == "" {
    t.Skip("ANKR_API_KEY 未设置，跳过联网测试")   // :379
}
url := ankrURL + "/walletsolidity/gettransactioninfobyid"

payload := strings.NewReader("{\"value\":\"2a80c3...\"}")

req, _ := http.NewRequest("POST", url, payload)   // :385 ← err 亦被丢弃

req.Header.Add("accept", "application/json")
req.Header.Add("content-type", "application/json")

res, _ := http.DefaultClient.Do(req)              // :390 ← ★ err 被丢弃

defer res.Body.Close()                            // :392 ← ★ res 可能为 nil ⇒ PANIC
body, _ := io.ReadAll(res.Body)                   // :393
```

**`go vet` 实测输出**：
```
blockchain\trc_test.go:392:8: using res before checking for errors
```

★ **实测扫描**：`trc_test.go` / `erc_test.go` 中
「丢弃 err 后用 res」的模式 **仅此 1 处**（`erc_test.go` 无同类问题）。

## ★ 前置澄清：这不是"`R2-C4` 漏做"

**本卡的存在前提须写清楚，以免误判为"台账失实"**（**P-5** 变体）：

- `R2-C4` 处置的是 **4 条风格类告警**（`sys_captcha.go`、`sys_user.go`、`sys_initdb_*.go`）
- **`trc_test.go` 属"卡外文件"** ⇒ 按调度纪律**不得改**
- ⇒ `R2-C4` 卡的 **V2 明文要求「`trc_test.go:392` 告警仍在」**（`L033:47-48`）
- ⇒ **该条告警是【有意保留】的**，**不是遗漏**

**本卡 = 为这条"有意保留"的告警单独立范围**（因为它确实是真实风险，只是不属 R2-C4 的允许范围）。

## 规格

### (a) 检查 `Do` 的 err（**最小改动**）

```go
res, err := http.DefaultClient.Do(req)
if err != nil {
    t.Fatalf("request failed: %v", err)   // 或 t.Skip / t.Errorf，见 (c)
}
defer res.Body.Close()
```

### (b) 一并修 `http.NewRequest` 的 err（**同一函数内，同类问题**）

```go
req, err := http.NewRequest("POST", url, payload)   // :385 的 `_` 同样丢弃了 err
```
★ 虽 `go vet` 只报 `:392`，但 `:385` 的丢弃是**同一根因** ⇒ **本卡一并处理**（避免下次又开一卡）。

### (c) ★ 保持既有测试语义

该测试是**联网测试**，且**已在 `:379` 用 `t.Skip` 保护**（未设 `ANKR_API_KEY` 时跳过）。
⇒ **失败处理须与之一致**：
- 本卡**不得**把"网络失败"改成"测试失败"（那会让 CI 在无网环境红）
- **建议用 `t.Skipf`**（网络不可达时跳过），而非 `t.Fatalf`
- `http.NewRequest` 的 err 才用 `t.Fatalf`（**它失败说明代码/URL 有问题，不是环境**）

★ **两条错误的边界要分清**：
| 错误源 | 处理 |
|---|---|
| `http.NewRequest` 失败 | `t.Fatalf`（代码问题） |
| `http.DefaultClient.Do` 失败 | `t.Skipf`（环境/网络问题） |

### (d) ★ 同步更新 `verify_r2c4_govet.py`

★ **关键**：该判据 **`L159` 明文断言「`trc_test.go:392` 告警仍在（卡外，有意保留）」**
⇒ 本卡修好后，**那条断言会失败**。

**处置**（二选一，执行者说明理由）：
1. 把 `L159` 改为**"该告警已由 `R2-C4b` 消除"**（推荐）
2. 或把 `verify_r2c4_govet.py` 的该条**降级为"历史记录"**（不再断言）

★ **不得**为了"让判据过"而删掉整条断言 —— 那会丢失留痕。

## 判据（`verify_r2c4b_trc_nil.py`）

| # | 断言 | 动前 |
|---|---|---|
| R1 | `go vet ./blockchain/` 输出**不含** `trc_test.go` 的 `using res` | ❌ 红（当前有） |
| R2 | `trc_test.go` 中**不存在** `res, _ :=` 形式（`Do` 的 err 必被接收） | ❌ 红 |
| R3 | `trc_test.go` 中**不存在** `req, _ :=` 形式 | ❌ 红 |
| R4 | `go test ./blockchain/ -run TestGetErrInfo` **可编译** | ✅ 绿（防改坏） |
| R5 | 未设 `ANKR_API_KEY` 时**走 `t.Skip`**（不红） | ✅ 绿（防改过头） |
| R6 | `verify_r2c4_govet.py` 的对应断言**已同步更新** | ❌ 红 |

★ **R5 是防改过头用例**：本卡**不得**把"环境不可用"变成"测试失败"。

## 不在范围

- 不改**任何非测试**的 Go 文件
- 不改 `erc_test.go`（**实测无同类问题**）
- 不改其他测试函数
- **不动 `go vet` 的其他告警**（若发现新增 ⇒ 停下升级）

## 证据要求

- `go vet ./blockchain/` 改前（含该条）/ 改后（该条消失）的**真实输出**
- 改后 `go vet` 的**总条数**（应比改前少 1）
- `go test ./blockchain/ -run TestGetErrInfo` 的**真实退出码**（未设 key ⇒ 应为 ok，走 Skip）
- `trc_test.go` 改前/改后 sha256 + diff
- ★ `verify_r2c4_govet.py` 的**改动 diff**（说明如何同步 V2）
- ★ 明确声明：**未改动任何非测试文件**

## 停靠点

1. ★ **是否要把 `Do` 的失败改为 `t.Fatalf`** —— 若 Owner 希望"联网测试失败即红"
   （而非 Skip），则与本卡的推荐相反 ⇒ 停下确认
2. 若发现 `trc_test.go` 还有**其他被丢弃的 err**（本卡只列了 2 处）⇒ 登记上报
3. 若改后 `go vet` 出现**新增**告警 ⇒ 停下升级
4. ★ 若 `verify_r2c4_govet.py` 的修改会**影响其他卡的判据链** ⇒ 先确认依赖关系
