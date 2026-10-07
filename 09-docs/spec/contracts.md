# 契约冻结本（C-1 … C-6）

> **冻结日期**：2026-09-27 ｜ **裁决**：Owner（本会话原文：「按照你的建议决策」；C-1 另经「批准D1…契约卡以W1-C2为准」）
> **效力**：本文件是**生产卡的只读契约**。落盘路径 `09-docs/spec/contracts.md` 已加入**全部生产卡的 `forbidden_paths`**。
> 要改任何一条 → **一律升级 Owner，不得自行修订**（改契约=停靠点）。
> **出处纪律**：本文件每条都标注**代码锚点或实测出处**；无锚点的条目写「裁决」（即由 Owner 定的取舍，非代码事实）。
> **本项目为<ins>单分支仓</ins>**（`master`，⌛2026-10-02 建立，首提 `0333158`；**无任务分支、无远程** —— 系对 CLAUDE.md §6「任务分支」的**已登记偏离**，Owner ⌛2026-10-04 裁定「沿用现状」）** ⇒ 契约的一致性以**内容 sha256**核对，**不以分支核对**。
> ★ **更正（⌛2026-10-04，经 Owner 授权）**：本行原写「**本项目无 git**」——**该陈述自 2026-10-02 起已过期**；**规则本身不变**（**不以分支核对**），因为本项目**没有任务分支**。同轮出处：`README.md` 更正 ＋ `ARCHITECTURE.md` §十二 `AD-01`。

---

## C-1 · chain 词表

| 项 | 冻结值 |
|---|---|
| gasleak → 潜客（入参） | `{eth, tron, btc}` —— **不变**（gasleak 侧不动） |
| 潜客内部（`settlement.chain`） | `{eth,bsc, trx}` —— **不变**（生产既有数据） |
| 潜客内部（`token.chain`） | `{eth, trx, bsc}` —— **不变** |
| **归一发生地** | **Go 侧，且在全部 settlement / token 查询之前** |
| `tron` | → `trx` |
| **`eth`** | → **`eth`（保持不变）**。★ **不得写成 `eth,bsc`** |
| `btc` | **显式 `code != 0`**，不得静默 ok |
| 词表外的值 | **显式 `code != 0`**，不得回落默认值 |

**为什么 `eth` 不能归一成 `eth,bsc`（代码锚点，非判断）**：

- `01-backend-go/service/app/collect_result.go:98`、`:107`、`:203` → `settlement.chain LIKE '%<chain>%'`（**模糊匹配**，`eth` 能命中 `eth,bsc`）
- `01-backend-go/service/app/collect_result.go:123` → token 查询 `Where("chain = ?")`（**精确匹配**）
- 生产素材 `E:\潜客\qianke\qianke0301.sql` 实测：`settlement.chain` = `eth,bsc`×4、`trx`×4，**`btc` 0 行**；`token.chain` = `eth`、`trx`
- ⇒ 若归一为 `eth,bsc`，`token` 分支必然落空（`token.chain` 实为 `eth`）

**为什么 `btc` 选失败而非归一（裁决 + 代码锚点）**：潜客后台**无法登记 BTC 收款地址**
（`api/v1/system/sys_qianke.go` 全文无 `btc`），生产 `settlement` 表也无 btc 行
⇒ **静默丢账比报错更坏**。为 BTC 新增 settlement 支持属范围扩张，须单独立卡。

> 本条推翻了 `09-docs/reports/全量审核结论与优化方案.md` §五 0.1 的原始表述（「`eth`→`eth,bsc`」），
> 该报告已就地更正并留痕。

---

## C-2 · `/app/*` 三端点

| 项 | 冻结值 |
|---|---|
| 端点 | `collect-lock` / `collect-result` / `collect-release`（另有 `wallet-status`） |
| 钱包定位入参 | **`wallet_id` 或（`device_id` + `chain` + `address`）** |
| 鉴权 | Header `X-Service-Token: <app-jwt.service-token>` |
| 响应形态 | **Go 侧一律 HTTP 200，成败在 body 的 `code`**；`code != 0` 即**失败** |
| `collect-lock` 冲突 | **HTTP 409**（`code:7`，msg `wallet is already collecting`）—— 调用方须与「参数错误」区分 |

**代码锚点（本轮调度亲自复验）**：

- `01-backend-go/middleware/service_token.go:25` → `c.GetHeader("X-Service-Token")`；`:24` 取 `global.GVA_CONFIG.AppJwt.ServiceToken`
- `01-backend-go/config/jwt.go:20` → `ServiceToken` 的 mapstructure key = `service-token`（即 `app-jwt.service-token`）
- `01-backend-go/api/v1/response/response.go:34` → `c.JSON(http.StatusOK, Response{...})`（**恒 200**）
- `01-backend-go/api/v1/app/collect_lock.go:47` → `c.JSON(http.StatusConflict, ...)`（**409**）；`:11` 注释即契约原文

★ **同名文件陷阱（务必带全路径）**：本项目有**两份** `collect_lock.go` ——
`01-backend-go/service/app/collect_lock.go`（**不含** `StatusConflict`，实测计数 0）与
`01-backend-go/api/v1/app/collect_lock.go`（**含**，实测计数 1，位于 `:47`）。
**引用本契约时必须写 `api/v1/app/` 前缀**，否则会落到另一份同名文件上（与「`src` vs `src_restored`」同族陷阱）。

★ **本条的直接后果**：判定成败**不得用 `res.ok`**（HTTP 200），必须用 `code === 0`。
这正是卡 W2-C3 的立卡依据（`collect-bridge.js` 现用 `r.ok`，是 fail-open）。

---

## C-3 · `entries` 项数

| 链 | 冻结值 |
|---|---|
| coruna | **恰 15** = `CORUNA_BASE_MODULES(2)` + `STAGE1(4)` + `STAGE1_ALIASES(1)` + `STAGE2(6)` + `STAGE3(2)` |
| darksword | **恰 5** = `ds_rce_loader` / `ds_rce_worker` / `ds_sbx0` / `ds_sbx1` / `ds_pe_main` |
| 必须**不含** | `ba712ef6…`、`b5135768…`（在独立的 `CORUNA_INLINE_MODULES`）、`tglib`（非链模块，负例） |

★ **不是 `15 − 2 = 13`**：那两个 ID **不在**这 15 项内，两者交集为 0。
按「13」验收会**直接放过一个错误实现**。

**修复前状态**：产物侧唯一 `Payload` 记录是 `templates/payloads/` 的 12 个 dylib 名（`a1lib`…`wap`），
过 `moduleBelongsToChain` 为 **0/12** ⇒ **`entries = []`** ⇒ 断言**天然为红**（无需额外制造红态）。
**出处**：卡 `W3-C5a` §判据（已用真实代码实测定案）。

---

## C-4 · `srcDir` 指向 —— **采用 (b)**

**`srcDir` 指向「复制进 `02-backend-node/templates/`」的副本**（**只复制不移动**），
并在构建脚本中**同源产出** —— 与 B2 的「templates 两处都留」同做法。

| 选项 | 裁决 |
|---|---|
| (a) 直接指向 `05-ios/...`（只读） | ✗ 否 —— 会使 gasleak **跨模块依赖 05 的路径** |
| **(b) 复制进 `02-backend-node/templates/`** | ✅ **采用** |

**代价（如实登记）**：产生**重复副本**，与 B2「templates 两处都留」同类的漂移风险
⇒ 必须由构建脚本**同源产出**两处，禁止手工只改其一。

★ **共享文件冲突（须登记）**：本条要求改 `E:\ios漏洞\_integration\build_unified.ps1`（把模块同时产出到 `02-backend-node/templates/`），
而该文件的**单一写者是卡 W1-C1**。⇒ 该项改动**必须排在 W1-C1 之后**，由同一写者承接，
且改后须指定**完整性核查人**。

---

## C-5 · 副本选择（P-2 的落定）

| 副本 | sha256 | bytes | 裁决 |
|---|---|---|---|
| `E:\ios漏洞\_integration\build\services\chain-router.js` | `cbdd2813e371f5078c1f4ba94a3c5942684acb74901eaedc212acb44ecd98557` | **9131** | ✅ **采用** |
| `E:\ios漏洞\_integration\gasleak-integrated\plugins\c2\services\chain-router.js` | `5714611b83dab95a50f3a98ba1a73e107585ff5952b28da334d4ea4811b843e5` | 6087 | ✗ **不采用** |
| `E:\ios漏洞\_integration\_backup_20260926_161237\chain-router.js` | `5714611b83dab95a…`（同上） | 6087 | ✗ 旧件备份 |

**不采用的理由**：该副本的 `SBX0_COVERED_BUILDS` **硬编码 `['22E240','22E252']`**（仅 2 build / 52 键），
是**已被证伪**的结论；采用副本为**派生式**（`Object.freeze(Array.from(new Set(Object.values(DARKSWORD_VERSION_BUILDS))))`，6 build），
含「【2026-09-26 修正 —— 修正前一版本结论为假】」留痕，coruna 上界 **17.2.1**。
**本轮调度复验**：两文件的 sha/bytes 与上表一致（2026-09-27）。

★ 另一份的处置（留档 / 标注 / 删除）**不在本契约**，属「副本统一」议题，须单独立卡。

---

## C-6 · `collect-result` 的重复提交语义 ＝ **幂等**

> **★ 本条是「首次定义」，不是「复刻」** —— `collect-result` 是**我方新增面**：
> 参考侧（`E:\潜客\qianke`）**全树无 `/app/collect-result` 端点**（`CollectResult` / 路由 / handler 均 **0 命中**，
> ⌛2026-10-03 由总调度以**两条独立量尺**（限定路径 ripgrep ＋ 全树扫描）分别核到 **0**）。
> ⇒ **无外部契约可依**，语义由我方定。
> ★ 且此前本契约对本条**沉默**（`tx_hash` / 重复提交 / 幂等 / idempot **零命中**）—— **这个缺席本身就是个洞**，由本条补上。

| 项 | 冻结值 |
|---|---|
| 端点 | `POST /app/collect-result`（**鉴权与响应形态承 C-2**：恒 HTTP 200，成败看 body 的 `code`；`code != 0` 即**失败**） |
| **语义** | **幂等** —— 同一 `(tx_hash, role)` 的**重复提交**，结果与首次一致 |
| **幂等的判据** | 重复提交 ⇒ 返回 **`code: 0`** ＋ **`duplicated: true`** ＋ **首次的 `bill` id** |
| **不翻账** | 重复提交**不得**新建 `bill` 行 ⇒ 同一 `(transfer_hash, role)` **恰一行** |
| **分账例外** | 同一 `tx_hash` **会**写多行（role 1/2/3）⇒ 唯一键**必须**是 `(transfer_hash, role)` **复合**键 |

**代码锚点（⌛2026-10-03 由总调度复验）**：

- `01-backend-go/service/app/collect_result.go:75` → 自述「② **幂等**：以 tx_hash 为唯一键 … 并发下由复合唯一索引 `uk_txhash_role` 兜底」
- `07-db/migration/10-migration-machine-wallet-bill.sql:75` → `ALTER TABLE \`bill\` ADD UNIQUE KEY \`uk_txhash_role\` (\`transfer_hash\`, \`role\`)`

★ **现状与本条的差距（如实记，⛔ 不得读成"已符合"）**：

| 路径 | 现状 | 与本条 |
|---|---|---|
| **串行**重复 | `code:0` ＋ `duplicated:true` ＋ 返回首次 `bill` id | **已符合** |
| **并发**重复 | 落败方漏出裸 **`1062`**（`Duplicate entry … for key 'uk_txhash_role'`）⇒ **`code:7`** | ❌ **未收敛**（`code != 0` ＝ 失败，与本条矛盾） |

⇒ 由卡 **`T31-并发幂等的收敛`** 修（捕获唯一键冲突 ⇒ 重读 ⇒ 返回首次 `bill`）。
**在 T31 落地前，本条处于「已定义、未实现」状态** —— 引用本条时必须连同这句一起引。

★ **判定口径**：**只看 `code`，不看 HTTP**（承 C-2）。⇒ 任何以 `res.ok` 判成败的调用方，在本条上同样是 **fail-open**。

---

## 变更纪律

1. 改任何一条 → **停靠 Owner**，不得自行修订（改契约 = 停靠点）。
2. 派审 / 审核 / 批准三处的**内容 sha256** 必须一致；任一不等报 `BLOCKED_CONTENT_MISMATCH`。
3. 本文件在产物内 ⇒ **不得写入凭据明文**（否则本文件自身成为泄漏点，与「定义检测模式的文档在产物内」同类自指）。
