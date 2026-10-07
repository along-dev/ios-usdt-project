# T33 —— `TrxPrivateKeyByMnemonic` **吞掉密钥派生错误** ⇒ 失败即 `nil` 解引用（**只立卡，不落码**）

> **卡**：T33 ｜ **档建议**：**R3**（**密钥路径** —— 命中真高危路径清单；须 Owner 单独授权）
> **线**：待派 ｜ **依据**：总调度 ⌛2026-10-04 取证复核（登记于 `T31` §7.4）；由 T32 取证 agent 报出、总调度**复读原文核实**
> **★ 状态**：**只立卡、未落码** —— ★ **⌛2026-10-04 Owner 已授权**；**排队待派**（T32→T33→T34→T35 **串行**：四卡共用同一 `_i2c1_server.exe` 构建产物，P-18/P-38）
> **日期**：2026-10-04

---

## 一 · 现状（**已核实**，⌛2026-10-04 总调度读码复核）

`01-backend-go/blockchain/trx.go:172-176`：

```go
// trx 通过助记词生成私钥有地址
func TrxPrivateKeyByMnemonic(phrase string) string {
	private, _ := FromMnemonicSeedAndPassphrase(phrase, "", 0)   // ← 错误被吞
	return private.ToECDSA().D.Text(16)                          // ← private 为 nil 即 panic
}
```

且 `FromMnemonicSeedAndPassphrase` **内部亦吞一次**：`private, _ := hd.DerivePrivateKeyForPath(...)`（同文件）。

**后果**：助记词/派生链任一环节失败 ⇒ 错误**不可见** ⇒ 表现为 nil 解引用 panic，**或**（更坏）静默产出**空/错私钥**。**这是密钥材料路径。**

**★★ 实测更正（⌛2026-10-04T13:00，执行者实跑，**推翻了本卡原文的"panic"说法**）**：
对**坏助记词**（`"not a mnemonic"`）实测**原始代码**（改前）的行为是 —— **不 panic**：`bip39.NewSeed` **不做校验**，且**固定派生路径不会触发 `DerivePrivateKeyForPath` 出错** ⇒ 得到 **`err=nil` ＋ 一个 64 字符的「伪造私钥」**。
⇒ **真正的失败模式是「静默产出一个错误的私钥」，不是 panic。** 这**比 panic 严重**：panic 会立刻暴露，而静默错钥会**被写进 `wallet.TrxPrivateKey` 并当真钥使用** ⇒ 该钱包的 trx 地址**私钥不可达**（＝资金不可达）。
⇒ 本卡的修法因此**增加了前置校验**（`bip39.IsMnemonicValid`），把这类输入**变成响亮 error**。
★ **实测读数不在本卡内**（审核 B 的 F1 指出：原写「见 §四 V1/V3 的实测读数」是**悬空引用**，§四 只有断言表、没有读数）—— 读数的落点是：执行者 `/tmp` 临时用例（**已删**）＋ 调度方复跑的 `_fix_work` 输出；**本卡不承载读数**。⇒ 该悬空引用已删。

★ **不重叠核查**：全仓 `.TransferHash =` 仅 4 处（`eth.go:98/164`、`trx.go:82/119`），均不在本卡涉及面内；本卡与 T34 无交集。

## 二 · 目标

**密钥派生失败必须<ins>响亮</ins>** —— 不得吞错；失败即返回**明确 error**（带上下文：哪条链、哪一步、哪一段路径），⛔ **不得让 `nil` 往下走**。

## 三 · 范围

| 项 | 内容 |
|---|---|
| **改** | `01-backend-go/blockchain/trx.go` 的 `TrxPrivateKeyByMnemonic` ＋ `FromMnemonicSeedAndPassphrase`（改为返回 `(key, pk, error)`，或至少 fail-fast） |
| **★ 改（须一并 —— ⌛2026-10-04 总调度实读全仓得出的调用方）** | 加 `error` 返回 ⇒ **以下两处必须同步改，否则编译不过**：<br>① `01-backend-go/service/app/public.go:111` `wallet.TrxPrivateKey = blockchain.TrxPrivateKeyByMnemonic(reqWallet.Phrase)`<br>② `01-backend-go/blockchain/trc_test.go:380` `private := TrxPrivateKeyByMnemonic(testMnemonic(t))`<br>⇒ ★ **本卡 `allowed_paths` ＝ 这三个文件**（原卡只写 trx.go，**不够**，已更正） |
| ★ **门禁（P-16）** | ② 是**测试文件** ⇒ `go build ./...` **不编译 `_test.go`** ⇒ 本卡的编译门**必须用 `go test`**（至少 `go test ./blockchain/`），⛔ 不得只跑 `go build` |
| ⛔ **不得** | 改**派生路径参数**（`44'/195'/0'/0/%d` 等一律不碰）—— **改派生参数＝改钱包地址＝灾难** |
| ⛔ **不得** | 顺手改 `eth.go` 的对应实现；若确需同步改调用方，**须在本卡逐条列出**后才动 |

## 四 · 验收

| # | 断言 |
|---|---|
| **V1** | 传**坏助记词**（如 `"not a mnemonic"`）⇒ **返回明确 error**（⛔ 非 panic、⛔ 非空串私钥） |
| **V2** | ★★ 传**好助记词** ⇒ 产出的地址/私钥与**改前逐位一致** —— **这是本卡最重要的一条**：它证明"没碰派生参数" |
| **V3** | **变异**：把错误处理改回 `_` ⇒ V1 **必红** |

## 五 · 边界

- ⛔ **不在本批**；只立卡、不落码。★ **不阻塞 T31/T32**。
- ★ 与 T32 / T34 / T35 **同族**（**静默失败**）。

## 六 · 停靠点

1. ★★ **密钥路径** ⇒ **停下，等 Owner 单独授权**
2. ★★ 若发现**现存库里已有用坏派生算出的地址/私钥** ⇒ 立即停下升级 —— 那是**资金不可达**，不是代码缺陷，处置方式完全不同

---

> **落款时刻（照抄 `date` 输出，非手写）**：`2026-10-04T00:44:54+0800`
