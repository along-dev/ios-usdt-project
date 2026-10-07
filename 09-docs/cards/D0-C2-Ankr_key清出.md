---
id: D0-C2
mode: 实施
wave: P0
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  命中「凭据泄漏」类别 —— 该类别历史出过 P0（P0-2 生产 root 口令）。
  但本项位于 *_test.go（不参与运行时数据流），影响面是 API 额度而非资金
  ⇒ 定 P1/R2（不上 R3）。
  门禁强度自知：须有【全仓 grep 归零】+【脱敏模式集扩展】两条断言，
  不得只看"改了这两个文件"。
  来源: 完整版本开发方案_终版 §0.2（本轮复测命中 8）+ §七 卡表
base:
  - path: 01-backend-go\blockchain\erc_test.go
    sha256: 87d0e4b1a422cd158bf3fe4578d2b38b313a6985cc5bbbe2fdeb1ebfc4bb550a
    bytes: 9958
    eol: LF
  - path: 01-backend-go\blockchain\trc_test.go
    sha256: 219f33d6372ff216d6a4e31e80be1df1f7e39010ca3196b21aa9283c339dc652
    bytes: 11305
    eol: LF
allowed_paths:
  - 01-backend-go\blockchain\erc_test.go
  - 01-backend-go\blockchain\trc_test.go
  - E:\ios漏洞\_integration\_fix_work\verify_d0c2_ankr_key.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "01-backend-go\\blockchain\\scan.go 等非测试文件（本卡只动测试）"
  - "E:\\潜客\\**、E:\\ios漏洞\\ios15-17版本漏洞\\**、E:\\IOSusdt\\**（只读素材）"
  - "E:\\ios漏洞\\_integration\\build_unified.ps1（单一写者 = W1-C1）"
  - "_manifest.sha256（全部卡完成后单独重算，属停靠点）"
verify:
  - python _fix_work\verify_d0c2_ankr_key.py    # ①动前：须【红】，退出码 != 0
  - python _fix_work\verify_d0c2_ankr_key.py    # ②动后：须【绿】，退出码 0
  - go build ./...                              # 退出码 0
  - go test ./blockchain/ -run TestBtcDeriveMatchesBIP84Vector   # 退出码 0
packages: {}
---

# D0-C2 [R2] 硬编码 Ankr API key ×8 清出 + 脱敏模式集扩展

## 目标

把 `01-backend-go/blockchain/` 两个测试文件里的 **8 处硬编码 Ankr API key** 清出产物，
改为**从环境变量读取**（未设置则 `t.Skip`），并**扩展脱敏模式集**覆盖 API key 类。

## ★ 缺陷事实（本轮实测，**8 处**，两种形态）

| 文件 | 行号 | 形态 |
|---|---|---|
| `01-backend-go\blockchain\erc_test.go` | `41`、`60`、`132`、`189`、`263` | 标准 `rpc.ankr.com/<chain>/<key>` |
| `01-backend-go\blockchain\trc_test.go` | `276`、`302`、`356` | **`premium-http`** 形态 |

**复核命令（★ 必须用宽模式，两种形态都要覆盖）**：

```powershell
cd E:\USDT项目
Get-ChildItem -Recurse -File | Where-Object {$_.FullName -notmatch '\\node_modules\\|\\\.git\\'} |
  Select-String -Pattern 'rpc\.ankr\.com/[^"''\s]*[0-9a-f]{32,}' | Select-Object Path, LineNumber
# 预期 8 命中
```

★ **只用标准形态会漏掉 trc 的 3 处**（实测教训）。

**为何逃过此前所有脱敏轮次**：
- 该 key **不在** `_secrethunt` 的 208 条资产集内；
- 既有脱敏模式集覆盖**口令 / JWT / 私钥 / 助记词**，**API key 类未覆盖**；
- `D4` 报告本就写明「**资产集 ≠ 密钥全集**」—— 这是该局限的又一次实例化。

**扩展扫描结果（本轮实测）**：Tatum / Infura / Alchemy / QuickNode / GetBlock / BlockPI / NodeReal / Moralis
**全部 0 命中** ⇒ 方案称"未发现其他 key"**成立**。

## ★★ 保密纪律（P-4：本卡最易犯错处）

- **不得**把 key 明文写进任何 `.md` / 卡 / 台账 / 判据脚本；
- 本卡文档只写**行号与形态**，**不写值**；
- 判据脚本用**正则匹配形态**，**不硬编码 key 值**。

## 规格

### (a) 改为读环境变量

```go
func ankrRPC(chain string) string {
    key := os.Getenv("ANKR_API_KEY")
    if key == "" {
        return ""            // 调用方据此 t.Skip
    }
    return "https://rpc.ankr.com/" + chain + "/" + key
}
```

★ **形态差异须分别处理**：`premium-http` 形态的 URL 前缀不同（`/premium-http/<chain>/<key>`），
执行者**须实读那 3 行确认前缀**，**不得凭本卡描述猜测**。

### (b) 未设置环境变量时必须 `t.Skip`

```go
if rpc == "" {
    t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
}
```
★ **不得**用"跳过"冒充"通过"（P-13：无法验证时用 SKIP，不得判 PASS）。

### (c) 不得改变测试的**语义**

- 断言内容、测试向量、期望值**不动**；
- 只把**硬编码 URL** 换成**从环境变量构造**。

### (d) ★ 扩展脱敏模式集

在既有脱敏管线中增加 **API key 类模式**（至少覆盖 `rpc.ankr.com/<chain>/<32+hex>` 与 `premium-http` 变体）。

★ **单一写者约束**：脱敏脚本 `E:\ios漏洞\_integration\build_unified.ps1` 的
**单一写者是 W1-C1** ⇒ 若需改它，**须由同一写者承接**，或**另立卡**。
**本卡默认不动该脚本**；若要动 ⇒ **停下升级**（停靠点）。

## ★ 判据先于实现（判据 9）

`verify_d0c2_ankr_key.py`：

| # | 断言 | 红态 |
|---|---|---|
| A1 | 全仓宽模式 grep 命中 **0** | 8 ⇒ **红** |
| A2 | `erc_test.go` / `trc_test.go` 均含 `os.Getenv("ANKR_API_KEY")` | 缺 ⇒ 红 |
| A3 | 两个文件均含 `t.Skip` 调用 | 缺 ⇒ 红 |
| A4 | **扩展扫描**：8 家其他 RPC 服务商仍 0 命中（防改坏） | 绿（防改过头） |
| A5 | 判据脚本自身**不含** key 明文（P-4 自指防护） | 应绿 |

★ **量尺前置断言**：先用**已知必中**的模式（如 `rpc.ankr.com` 总命中 14）证明 grep 有效；
命中为 0 时**先怀疑模式坏了**。

## 不在范围

- 不改 `scan.go` 等非测试文件
- 不改 `build_unified.ps1`（停靠点）
- 不改 `_manifest.sha256`
- 不处理 `trc_test.go:367` 的 `go vet` 告警（属另一议题，见下）

## 证据要求

- `verify_d0c2_ankr_key.py` 改前红 / 改后绿两次真实退出码
- **改动前后各文件 sha256**
- **全仓宽模式 grep 改后 = 0** 的原始输出
- `go build ./...` 与 `go test` 的真实退出码
- ★ **明确声明**：本卡**未**改脱敏管线（若未改），并登记该缺口

## 停靠点

1. 若需改 `build_unified.ps1` 才能持久防复发 ⇒ **停下升级**（单一写者 W1-C1）
2. 若发现除 Ankr 外还有其他形式的 key（如 base64 编码）⇒ 登记上报
3. 若 `premium-http` 形态的语义无法确认 ⇒ **停下升级**，不得猜

## 附：本卡发现的关联项（登记，不在范围）

- `blockchain\trc_test.go:367:8` 有 `go vet` 告警：`using res before checking for errors`
  ⇒ 属**代码风格/正确性**问题，**与 key 泄漏同文件但不同性质** ⇒ 登记，另议（对应 R2-C4）。
