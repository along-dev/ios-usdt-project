# T49 —— `F-T48-1`（**P0**）：`migration/**` **写死 `USE qk_e2e;`** —— naive 全量应用**会打到业务库**（含一条 `DROP COLUMN` 回滚件）

> **卡**：T49 ｜ **来源**：`T48` 执行面查出（安卓继承**停工报危**）· **总调度现读自证**
> **档**：**P0 级风险**（**数据破坏**面）｜ **执行**：**待派** ｜ **收口/提交**：总调度第四任
> **状态**：**已立卡、待派**（★ 属**新增范围**，超出 Owner 已批的 `T47`/`T48` ⇒ **待 Owner 点头再派**）｜ **日期**：2026-10-05

---

## 一 · 缺陷（★ **总调度现读自证**，非转述）

```
$ grep -rnE "^\s*USE " 07-db/migration/*.sql
07-db/migration/50-custom-ownership.sql:26                              USE qk_e2e;
07-db/migration/50-custom-ownership-rollback.sql:14                     USE qk_e2e;
07-db/migration/51-customusdtnum-agentusdtnum-backfill.sql:56           USE qk_e2e;
07-db/migration/51-customusdtnum-agentusdtnum-backfill-rollback.sql:13  USE qk_e2e;
```

★ **`50-custom-ownership-rollback.sql` 的 `:14-16`** ＝ **`USE qk_e2e;` ＋ `ALTER TABLE \`packet\` DROP COLUMN IF EXISTS \`custom_user_id\`;`**。
★ **字典序**：`50-custom-ownership-rollback.sql` **<ins>先于</ins>** `50-custom-ownership.sql`（`…-rollback` < `…sql` 的 `.` vs `-`）⇒ 任何**「依序跑 `migration/**` 全部」**的 naive 应用器会：**① 连到业务库；② 先执行 `DROP COLUMN`**。
⇒ 业务库 `qk_e2e` **确有** `custom_user_id`（`AD-09` 方案件 §1.3 实读）⇒ **这是真删列**，且**在同一轮里 forward 件还没建它**（顺序反了）。

## 二 · 目标

让「**把迁移应用到<ins>非业务库</ins>**」这件事**可机检、不易误用**；★ ⛔ **不改变生产部署流程**（生产可能**就是**依赖 `USE qk_e2e` 的）。

## 三 · 范围（**分三档，⛔ C 不在本卡**）

| 档 | 内容 | 风险 | 是否本卡 |
|---|---|---|---|
| **A** | **文档**：`07-db/README.md` 补一条**醒目警示** —— ① `migration/**` **内写死目标库名**；② naive 全量应用**会写到 `qk_e2e`**；③ **`*-rollback.sql` 字典序先于对应 forward 件**；④ 应用到非生产库**必须先中和 `USE`（或整库重定向）** | 低 | ✅ **本卡** |
| **B** | **可机检件**：★ **⌛10-05 改齐**（原卡写 `verify_migration_use_guard.py` ＋「应用器须报告中和了几处 USE」，**与派单口径不一致** ⇒ 执行者按**更晚的派单**实现，本行照实改）：**新增 `verify_migration_hygiene.py`** —— **A1** 应用集必须**恰为** `10/20/21/22/31/32/50/51` · **A2** 全 `migration/*.sql` 中和后**代码级 `USE` 只剩临时库** · **A3** **同行中段**可抓 · **A4** README **逐字**含 `会写到 qk_e2e` ＋ `rollback 先于 forward`；★ **它 `import` ①的常量与 `neutralize()`（单源，⛔ 不各写一套 ⇒ 不会漂移）**；★ 带**负控/反向/变异** | 低 | ✅ **本卡** |
| **C** | 把 `USE qk_e2e;` 从迁移件里**去掉**（改由应用器传目标库） | **高**（动 `migration/**`、可能断生产流程） | ⛔ **须 Owner 单独授权** |

## 四 · 验收（待派时细化）

- `A`：README 里该警示**在位**且**逐字**含"会写到 `qk_e2e`"与"rollback 先于 forward"两点。
- `B`：正控（中和 ≥1 处 ⇒ `0`）· **负控（不中和 ⇒ 必红）** · 变异承重 · 登记索引。
- `C`：⛔ 不在本卡。

## 五 · 边界与停靠点

- ⛔ **不改 `migration/**`**（**高风险路径**）—— 除非 Owner 单独授权 `C`。
- ★ **本卡<ins>不阻塞</ins> `T48`**（`T48` 的脚本已 **USE 中和 ＋ 拒业务库名 ＋ 端口钉死**，安全）。
- ⛔ 不做 git 写操作（提交权在总调度）。

---

## 六 · ★ 追加（⌛2026-10-05）：`F-T48-2` —— `30-casbin-seed.sql` **MySQL 8 专属语法、本机 MariaDB 报 `1064`**（且**已被 `31` 取代**）

**★ 总调度现读自证**：
- `SELECT * FROM (SELECT 1 AS a, 2 AS b) AS v(a, b);`（隔离 MySQL 13306）⇒ **`ERROR 1064 (42000) … near '(a, b)'`** ⇒ **本机 MariaDB 11.4.4 拒「派生表<ins>列别名</ins>」**。
- `30-casbin-seed.sql:133` ＝ `) AS v(p, d, g, m)`；★ 全 `migration/` **只有这一处**用该写法。
- ★★ **`31-casbin-seed-v2.sql:9` 的注释原文**：「★ **v2 修正：v1 用了 `AS v(p,d,g,m)` 派生表【列别名】语法**」⇒ **`31` <ins>就是 `30` 的修正版</ins>** ⇒ **`30` 是<ins>已被取代的 v1</ins>**。

**危害**：任何**在本 MariaDB 上"依序跑 forward 迁移"**的流程都会**卡在 `30`**（不只影响判据件）。
**处置（并入本卡）**：
- **`A`** 文档警示**加一条**：「`30-casbin-seed.sql` 用 **MySQL 8 专属**的派生表列别名 ⇒ **在本机 MariaDB 报 `1064`**；★ 它**已被 `31-casbin-seed-v2.sql` 取代** ⇒ 应用集**应排除 `30`**」。
- **`B`** 可机检件**加一条断言**：「**应用集里若含 `30` ⇒ 红**」（★ **带负控**：把 `30` 放回 ⇒ 必红）。

---

## 七 · 追加（⌛2026-10-05）：并入 `F-T48-A`（**P2**）—— 中和/哨兵**只锚行首**

**来源**：`T48` 复核件（`复核_T48_追补审核_20261005.md`）之 `F-T48-A`；**总调度采纳**。
**事实**（复核者**离线实证**）：`E:\ios漏洞\_integration\_fix_work\verify_ad09_schema_migration_diff.py` 的 `neutralize()`（`:109`）与**哨兵**（`:122`）**都是** `re.match(r"(?i)^use\s+…")`（**锚行首**）⇒ **同行中段的 `USE <他库>;` 双漏**（喂 `SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;` ⇒ **未抛错、原样保留**）。
★ **当下影响 ＝ 0**（复核者现读全 12 件：真实 `USE` **仅 4 处、全在行首**）⇒ **潜伏**；★ 但它是**为缓解 `F-T48-1`(P0) 而设的装置的洞** ⇒ **必须收**。

**⇒ 并入本卡 `B`**：修**该装置**的判定口径 —— **按 `;` 分句后逐句判 `USE`**（或全文扫 `(?i)\buse\s+` 并排除**注释/字符串**）。
**`ACCEPTANCE`**（复核者已给**可机检**形式）：喂 `SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;` ⇒ **必须抛错或被改写**；★ **反向**：把判定改回 `^` 锚定 ⇒ 该断言**必红**。
**`REGRESSION`**：对那 4 处**行首** `USE` 的中和结果**不变**（离线可复算）。
- ★ **口径**：排 `30` **必须响亮登记**（⛔ 不静默跳过）—— 与 `T48` 执行者对 `40`/两个 rollback 的处置同法。
