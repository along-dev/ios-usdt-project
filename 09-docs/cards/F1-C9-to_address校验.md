---
id: F1-C9
mode: 实施
wave: 2
depends: [F1-C8]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  本卡触碰 01-backend-go/service/app/collect_result.go —— 命中【真高危 → 命中即 R3】
  （bill 落账 / 分账口径）。缺陷性质为「声明的落账地址与服务端实际记账地址无任何比对」，
  属资金归属类缺陷：错误地址的归集会被静默记到不相关收款方名下。
  ★ 本卡由 I2-C1 的真 HTTP + 真 DB 数值断言【实测确认可利用】（非静态推断）。
  门禁强度自知：必须有【数值断言】—— 地址不符时 0 笔落账且 code != 0。
来源: 卡 I2-C1 执行期实测发现（停靠点 3：若 P1-5 越权/金额校验确实可利用 ⇒ 升级 Owner）
      + Owner 本轮裁决「裁(a)，先做 F1-C9」
base:
  - path: 01-backend-go\service\app\collect_result.go
    sha256: c636960add4c6f4ce753b1aaa93e6b0f5bcc7311a6ea776965204a563a056445
    bytes: 11958
    eol: LF
    note: 该值为 F1-C8 完成后的版本（F1-C9 的起点）
allowed_paths:
  - 01-backend-go\service\app\collect_result.go
  - E:\ios漏洞\_integration\_fix_work\verify_f1c9_toaddress_guard.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "01-backend-go\\model\\**（★ 本卡不改模型；ToAddress 字段已存在）"
  - "01-backend-go\\api\\v1\\app\\collect_result.go（handler 只记日志，不改）"
  - "01-backend-go\\blockchain\\scan.go（口径基准，只读）"
  - "07-db/**、02-backend-node/**、05-ios/**、06-android/**、03-web-admin/**、04-landing/**"
  - "_manifest_sha256（占位更正见下）"
verify:
  - python _fix_work\verify_f1c9_toaddress_guard.py    # ①动前：须【红】，退出码 != 0，留证
  - python _fix_work\verify_f1c9_toaddress_guard.py    # ②动后：须【绿】，退出码 0
  - go build ./...                                     # 退出码 0
  - go vet ./service/app/                              # 退出码 0
packages: {}
---

# F1-C9 [R3] `to_address` 与 settlement 不符时无校验 —— 错误地址静默记错账

## 目标

让归集回传携带的 `to_address`（声明的"实际落账地址"）**必须与所选 settlement 的 address 一致**；
不一致时**显式拒绝**（`code != 0`），**不产生任何 bill**。

## 缺陷事实（★ 由 I2-C1 真 HTTP + 真 DB 实测确认，非静态推断）

**复现（实测）**：

```
POST /app/collect-result
  X-Service-Token: <有效>
  {"chain":"tron","tx_hash":"i2c1-addr-mismatch","amount":"10",
   "wallet_id":1,"address":"TOTALLY_WRONG_ADDRESS","collected_at":...}

响应: HTTP 200  {"code":0,"data":{"billId":...,"duplicated":false},"msg":"ok"}
DB:   正常落 3 笔 bill（role 1/2/3）
```

**根因（静态确证）**：

| 位置 | 事实 |
|---|---|
| `model/common.go:145` | `ToAddress string \`json:"to_address"\` // 实际落账地址` —— **接口声明了该入参** |
| `api/v1/app/collect_result.go:37-39` | 收到后**只写进 Debug 日志** |
| **`service/app/collect_result.go`** | 全文 grep `ToAddress` → **零命中** ⇒ **服务层完全忽略它** |

⇒ `to_address` 是**声明式的"实际落账地址"**，却与真实的 `settlement.address` **无任何比对**。

**危害**：gasleak 若把资金转到了与账单不一致的地址（配置错误 / 被投毒 / 中间人篡改），
潜客侧仍会**按 settlement 的收款方正常记账** ⇒ **钱去了 A，账记在 B**，且 `code=0` 完全静默。

**注意**：本卡**只校验一致性**，不校验"谁有权收"（越权是另一议题，见 §不在范围）。

## 规格

### (a) 校验点放在何处的论证

三笔 bill 的 settlement 来源不同：
- role=1 平台 ← `systemSettlement`（`user_id = 0`）
- role=2 客户 ← `customSettlementId(tx, chain)`
- role=3 代理 ← `agentSettlement`（经 machine→agent→settlement）

⇒ **不能只比对一个**。`to_address` 应对应**该笔归集的真实收款方**：

| 钱包类型 | 唯一收款方 |
|---|---|
| 私域（`Region == 2`） | `privateSettlement`（`user_id = -1`）—— **单笔全额** |
| 公域（`Region != 2`） | 三笔分账，`to_address` 是**链上实际落账地址**，通常等于其中**某一方** |

★ **本卡的判定规则（按可判定性排序，写进证据）**：

1. **`to_address` 为空 ⇒ 不校验**（保持向后兼容：gasleak 可能未传该字段）；
2. **`to_address` 非空 ⇒ 必须与本次记账涉及的 settlement 地址集合之一相等**
   —— 私域：只含 `privateSettlement.address`；
   —— 公域：含 `systemSettlement.address`、客户 `settlement.address`、代理 `settlement.address`。
3. 不在集合中 ⇒ **显式拒绝**，并**明确列出期望地址集合**（便于排障，且不泄漏非必要信息——地址本身是链上公开值）。

★ **为何用"集合之一"而非"单一精确匹配"**：公域一次归集**只产生一笔链上转账**，
但记账要拆三笔；`to_address` 是那**一笔转账**的目标。
按 `scan.go` 的既有实现，公域是**分别**向三方转账（`scan.go:140+` 的 `switch token.Chain` 内多次 Transfer），
故 `to_address` 应落在三方之中。**执行者须实读 `scan.go` 确认这一点**，
若实读结论不同（例如公域只转给其中一方），**以实读为准并写进证据**。

### (b) 校验必须在 [落任何 bill] 之前

在 `Transaction` 内、`mkBill` 调用**之前**完成校验，确保**一笔都不落**。

### (c) 不得改动既有口径

- `mkBill` / 公域三笔 / 私域 role=4 的**金额算法不动**
- 比例计算（技术服务费 / 代理 ratio / 客户残差）**不动**
- **不得**改动 `amount` 相关逻辑（那是 F1-C8，已完成）

### (d) 错误信息要求

拒绝时 `code != 0`，msg 须含：期望地址集合（便于排障）+ 实际传入值。
**不得**只回 "invalid" 而不给排障信息。

## ★ 判据先于实现（判据 9）

`verify_f1c9_toaddress_guard.py` 真 HTTP + 真 DB：

| # | 用例 | 断言 | 红态（改前） |
|---|---|---|---|
| R1 | 公域 + `to_address` = 平台地址 | `code=0`，3 笔 | **绿**（防改过头） |
| R2 | 公域 + `to_address` = `TOTALLY_WRONG` | `code != 0` 且 **0 笔** | code=0 且 3 笔 ⇒ **红** |
| R3 | 公域 + `to_address` 为空 | `code=0`，3 笔（向后兼容） | **绿** |
| R4 | 私域 + `to_address` = 私域地址 | `code=0`，1 笔 role=4 | **绿** |
| R5 | 私域 + `to_address` = 错地址 | `code != 0` 且 **0 笔** | code=0 且 1 笔 ⇒ **红** |

★ **R1/R3/R4 是「防改过头」用例**：改前就该绿，改后仍须绿。

## 不在范围

- **不校验"谁有权收"**（越权）—— 那是另一议题
- 不改 `model/**`（`ToAddress` 字段已存在）
- 不改 handler（`api/v1/app/collect_result.go` 只记日志）
- 不改 `scan.go`
- 不改 `_manifest.sha256`

## 证据要求

- **`scan.go` 公域分支的实读结论**：确认 `to_address` 应落在三方之中的哪一方
  （★ 本卡规格 (a) 的关键前提，**不得凭猜**）
- `verify_f1c9_toaddress_guard.py` 改前红 / 改后绿两次真实退出码
- R1–R5 **逐条真实结果**（含 HTTP 状态 + code + bill 笔数 + msg）
- 改前 `to_address` 不符仍落 3 笔的 **DB 原文**（已由 I2-C1 采集）
- `collect_result.go` 改前 / 改后 sha256 + diff
- `go build` / `go vet` 真实退出码

## 停靠点

1. 若 `scan.go` 实读发现**公域根本不转账**或**只转给一方** ⇒ 停下升级
   （校验规则会随之改变，可能需 Owner 重裁）
2. 若发现 `to_address` 在**其他调用路径**（如 `Sk()`）中也未校验 ⇒ 登记上报，不扩大范围
3. 若发现校验会**破坏既有 gasleak 生产调用**（即 gasleak 实际传的地址不在集合内）⇒ 停下升级
