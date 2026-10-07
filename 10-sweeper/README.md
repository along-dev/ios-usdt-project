# wallet-sweeper · 本地钱包多链余额测绘与归集

从本地助记词 / 私钥批量派生出多链地址，查询主流币余额，并归集到你指定的目标地址。

**scan（只读测绘）与 sweep（归集）是两个完全独立的命令**，可以只做前者。

---

## 一、支持范围

| 链 | 地址类型 | 查询资产 | 归集 |
|---|---|---|---|
| Ethereum | 0x | ETH / USDT / USDC / DAI | ✅ |
| BSC | 0x | BNB / USDT / USDC / BUSD | ✅ |
| Polygon | 0x | POL / USDT / USDC | ✅ |
| Arbitrum | 0x | ETH / USDT / USDC | ✅ |
| Base | 0x | ETH / USDC | ✅ |
| Optimism | 0x | ETH / USDT / USDC | ✅ |
| TRON | T... | TRX / TRC20-USDT | ✅ |
| Bitcoin | P2PKH / P2SH-P2WPKH / P2WPKH | BTC | ✅ |
| Solana | Base58 | SOL / SPL USDT / USDC | ✅ |

派生路径遵循 BIP44 标准：

```
EVM     m/44'/60'/{account}'/0/{index}
TRON    m/44'/195'/{account}'/0/{index}
BTC     m/44'/0'/{account}'/0/{index}
SOL     m/44'/501'/{index}'/0'
```

---

## 二、输入方式（三种都支持）

```bash
# 1) 递归扫描目录（自动识别文本/JSON 中的助记词与私钥）
python -m wsweep scan --scan-dir D:\wallets --scan-dir E:\backup

# 2) 指定文件
python -m wsweep scan --file D:\keys.txt --file D:\data\wallet.json

# 3) 命令行直接传入
python -m wsweep scan --mnemonic "abandon abandon ... about"
python -m wsweep scan --privkey 0x4c0883a69102937d...
```

识别规则（宁少勿错，每条都记录来源文件与行号）：

- **助记词**：12/15/18/21/24 词，必须通过 BIP39 校验和，且 ≥90% 单词命中官方词表
- **私钥**：覆盖 11 种写法变体（见下节），全部还原为统一的 64 位小写 hex
- **JSON**：按字段名关键词识别 `mnemonic` / `private_key` / `secretKey` 等，支持嵌套

---

## 二·补、私钥变体识别与还原

同一个私钥在真实文件里会以各种形态出现。工具会**全部搜出来**，并**还原成统一的规范形式**存储。

### 支持的变体（11 种）

| 类别 | 示例 |
|---|---|
| 0x + 64hex | `0x4c0883a6…2318` |
| 裸 64hex | `4c0883a6…2318` |
| 大写 HEX | `4C0883A6…2318` |
| 0X 前缀大写 | `0X4C0883A6…2318` |
| 分组·空格 | `4c08 83a6 9102 … 2318` |
| 分组·连字符（4位） | `4c0883a6-9102937d-…-3f362318` |
| 分组·8位 | `4c0883a6-9102937d-…` |
| 冒号分隔 | `4c:08:83:a6:…:23:18` |
| TRON 0x41 前缀 | `0x414c0883a6…2318` |
| WIF（主网压缩/非压缩） | `KymWWYtz…` / `5JPmkQ5y…` |
| WIF 测试网 / base64 | `cQ8VyTtq…` / `TAiDppEC…` |
| 补零/截断 | `0x0000…4c0883…`、`0x4c0883…`（省略前导零） |

### 还原存储结构

`scan_report.json` 中的 `variant_store` 以**规范私钥**为主键：

```json
{
  "4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318": {
    "fingerprint": "a08d67bdf1e0",
    "variant_count": 10,
    "forms": ["0x 前缀", "TRON 0x41 前缀写法", "WIF 主网·压缩", "裸 hex"],
    "sources": [
      { "source": "E:\\path\\keys.txt", "line": 6, "origin": "0x4c0883a69102937d…" },
      { "source": "E:\\path\\wif.txt", "line": 12, "origin": "KymWWYtz6iLgVAzx…" }
    ],
    "canonical": {
      "hex": "4c0883a6…2318",
      "hex_0x": "0x4c0883a6…2318",
      "hex_upper": "4C0883A6…2318",
      "wif_compressed": "KymWWYtz…",
      "wif_uncompressed": "5JPmkQ5y…",
      "wif_testnet_compressed": "cQ8VyTtq…",
      "tron": "414c0883a6…2318",
      "base64": "TAiDppEC…"
    }
  }
}
```

要点：

- **去重合并**：同一私钥的 10 处不同写法 → 只保留 1 条账户记录，不会重复查询余额
- **来源可追溯**：每处变体的文件路径、行号、原始字符串都完整保留
- **一键还原**：`canonical` 字段给出该私钥所有等价写法，需要哪种格式直接取用
- **安全引用**：`fingerprint`（sha256 前 12 位）可用于日志中标识私钥而不泄露内容

---

## 三、使用流程

### 第 1 步：扫描（只读，不涉及任何签名广播）

```bash
python -m wsweep scan \
  --scan-dir D:\wallets \
  --chains evm,tron,btc,sol \
  --account-count 5 \
  -o scan_report.json
```

输出内容：

- 命中的助记词/私钥清单（含来源与行号）
- **变体还原汇总**：哪些私钥存在多种写法、各来自哪个文件哪一行
- 每个派生地址在各链上的非零余额
- `scan_report.json`：完整结果 + `variant_store` + 账户私钥（供 sweep 衔接）

常用参数：

| 参数 | 说明 |
|---|---|
| `--account-count N` | 每条助记词派生 N 个地址（默认 5） |
| `--chains` | 限定链，如 `evm,tron` |
| `--keyword REGEX` | 文件名过滤正则，缩小扫描范围 |
| `--exts txt,json` | 限定扩展名 |
| `--passphrase` | BIP39 第 25 个词 |
| `--workers N` | 并发线程数（默认 6） |

### 第 2 步：归集 dry-run（仅签名，**不广播**）

**四个目标地址各自独立、均为可选 —— 填哪个链的地址，就只归集哪个链。**

```bash
python -m wsweep sweep \
  --from-report scan_report.json \
  --to 0x你的EVM目标地址 \
  --target-tron T你的TRON地址 \
  --target-btc bc1q你的BTC地址 \
  --target-sol 你的SOL地址
```

| 参数 | 对应链 | 地址格式 |
|---|---|---|
| `--to` | EVM 系 6 条链（ETH/BSC/Polygon/Arbitrum/Base/OP） | `0x` + 40hex |
| `--target-tron` | TRON | `T` 开头，34 字符 |
| `--target-btc` | Bitcoin | `bc1…` / `1…` / `3…` |
| `--target-sol` | Solana | Base58，32–44 字符 |

只填其中一两个即可，未提供目标地址的链会**自动跳过**并在输出中说明：

```bash
# 只归集 TRON 和 SOL
python -m wsweep sweep --from-report scan_report.json \
  --target-tron T你的地址 --target-sol 你的SOL地址
# 输出: [目标] 未提供目标地址，跳过: evm,btc
```

一个都不填会直接报错退出，不会执行任何操作。

默认只处理 `scan` 时检测到有余额的账户（`--all` 可关闭）。输出每笔转账的链、币种、金额、来源、目标与交易哈希，**但不会发送到网络**。

### 第 3 步：确认无误后真正广播

```bash
python -m wsweep sweep \
  --from-report scan_report.json \
  --to 0x你的EVM目标地址 \
  --target-tron T你的TRON地址 \
  --broadcast
```

`--broadcast` 会先显示警告并留 5 秒供你 Ctrl+C 中止。

---

## 三·补、★ 操作规程：广播前的前置条件（**必须遵守**）

> **依据**：`09-docs/cards/V0-本轮裁决留痕.md` 的裁决 **D-2**
> （``10-sweeper`` 保持离线，**不接入主系统互斥**）。

### 为什么需要这条规程

本模块是**离线命令行工具**，与主系统的另两条归集路径**不存在技术互斥**：

| 路径 | 触发方式 | 互斥机制 |
|---|---|---|
| gasleak 自动归集 | PM2 定时任务 | `collect-lock` 原子占位 |
| 潜客 `Sk()` | Go 侧接口 | 同上 |
| **`10-sweeper --broadcast`** | **人工执行** | ★ **无** |

`D-2` 已裁决**不给本模块加互斥代码**（否则会把一个离线工具变成必须联网的工具）。
⇒ **重复归集的防护完全依赖本节的人工规程。**

### ★ 广播前必须确认的三件事

执行 `--broadcast` **之前**，**必须**逐条确认：

1. 目标地址**不在** gasleak 的自动归集队列中
   —— 即 `DerivedAddress.collectStatus != 'collecting'`；
2. 目标地址**不在**潜客 `Sk()` 的执行中
   —— 即 `wallet.progress != 1`；
3. **若无法确认 ⇒ 不得广播。**

> ★ 这是 `D-2` 的**代价兜底**：既然不做技术互斥，就必须把规程写死、由**人工**执行。

---

## 三·补二、★ 残余风险显式登记

> **本模块与另两条归集路径不存在技术互斥。**
>
> 重复归集的防护**完全依赖**上述操作规程（三·补）的**人工**确认。
> 系统层面**没有**任何技术手段能阻止 `--broadcast` 与另两条路径并行。

### 触发复审条件

**若本模块被改为自动 / 高频调用** ⇒ **`D-2` 裁决失效，必须重新裁决。**
（`D-2` 的成立前提是「本工具为低频、人工调用的离线工具」。）

### 相关实测

- 本模块全目录 grep `collect-lock|collect-release|acquireLock` → **零命中**
  （即确认无任何互斥耦合，非推断）。
- `--broadcast` 会**真广播**（`--broadcast` 之外一律 dry-run，只签名不发送）。

> ★ 不得让"没有互斥"看起来像"有互斥"——若将来有人在本模块加入了互斥调用，
> 必须同时更新本节与 `D-2` 的复审结论。

---

## 四、控制权与 gas 检测

**余额非零 ≠ 能拿走。** scan 阶段会对每个账户检查两件事：

### A. gas 够不够（能否支付归集手续费）

| 链 | 手续费来源 | 判定阈值 |
|---|---|---|
| EVM | 该链原生币（ETH/BNB/POL…） | `65000 gas × gasPrice` |
| TRON | TRX | ≥ 30 TRX（TRC20 能量费） |
| BTC | UTXO 总额 | 能覆盖 `估算vsize × 费率` |
| Solana | SOL | > 0.000895 SOL（手续费+租金） |

### B. 我们说了算吗（多签 / 权限转移）

| 链 | 检测项 | 方法 |
|---|---|---|
| EVM | 合约账户 | `eth_getCode` 非空 → 私钥无法直接转账 |
| EVM | **EIP-7702 委托** | 代码为 `0xef0100‖地址` → 执行被委托给该合约，**高危** |
| EVM | 多签钱包 | 调用 Safe 的 `getThreshold()`（`0xe75235b8`） |
| TRON | **权限转移** | `owner_permission` 的首个 key ≠ 本地址 |
| TRON | 多签 | owner/active permission 的 keys>1 或 threshold>1 |
| BTC | 多签地址 | `3` 开头（P2SH，可能是多签） |
| Solana | 被程序托管 | 账户 owner ≠ System Program |

### 实测案例

本项目测试中就抓到两种真实风险：

```
! TRON 权限已转移  TUEZSdKsoDHQMeZwihtd…
  owner_permission 已转移至 TUmdykWXNWHbRk3V4wFGKGHKMdh6jHzijm（私钥无法控制）

! EVM(eth) EIP-7702 委托  0x9858effd232b4033e4…
  ⚠ EIP-7702 委托账户：代码执行被委托给 0x8a67b5020ee254ef48e3b6a04927f39baf7e408a。
    私钥可签名，但交易会经该合约执行，存在资金被控制风险
```

两者都是"余额看起来有、私钥也在手，但实际转不走"的典型形态。

用 `--no-control` 可跳过该检测（会快很多）。

---

## 四·补、密钥库（vault）

scan 结束后自动把提取到的密钥汇总到 `vault/`：

```
vault/
  keys.json        含明文私钥 + 变体还原存储
  addresses.csv    地址清单（不含私钥，含余额/gas/风险标记，带 BOM 便于 Excel 打开）
```

`keys.json` 结构：

```json
{
  "note": "本文件含明文私钥，请妥善保存并及时删除",
  "account_count": 12,
  "variant_store": { "<64hex>": { "variant_count": 3, "sources": [...] } },
  "keys": [ { "source": "...", "evm_address": "0x...", "evm_privkey": "...", ... } ]
}
```

用 `--vault DIR` 可改输出目录。

---

## 五、安全设计

- **默认 dry-run**：不加 `--broadcast` 绝不广播任何交易，只做签名与校验
- **两命令分离**：scan 可在不产生任何签名的情况下独立使用
- **目标地址独立**：四条链的目标各自可选，未填的链不参与，避免地址格式串用导致失败
- **控制权前置检测**：归集前先确认权限未被转移、gas 充足，避免无效广播
- **EVM 归集顺序**：先转 ERC20，最后转原生币，避免 gas 被先转走
- **gas 保护**：每笔转账前检查 native 是否足够支付 gas，不足则跳过并说明原因
- **保留金**：`--leave-native` 控制每条 EVM 链保留的 native 数量（默认按链设定）
- **TRC20 保护**：TRX 不足 30 时会拒绝 TRC20 归集，防止代币卡死
- **目标校验**：启用某条链但目标地址格式不符时直接报错退出

---

## 五、依赖

**全部功能无需额外安装**，只依赖环境中已有的包：

```
eth-account  coincurve  pycryptodome  base58  pynacl  protobuf
```

四条链的归集**全部为内置实现**，不依赖任何行业 SDK：

| 链 | 实现方式 | 不依赖 |
|---|---|---|
| EVM | eth-account 签名 + 自序列化 | — |
| TRON | 手写 protobuf 编码 + coincurve ECDSA | 不需要 `tronpy` |
| BTC | 自实现 BIP143 segwit 签名 | 不需要 `bitcoinlib` |
| Solana | 自实现 legacy 交易序列化 + nacl ed25519 | **不需要 `solders` / `solana-py` / `spl-token`** |

Solana 的交易构造（header / 账户表排序 / 指令编译 / compact-u16 编码）
全部按 [官方交易结构文档](https://solana.com/docs/core/transactions/transaction-structure) 手写实现。

---

## 六、模块结构

```
wsweep/
  derive.py    BIP39/BIP32 派生；EVM/TRON/BTC/SOL 地址生成（纯 Python + bech32）
  privkey.py   私钥变体识别 + 规范化还原（11 种写法 <-> 统一 hex）
  control.py   多签 / 权限转移 / EIP-7702 委托 / gas 可行性检测
  loader.py    目录递归扫描 / 文件 / 命令行 三种输入；正则 + JSON 结构化提取
  chains.py    多链 RPC 余额查询（批量 JSON-RPC + 并发 + 重试）
  tron_tx.py   TRON protobuf 交易构造与 ECDSA 签名（不依赖 tronpy）
  btc_tx.py    BTC 交易构造与 BIP143 签名
  sol_tx.py    Solana legacy 交易构造与 ed25519 签名（不依赖 solders）
  sweep.py     归集编排：EVM / TRON / BTC / SOL
  cli.py       scan / sweep / generate 命令
```

---

## 七、已验证项

以下密码学路径均已**独立验证**（非仅"能跑"）：

- **助记词派生**：`abandon...about` → EVM `0x9858EfFD...`、TRON `TUEZSdKso...`、BTC P2WPKH `bc1qmxrw6q...`、SOL `4nFZgXtZ...`，与公开测试向量一致
- **EVM 签名**：签名后从 raw 交易恢复出的发送者 == 派生地址
- **TRON 签名**：`txID == sha256(raw_data)`；签名可恢复出完全相同的公钥与地址
- **BTC 签名**：手工解析 raw 交易逐字段正确；独立重算 BIP143 sighash 后签名验证通过
- **Solana**：ed25519 密钥对独立重算一致
- **Solana 交易**：自实现的序列化经**链上 simulateTransaction 实测** ——
  账户排序、header 计数、指令编译全部通过链上 sanitize，错误推进至
  `SignatureFailure`（证明结构校验已全部通过）
- **ATA 推导**：与链上 `getTokenAccountsByOwner` 返回的真实 ATA 一致
- **控制权检测**：TRON 权限转移、EIP-7702 委托均在真实链上数据上验证命中
- **余额查询**：9 条链全部实测返回真实数据
- **私钥变体**：单值回归 10/10 通过；端到端把同一私钥的 **10 处不同写法**正确合并为 1 条规范记录并保留全部来源

---

## 八、清理

使用完毕后建议删除 `scan_report.json` 与 `sweep_*.json` —— 它们包含明文私钥。

```powershell
Remove-Item scan_report.json, sweep_dryrun.json, sweep_result.json -ErrorAction SilentlyContinue
```
