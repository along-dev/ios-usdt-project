---
id: F1-C1
mode: 实施
wave: 1
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  本卡触碰 01-backend-go/blockchain/scan.go —— 命中调度《高风险/真高危路径》表的
  【真高危 → 命中即 R3】（链上转账 ×37 + 分账）。
  且缺陷性质为「静默吞掉对账结果」（bill 永不置 status=1），与 P0-1（静默丢账）同族。
  门禁强度自知：改前判据须为【静态断言】（该列不存在），改后须为【行为/结构断言】，
  不得只看 go build 绿。
来源: 09-docs/reports/全量审核报告_独立复核版.md §三 P1-A + §六（模型定义与生产 schema 双向确认）
base:
  - path: 01-backend-go\blockchain\scan.go
    sha256: 92b23405d643c8b286bdb93e5ebee18ea47bf380e42ec52e51799deb87ff481b
    bytes: 17792
    eol: LF
  - path: 01-backend-go\model\app\token.go
    sha256: 48a3c9230d44646a0f180b63c3dfba025932f375d0ab73274e209bcd72497e90
    bytes: 533
    eol: LF
  - path: 07-db\schema\qianke.sql
    sha256: d8540e2d6201c5a8dcc3ea6d4d0522cf903281db505d74b2872105dfc91ae56b
    bytes: 31381
    eol: CRLF      # ★ 实测 548 CRLF / 0 LF —— 非 LF！勿照抄旧登记（P-5）
allowed_paths:
  - 01-backend-go\blockchain\scan.go
  - E:\ios漏洞\_integration\_fix_work\verify_f1c1_bill_reconcile.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本 C-1…C-5，生产卡只读）"
  - "01-backend-go\\model\\**（★ 不得给 token 加列 —— 见规格 (c)）"
  - "07-db\\schema\\qianke.sql、07-db\\migration\\**（生产 schema 不动）"
  - "01-backend-go\\service\\app\\collect_result.go（属 A 线另一路径，本卡只【读】）"
  - "05-ios/**、06-android/**、02-backend-node/**、03-web-admin/**、04-landing/**"
  - "_manifest.sha256"
verify:
  # ★ 判据先于实现（判据 9）：先写脚本、先跑到红，再改实现。
  - python _fix_work\verify_f1c1_bill_reconcile.py    # ①动前：须【红】，退出码 != 0，留证
  - python _fix_work\verify_f1c1_bill_reconcile.py    # ②动后：须【绿】，退出码 0
  - go build ./...                                    # 退出码 0
packages: {}
---

# F1-C1 [R3] 对账链路 join 到不存在的列 → bill 永不复核

## 目标

消除**「归集回传后的链上复核永不执行 ⇒ bill 永不置 `status=1`、代理/客户 `usdt_num` 永不累加」**。

## 缺陷事实（本轮实读，非转述）

| 位置 | 现状 |
|---|---|
| `scan.go:288` | `Joins("left join settlement on settlement.id = token.settlement_id")` |
| `model/app/token.go:3-10` | `Token` 字段仅 `ID`/`Chain`/`CoinName`/`CoinAddress`/`RadioUsdt`/`Rpc` —— **无 `SettlementId`** |
| `07-db/schema/qianke.sql:483-491` | `token` 表 6 列 —— **无 `settlement_id`** |
| `scan.go:289`（原） | `Find(&transInfoList)` **未检查 `.Error`** ⇒ 查询失败被吞 |

**双向确认**：ORM 模型与生产 schema **均无此列** ⇒ 不是"漏映射"，是**该列从不存在**。

**后果链**：join 失败 → `transInfoList` 恒空 → `:290` 循环不执行 →
`:308` `billOrder.Status = 1` **永不执行** → `:312-325` 客户/代理 `usdt_num` **永不累加**；
且错误被吞 ⇒ **日志里也看不到**。

## 规格

### (a) join 改指向 `bill`（本卡主体）

收款方归属本来就在 `bill` 上（`collect_result.go:165` 写入 `SettlementId`）。
`settlement.user_id` 的唯一消费者是 `:315`/`:321`（按 `Role` 2/3 取客户/代理）。

```
原: .Select("bill.*, token.chain, token.rpc, settlement.user_id")
    .Joins("left join settlement on settlement.id = token.settlement_id")
    .Joins("left join token on bill.token_id = token.id")

新: .Select("bill.*, token.chain, token.rpc, settlement.user_id")
    .Joins("left join token on bill.token_id = token.id")
    .Joins("left join settlement on settlement.id = bill.settlement_id")
```

### (b) 补错误检查（不得省略）

查询后必须检查 `.Error`，失败时 `global.GVA_LOG.Error(...)`，
且必须**明确区分「查询失败」与「确实没有待复核的 bill」** ——
不得让"查询失败"表现为"循环体不执行"。

### (c) ★ 明确禁止的修法

❌ **不得**给 `token` 表/model 加 `settlement_id` 列。
理由：那是**改生产 schema 的形状**去迁就一句写错的 join，
且 `bill.settlement_id` **已承载同一语义**（双写会引入一致性风险）。
若认为必须加列 ⇒ **停下升级 Owner**（属范围扩张，触 `07-db/**`）。

### (d) 保持既有语义不变

- `:293-298` 的 `switch Chain`（`trx` / `eth,bsc`）**不动**
- `:331-333` 的 `wallet.SkCount += 1` / `Progress = 0` **不动**
- `:303-327` 的成功判定与累加逻辑**不动**（只修它现在拿不到数据的问题）

## ★ 判据先于实现（判据 9）

必须先写 `E:\ios漏洞\_integration\_fix_work\verify_f1c1_bill_reconcile.py`（放产物外，**P-4**）并跑到**红**。

| # | 断言 | 红态（改前） |
|---|---|---|
| R1 | `scan.go` 全文 `token.settlement_id` 命中数 = **0** | 命中 **1** ⇒ 红 |
| R2 | `scan.go` 含 `settlement.id = bill.settlement_id` | 命中 **0** ⇒ 红 |
| R3 | 复核查询处存在 `.Error` 检查 | 命中 **0** ⇒ 红 |
| R4 | `model/app/token.go` **仍不含** `SettlementId`（防改错方向） | 绿（防改过头） |
| R5 | `07-db/schema/qianke.sql` 的 `token` 段**仍无** `settlement_id` | 绿（防改过头） |

★ **量尺前置断言（P-5）**：R1 的模式必须在**改前的真实文件**上**先命中 1 次**，
证明模式有效；**命中 0 时先怀疑模式坏了**。

## 不在范围

- 不改 `model/**`、`07-db/**`（见规格 (c)）
- 不改 `collect_result.go`（A 线另一路径）
- 不改 `src/`（Node 扁平版，**P-8**）
- 不改 `_manifest.sha256`

## 证据要求

- `verify_f1c1_bill_reconcile.py` 改前**红** / 改后**绿**两次真实退出码
- `scan.go` 改前 / 改后 sha256 + bytes
- `grep -c 'token.settlement_id'` 改前=1 / 改后=0 的**真实输出**
- `go build ./...` 退出码（★ 取码不接管道：`echo "EXIT=$LASTEXITCODE"`）

## 停靠点

1. 若认为需给 `token` 加列 ⇒ **停下升级**（触 `07-db/**` + 契约）
2. 若发现 `:288` 之外还有引用 `token.settlement_id` 的位置 ⇒ **登记上报**，不扩大范围
3. 若 `go vet` 出现**新增**告警（非 N-9 既有 3 条）⇒ 停下升级
4. 若 `go.exe` 不可用 ⇒ 用 `E:\ios漏洞\_integration\_fix_work\_toolchain\go\bin\go.exe`
   （★ 本轮实测：`C:\`、`E:\` 4 层深内**搜不到** `go.exe`）
