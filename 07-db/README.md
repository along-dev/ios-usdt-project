# 07-db（数据库 schema 与迁移）

> **卡 I3-C3**｜基线：本轮实测｜**不得写入凭据明文**

## 职责

数据库 **schema 定义与迁移**。生产库为 **MariaDB，端口 13306**（固定，不得改）。

## 关键文件

| 路径 | 内容 |
|---|---|
| `schema/qianke.sql` | 潜客生产库 schema |
| `migration/**` | 迁移脚本 |

★ **`qianke.sql` 的换行实测为 CRLF**（548 CRLF / 0 LF）——
曾经被卡片误登记为 `eol: LF`；按错误登记行事会把 548 行全量改写，
**diff 膨胀并触发脱敏连锁差异**。取基线时**必须实测 eol，不得沿用旧值**。

## ★★ 三源权威关系（**先读本节再动库**）

与 schema 相关的**三个源**，职责与优先级**不同**，**不得混用**：

| # | 源 | 明确路径 | 地位 |
|---|---|---|---|
| ① | **基线快照** | **`07-db/schema/qianke.sql`** | **建库用**。★ **它 ≠ 完整 schema** —— 缺 `migration/**` 追加的列与键 |
| ② | **唯一增量权威** | **`07-db/migration/**`**（如 `07-db/migration/10-migration-machine-wallet-bill.sql`） | **必须**在 ① 之后执行。**最终 schema 形状 = ① 叠 ②** |
| ③ | **GORM `AutoMigrate`** | 调用点：**`01-backend-go/initialize/gorm.go:30`**（`RegisterTables`）· **`01-backend-go/source/system/menu.go:29`** | ⛔ **不作 schema 源** —— 仅**容错/幂等补建**；**不得**据它推断 schema 形状 |

**★ 依据（原文照抄）** —— `07-db/migration/10-migration-machine-wallet-bill.sql:4`：

> `-- 目标：统一目录产物中的 07-db/schema/qianke.sql 建库后，执行本脚本补齐字段。`

**★ 为什么顺序不能颠倒（实例，可复算）**：四个标识 —— `uk_txhash_role`（**幂等唯一键**）·
`btc_address` · `btc_private_key` · `custom_user_id` —— **在 `07-db/schema/qianke.sql` 里的出现次数均为 0**，
**只存在于 `07-db/migration/**`**。
⇒ **只跑 ①、不跑 ②** ⇒ 缺 `uk_txhash_role` ⇒ **幂等唯一键静默消失**；
而 `schema/qianke.sql` 头部看起来**完整且权威**、**无可机检标记**提示"需配 migration"。

**★ 复核命令（照着 grep 即可）**：
```bash
rg -c "uk_txhash_role|btc_address|btc_private_key|custom_user_id" 07-db/schema/qianke.sql   # 预期 0
rg -l "uk_txhash_role|btc_address|btc_private_key|custom_user_id" 07-db/migration/          # 预期非空
rg -n "AutoMigrate" 01-backend-go/initialize/gorm.go 01-backend-go/source/system/menu.go    # ③ 的调用点
```

### ④ ⛔ 禁令：**不得据 `07-db/schema/` 单独建库**

任何"建库"动作**必须** ＝ ① `07-db/schema/qianke.sql` **＋** ② **全量** `07-db/migration/**`。
照 `schema/` 单建 ＝ **静默丢列/丢键**（且与本节「注意」一节的成文禁令相违）。

### ⑤ ⛔ 施工面卫生：`migration/**` 的目标库**由应用器决定**（**T52 已删掉写死的 `USE`**）

> **来源**：`T49`（承 `T48` 的 `F-T48-1`，**P0 级数据破坏面**）—— ★ **`T52` 已把 4 件里写死的 `USE qk_e2e;` 删除** ｜ **可机检件**：`_fix_work/verify_migration_hygiene.py`

**★ 一句话口径**：目标库由应用器决定 —— `migration/**` **不再**写死库名（⛔ 不得回退）。

**1) 目标库**只由应用器决定 —— `migration/**` **不再**写死库名：

```bash
grep -rnE "^\s*USE " 07-db/migration/*.sql      # ★ T52 之后：预期 0 处
```

★ **删它的理由（不是风格问题，是fail-closed）**：`USE` 会**击穿**应用器的 `<db>` 实参 ——
生产命令 `mysql -h 127.0.0.1 -P 13306 -u root <db> < …\migration\<脚本>.sql` **本就传了库**，
但只要文件里有 `USE qk_e2e;`，**传任何别的库也会被它切走**（**静默打错库**）。
⇒ **现在**：传错库/不传库 ⇒ **`1046 No database selected`**（**响亮失败**），⛔ 不再静默落错库。

**2) ★★ `*-rollback.sql` 的<ins>字典序</ins>先于对应 forward 件** ⇒ **顺序是反的**（★ 本条与 `USE` **无关，仍然成立**）：

```
50-custom-ownership-rollback.sql     ← 先（`-` 的序 < `.`）
50-custom-ownership.sql              ← 后
```

而 `50-custom-ownership-rollback.sql` 干的是 **`DROP COLUMN IF EXISTS custom_user_id`** ⇒
**任何按字典序/`ls` 顺序枚举 `migration/**` 的应用器，会先跑 rollback**。
⇒ **`rollback 先于 forward`** —— 这不是理论，是**文件名排序的必然结果**。

**3) 装置仍保留 `USE` 中和（<ins>纵深防御</ins>）** —— 若将来有人再往迁移件里写 `USE`，口径必须是：

- 中和口径：**按 `;` 分句后逐句判 `USE`** —— ⛔ **不能只锚行首**：同行中段的
  `SET @x:=1; USE <他库>; ALTER …;` 会**漏**（`F-T48-A`）；
- 中和之后**必须**有**哨兵**：任何代码级 `USE <非目标库>` ⇒ **直接抛错、不许继续**；
- ★ 现成实现见 `_fix_work/verify_ad09_schema_migration_diff.py` 的 `neutralize()`（**含哨兵**）。

**4) 应用集<ins>必须排除</ins> 4 件**（⛔ 且**排除要响亮登记**，不许静默跳过）：

| 排除件 | 理由 |
|---|---|
| `30-casbin-seed.sql` | ★ **已废**：用 MySQL 8 专属的「派生表列别名」`AS v(p,d,g,m)` ⇒ **本机 MariaDB 11.4.4 报 `1064`**；**已被 `31-casbin-seed-v2.sql` 取代**（其 `:9` 自证） |
| `40-prod-db-hardening.sql` | 自述**部署期执行**、**不在装测环境运行**（Owner 裁决）；跑它会立刻切断装测环境连接 |
| `50-custom-ownership-rollback.sql` | rollback 件（会让「期望 schema」undefine）**＋ 字典序先于 forward** |
| `51-customusdtnum-agentusdtnum-backfill-rollback.sql` | 同上 |

⇒ **有效 forward 应用集 ＝ `10/20/21/22/31/32/50/51`（8 件）**。

**★ 一条命令自检（只读、不连库）**：

```bash
python E:\ios漏洞\_integration\_fix_work\verify_migration_hygiene.py              # 期望 RESULT=GREEN / EXIT=0
python E:\ios漏洞\_integration\_fix_work\verify_migration_hygiene.py --selftest   # 负控/正控/变异
```

⛔ **改 `migration/**` 仍属高风险路径** —— `T52` 那次删除是**已获 Owner 授权的一次性操作**；今后的改动仍须单独授权。

## ★ 重要表事实（本轮实测）

### `token` 表 —— **无 `settlement_id` 列**

`qianke.sql` 中 `token` 表共 6 列：
`id` / `chain` / `coin_name` / `coin_address` / `radio_usdt` / `rpc`。

这与 `01-backend-go/model/app/token.go` 的 GORM 结构体一致。

⇒ **`token.settlement_id` 这一列从不存在**。若代码里出现该 join，属于写错目标表
（收款方归属在 **`bill.settlement_id`** 上）。该缺陷已修复（见 F1-C1）。

### `settlement.chain` / `token.chain` 的取值

生产素材 `E:\潜客\qianke\qianke0301.sql` 实测：

| 列 | 实测值 |
|---|---|
| `settlement.chain` | `eth,bsc` ×4、`trx` ×4，**`btc` 0 行** |
| `token.chain` | `eth`、`trx`（**精确匹配**，见契约 C-1） |

⇒ 链路名归一**必须**保持 `eth` → `eth`（**不得**写成 `eth,bsc`），
否则 token 分支必然落空。详见契约 **C-1**。

### 私域路径

生产 `settlement` 表存在 `user_id=-1` 的 `'private trx'` / `'private'` 行
⇒ **私域（`region=2`）路径确在生产使用，非死代码**。

## 相关契约

- **C-1**（chain 词表）：`tron`→`trx`；`eth`**保持不变**；`btc` **显式失败**；词表外值显式失败。
- **BTC settlement 支持**：潜客后台**无法登记 BTC 收款地址**（`sys_qianke.go` 全文无 `btc`）
  ⇒ 为 BTC 新增 settlement 支持属**范围扩张，须单独立卡**（当前为停靠点）。

## 注意

- 本目录的 `migration/**` 与 `schema/**` 属**高风险路径**（命中即至少 R2）。
- **不要**为迁就一句写错的 join 而给表加列 —— 那是改生产 schema 的形状。

---

## ★ 假绿族严格档（Go 测试；**谁在跑全绿时按它**）

> **来源**：卡 `T50`（假绿族统一严格档，含 `F-T47-1`/`F-T47-3`）｜ ★ 本节与 DB schema **无关**，仅因卡面指定落点于此。

`01-backend-go/blockchain/` 里若干测试**前提缺失时以 `t.Skip` 收场** ⇒ 单独 `go test` **退出码仍 0** ⇒ 门禁/CI 会把「**全跳过**」读成「**通过**」（在册 `E-359`/`E-360` 族「恒绿＝没检查」）。
覆盖面（**收窄后**）：`billing_test.go`（`WBE01A_TEST_DSN` 未设）· `t44_v1_test.go`（隔离库 `qk_e2e_test` 不可用）。⛔ `erc_test.go`/`trc_test.go` 的 `Skip` 属**外部前提**（`ANKR_API_KEY`／联网，`G-08` 成文口径）⇒ **有意保留，不在本档**。

**严格档开关**：环境变量 **`DSH_REQUIRE_ISOLATED_DB=1`** ⇒ 上述 `Skip` 改 **`Fatal`**（`billing_test.go` 的 `requireIsolatedDB` ＋ `t44_v1_test.go` 的 `t44RequireIsolatedDB`）。
★ **默认档（不设）⇒ 行为等价（`skip` 数、退出码一致）** —— ★ 该"不变"**只限「<ins>缺前置</ins>」这条路径**（`billing` 无 `WBE01A_TEST_DSN` ／ `t44` 的隔离库不可用）；★ **`skip` 文案已统一**（两条原专用文案改为 helper 的通用文案）。
★ ⚠️ **例外（默认档<ins>确实</ins>变了，且是 `F-T47-1` 的本意）**：`t44` 的 `DSH_DB` 护栏由黑名单改**白名单**后，**`DSH_DB ∉ {qk_e2e_test}` 在默认档下<ins>也</ins>会 `Fatal`**（白名单外一律拒）。

### ★★ 最隐蔽的一态：**父测试 `PASS`，而子测试全 `SKIP`**

`go test` 对**用 `t.Run` 组织的父测试**：**子测试全 `SKIP` 时，父测试不报 `SKIP`、而报 `PASS`**（实测：`TestAccumulateUsdtNum` 三子用例 `SKIP` ⇒ 父 `--- PASS`）。
⇒ **按「父 `PASS`」判门禁，会把「一条都没跑」读成「通过」** —— **本族最隐蔽的假绿**。
⇒ 判据须**下钻到子测试的 `--- SKIP` 行**，或（更稳）**直接以严格档跑**（见下）。

★ **可复跑命令**（`F-T54-2D`；★ 该断言已由**两条异质复核<ins>各自实测</ins>**成立）：
```bash
go test -count=1 ./blockchain/ -run 'TestAccumulateUsdtNum|TestT54_WhiteListGuard' -v
```

★ **期望的父子行样本**（逐字摘录自实测输出 —— ★ 注意**父子两行的`标签`相反**）：
```
--- PASS: TestAccumulateUsdtNum (0.00s)                              ← ★ 父：报 PASS
    --- SKIP: TestAccumulateUsdtNum/status=0_⇒_置1且累加 (0.00s)      ← ★ 子：全 SKIP
    --- SKIP: TestAccumulateUsdtNum/未知_role_⇒_显式错误（不静默） (0.00s)
    --- SKIP: TestAccumulateUsdtNum/userId_无对应主体_⇒_报错且不提交 (0.00s)
--- SKIP: TestAccumulateUsdtNum_Idempotent (0.00s)
```
⇒ ★ **出处**：`09-docs/reports/复核_T54_20261005.md` **§10.1**（**第 1 名**补跑）· `09-docs/reports/复核_T54_第2名_20261005.md` **§9**（**第 2 名**追补）—— **两审独立**各测得同一父子行形态。

★ **引用 `skip` 计数必须**<ins>连同命令与范围</ins>**写出**（`F-T50-4`：同一树在不同 `-run`/包范围下计数不同 ⇒ 单写一个数无法互校）。本轮实测口径举例：
```bash
go test -count=1 ./blockchain/ -run 'TestAccumulateUsdtNum|TestT54_WhiteListGuard' -v   # 默认档 ⇒ `--- SKIP` × 4（3 个子用例 ＋ `…_Idempotent`）
```
★ 派单/复核报过的 **22 / 19** 是**别的范围口径**（全包／全仓），**各自都对** —— 故计数**一律带命令**。

**★ 谁在跑全绿时按它（`T54`／`F-T50-1` 接线闭合）**：**本仓的「Go 全绿」验收/复核动作**按它 ——

```bash
python E:\ios漏洞\_integration\_fix_work\run_regression_go_strict.py              # 严格档跑 go test ./...
python E:\ios漏洞\_integration\_fix_work\run_regression_go_strict.py ./blockchain/ # 只跑指定包
python E:\ios漏洞\_integration\_fix_work\run_regression_go_strict.py --selftest    # ★ 置位自证 ⇒ PLACEMENT=OK
```

★ 该脚本**只置位环境变量并转调 `go test`**（⛔ 不联网、不启停服务、不写库）；路径一律 `E:\` 真实路径（⛔ 不用 `X:` —— `subst` 会话级、重启即失效，在册 `E-11`/`P-45`）；★ **自足**（脚本内显式给 `GOCACHE`/`GOFLAGS`，不依赖调用方 shell）。
★ **判「全绿」时必须用它**；直接 `go test ./...` 得到的是**默认档**（可能全 `Skip` 而仍退 0）。
★ **可机检的置位证据**：`--selftest` 对**同一个 DB-free 用例**跑**默认/严格 A/B**，断言「默认退 `0` ／ 严格退 `≠0`」并打印 **`PLACEMENT=OK`** ⇒ 任何人可复核「开关确已接上」，且**可进任何门禁**（退出码确定）。

★ ★ **本节的两条效力边界（`T54` 双审：`F-T54-A`／`F-T54-2B`）**：
- ★ **① 本节是「<ins>接线闭合</ins>」，⛔ <ins>不消除</ins>默认档假绿** —— 开关的**接线**可自证（`PLACEMENT=OK`），但**「有人按」是<ins>纪律</ins>、不是<ins>机制</ins>**：**没有任何东西在「没人按」时失败** ⇒ **直接 `go test ./...`（默认档）仍「全 `Skip` ⇒ 退 0」＝ 假绿仍在**。⇒ **判「全绿」的人必须记得按它**。
- ★★ **② 按它会让 `billing` <ins>清掉隔离库那 3 张表</ins>**（`DROP TABLE IF EXISTS custom, agent, bill` —— `billing_test.go` 的 `openTestDB`；`t.Cleanup` 跑完**还会再清一次**）⇒ **须与<ins>正用 `qk_e2e_test` 的线互斥</ins>**（★ 与「**同一时刻只许一条线跑本仓 Go**」**同源**）。★ 目标库是**隔离库**（白名单保证 ⛔ **不会落业务库**），且 `iso_run` **可重播种**。
