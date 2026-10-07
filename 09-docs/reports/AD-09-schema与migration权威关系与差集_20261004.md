# AD-09 方案件 —— `schema/qianke.sql` 与 `migration/**` 的**权威关系**与**差集**：先定关系，再谈改法

> **编号**：`AD-09`（承 `09-docs/ARCHITECTURE.md` §十二 架构债登记表）｜ **性质**：**只出件，⛔ 不落码**
> **件**：`07-db/schema/qianke.sql` ＋ `07-db/migration/**`（**本仓内**，高风险路径）
> **产件**：后台线（接班人，本会话）｜ **时刻**：⌛2026-10-04 15:26:37 +0800
> **★ 全部 sha 均为本件落笔时【现算】，64 位全长**；所有计数均为**本件实读命令**所得（命令随附）。

---

## 一 · 事实（**实读，非转述**）

| 件 | sha256（现算） | 字节 | 备注 |
|---|---|---|---|
| `07-db/schema/qianke.sql` | `a72b5cd70e8e852b85cdd4d8b656c5d30121769f366d2a9f30ed8600dce40529` | 31507 | 27 张 `CREATE TABLE` |
| `07-db/migration/10-migration-machine-wallet-bill.sql` | `1bed0f50322fbdcfe961740e6e431ea0e72a0c595f5f5e686ccc2c5605f6c958` | 8695 | 补字段主脚本 |
| `07-db/migration/50-custom-ownership.sql` | `49afc87e4cb503c6154672fa30e9f2de0161503c49cdb96f62579e9b23bcd6a3` | 2820 | 加 `packet.custom_user_id` |

`migration/` 共 **12 个 `.sql`**：`10 / 20 / 21 / 22 / 30 / 31 / 32 / 40 / 50 / 50-rollback / 51 / 51-rollback`。

### 1.1 schema 的 27 张表（实读 `grep -nE "CREATE TABLE" 07-db/schema/qianke.sql`）

`agent` · `bill` · `casbin_rule` · `custom` · `jwt_blacklists` · `machine` · `meta` · `packet` · `settlement` ·
`sys_apis` · `sys_authorities` · `sys_authority_btns` · `sys_authority_menus` · `sys_auto_code_histories` ·
`sys_auto_codes` · `sys_base_menu_btns` · `sys_base_menu_parameters` · `sys_base_menus` ·
`sys_data_authority_id` · `sys_dictionaries` · `sys_dictionary_details` · `sys_operation_records` ·
`sys_user_authority` · `sys_users` · `token` · `wallet` · `wallet_balance`

### 1.2 four-标识（AD-09 点名的四个）在 schema 里的出现次数 —— **全 0**

实读：`for k in btc_address btc_private_key uk_txhash_role custom_user_id; do grep -c "$k" 07-db/schema/qianke.sql; done`

| 标识 | 在 `schema/qianke.sql` | 在 `migration/` |
|---|---|---|
| `btc_address` | **0** | 1 文件（`10-…`） |
| `btc_private_key` | **0** | 1 文件（`10-…`） |
| `uk_txhash_role` | **0** | 1 文件（`10-…`） |
| `custom_user_id` | **0** | 2 文件（`50-…` ＋ `50-…-rollback.sql`） |

★ **0 也要说**：四个标识在 schema 中**一次都不出现**。

### 1.3 差集明细（**migration 有、schema 无**）

实读：`grep -n "ADD COLUMN\|ADD UNIQUE\|ADD INDEX" 07-db/migration/*.sql`

| 表.列/索引 | 由哪个迁移件加 | schema 是否有 |
|---|---|---|
| `machine.platform` | `10-…` | ❌ 无 |
| `machine.ios_version` | `10-…` | ❌ 无 |
| `wallet.btc_address` | `10-…` | ❌ 无 |
| `wallet.btc_private_key` | `10-…` | ❌ 无 |
| `bill` `UNIQUE KEY uk_txhash_role(transfer_hash, role)` | `10-…` | ❌ 无 |
| `packet.custom_user_id` | `50-…` | ❌ 无 |

（另：`20/21/22` 建 `_bak_sys_base_menus_hidden[_t26]` 备份表、`30/31/32` 是 casbin 种子、`40` 是**部署期**加固（⛔ 不在装测环境执行）、`51` 是数据回填 —— 这些**不改表结构**。）

**方向是单向的**：差集全部是「**迁移件有、schema 无**」；**没有**「schema 有、迁移件无」的表。

---

## 二 · 权威关系（**实读断定**）

### 2.1 设计意图：**baseline-then-patch**（schema 建库 → migration 补齐）

`10-migration-machine-wallet-bill.sql:4` **原文**：

```
-- 目标：统一目录产物中的 07-db/schema/qianke.sql 建库后，执行本脚本补齐字段。
```

⇒ 意图明确：**schema 是"迁移前基线"，migration 是"其上的增量"**。

### 2.2 但 schema 的**出身**说明它本就不该包含那 4 个标识

`07-db/schema/qianke.sql:1-13` **原文**：

```
 Navicat Premium Data Transfer
 Source Server : qianke
 Source Server Version : 50562
 Date: 01/03/2024 12:31:26
```

⇒ 它是 **2024-03-01 的原始生产快照**（源库名 `qianke`，MySQL 5.5.62），
**早于**本轮"潜客后台调整"的 migration ⇒ **4 个标识不在其中是"设计使然"，不是遗漏**。

### 2.3 ★ 权威关系**只在迁移件头部有一处**，别处均未重申

| 位置 | 是否写了"schema 与 migration 的关系" |
|---|---|
| `10-migration-machine-wallet-bill.sql:4` | ✅ 有（见 §2.1） |
| `07-db/README.md` | ❌ 无 —— 只**平列**二者（"`schema/qianke.sql` = 潜客生产库 schema ／ `migration/**` = 迁移脚本"） |
| `schema/qianke.sql` 自身头部 | ❌ 无 —— 不提自己需要配 migration |
| 其余 11 个迁移件 | ❌ 无 |

### 2.4 还有**第三个源**：GORM `AutoMigrate`（**关系未定义**）

`iso_run.py:295-297` **注释原文**：

```
# ★★ 顺序要点：**schema 克隆必须在实例启动之后** —— 启动期的 AutoMigrate
#    （`DefaultStringSize:191`）会把克隆来的 `varchar(32)` 又加宽成 `varchar(191)`，
#    保真度当场丢失（本线实测）。
```

⇒ **运行时还有一层 DDL 变更**（GORM AutoMigrate），其与 `migration/**` 的**优先级无任何成文定义**；
且已被实测**改过一次列宽**（`varchar(32)` → `varchar(191)`）。

---

## 三 · 风险（**为什么必须先把关系定死**）

1. **只从 schema 建库、不跑 migration** ⇒ 缺 `uk_txhash_role` ⇒
   **幂等唯一键静默消失**（`iso_run.py:245` 记该键正是"防重复 tx 幂等"的落点）——
   属 `E-389` 族（**一个"检查"无声消失，而形检看不出**）；同时缺 `btc_*` / `custom_user_id` ⇒ 相关 SQL 报错。
2. schema 头部**看起来完整、权威**（Navicat dump 形态），**无可机检标记**表明它"需配 migration" ⇒
   新人/新脚本**照 schema 行事就会错**。
3. **三个源（schema / migration / AutoMigrate）优先级未定义** ⇒ 保真度已实测丢过一次（§2.4）。

---

## 四 · 方案（**先定关系，再谈改法**）

### 4.1 推荐：**显式定为「schema=基线快照；migration=唯一增量权威；AutoMigrate 不作 schema 源」**，并存成**可机检**的一件

- **(a)** 只在 `07-db/README.md` **补一节「权威关系」**（三句话 + 一句"⛔ 不得据 schema 单独建库"）；
  ⛔ **不改 `schema/qianke.sql` 本身**（理由见 4.2）。
- **(b)** 建议另立**差集判据件**（本件**只提议**）：断言
  「`migration/**` 的目标列 ⊂ 现库」且「`schema 建库 ＋ 全量 migration == 期望 schema`」；
  ★ 必须带**负控**（去掉跑 migration ⇒ 判据必红），否则就是"恒绿＝没检查"（在册 `E-359` 族）。
- **(c)** `10-…` 头部那句话**升级为规范**：把"建库后执行本脚本补齐字段"抄进 README 与 CI 前置说明。

### 4.2 ⛔ 不推荐：把 4 个标识**回写进** `schema/qianke.sql`

- **违反本目录成文禁令**：`07-db/README.md:58` 原文 ——
  「**不要**为迁就一句写错的 join 而给表加列 —— 那是改生产 schema 的形状」；
- **技术性代价**：schema 是 **CRLF（548 CRLF / 0 LF，README:16-18 实测）**，全量改写会**触发脱敏连锁差异**；
- **语义性代价**：回写会把「基线快照」与「补齐结果」**混为一谈** ⇒ **抹掉"两者本应不同"这一事实**
  ⇒ 恰恰**制造**了"关系不清"的债（本件要消除的东西）。

---

## 五 · 未能验证（**如实声明**）

1. **未连库实测现库 schema** —— ⛔ 本线红线"不直连业务库" ⇒ 「现库确有 `uk_txhash_role` / `custom_user_id`」是**引用上游件**（`WBE01-A-…_修订3.md` 记 `uk_txhash_role` 存在），**本件未复测**；
2. **未做全新建库复核** —— 没跑「`schema` 建库 → 全量 migration → 比对期望」这条路 ⇒ §4.1(b) 的差集判据**尚无读数**；
3. **未盘 AutoMigrate 实际改了哪些列** —— 只引 `iso_run.py:295-297` 一处注释，**未读 GORM model 逐字段比对**；
4. **`migration/` 里 `40-prod-db-hardening.sql` 未展开** —— 头部自述"部署期执行、不在装测环境运行"，本件**只登记、未逐行核**其是否含结构变更；
5. schema 表清单**只取 `CREATE TABLE` 行**；若存在 `CREATE TABLE` 之外的建表形态（如 `CREATE TABLE ... LIKE`），**未查**。
