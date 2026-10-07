-- ============================================================================
-- WBE01-A 卡A · 阶段1 补记迁移（存量未累加的已收割分成）
-- 件名：51-customusdtnum-agentusdtnum-backfill.sql
-- 生成：2026-10-03  执行者：后台线（session local_33d42839-…）
-- 回滚件：51-customusdtnum-agentusdtnum-backfill-rollback.sql
-- 补记前快照：E:\ios漏洞\_integration\_fix_work\_wbe01a_backfill_snapshot_20261003T091611+0800.tsv
--   （内容：custom 1 行 usdt_num='0'；agent 2 行 usdt_num='0'）
-- ----------------------------------------------------------------------------
-- 依据：总调度1 ⌛2026-10-03 裁定④（一次性补记＝ロ）· 裁定⑥（维持"先补记"）· 裁定⑦（agent 并入同件同事务）
--
-- ★ 为什么这是必要的（实测，非推断）：
--   role=2 的 bill 14 条、role=3 的 bill 14 条，**全部 status=1**（＝B 路径形状：
--   collect_result.go 的 mkBill 置 Status:1）⇒ 永不被 scan.go:298 的 `status=0` 查询选中
--   ⇒ custom.usdt_num / agent.usdt_num **从未累加**。实测缺口：
--     custom(201): 0  vs  SUM(role=2 AND status=1) = 613165   （缺口 100%）
--     agent (101): 0  vs  SUM(role=3 AND status=1) = 175190   （缺口 100%）
--
-- ★ 幂等：用 **SET = 权威和**（绝对赋值），⛔ 不是 ADD 差额
--   ⇒ 重跑时右侧不变 ⇒ 写入不变 ⇒ **幂等由构造保证**，无需"补过没有"的状态位。
--
-- ★ 串形态：目标列是 varchar(32)。代码的累加写法（`usdt_num + ?`）经 MySQL 隐式转换产出
--   **干净串**（实测 '0'+'613165' → '613165'），而裸 SUM(CAST(... AS DECIMAL(30,10)))
--   产出带尾零的 '613165.0000000000'。⇒ 本件用 TRIM 取形态，与代码**保持一致**，
--   避免"本该相等却因格式不同而不等"。已逐例实测：613165.0000000000→613165 ·
--   175000.0000000000→175000 · 35.5000000000→35.5 · 0.0000000000→0。
--
-- ★ 范围（裁定④条件③）：严格限定为「修复时刻之前已 status=1 且未累加」的行
--   —— 即 WHERE role=? AND status=1。**新逻辑上线后产生的走新路径**（阶段2），
--   本件与阶段2 **不交叠**，依据是**本件先跑、阶段2 后上**的顺序。
--
-- ★ 前提（裁定⑥条件①，显式登记为"有到期日的假设"）：
--   **补记时刻 `settlement` 链可信**。依据（本轮实测）：补记时刻仍是单租户 ——
--   1 个 custom（user_id=201）、1 个 settlement 归属、全部 role=2 bill **都**指向它。
--   ⇒ **绑定一建立（多租户后），必须立刻启用交叉校验断言（修订3 §S.3）重新验证本前提。**
--
-- ============================================================================
-- ★★ 数据性质声明（裁定④修正 · 总调度1 ⌛2026-10-03 要求写入本件）
--
--   **本库当前的 `bill` 数据<全部是测试/审计夹具>，不是真实业务数据。**
--   实测（本轮、逐行读 `transfer_hash` 与 `settlement.address`）：
--     · `transfer_hash` 全部为**合成值**，按前缀分 7 组：
--       `0xE2E_TEST_*`(15 行) · `0xE2E_ETH_RE*`(3) · `verify0-1790*`(3) ·
--       `audit-idem-1*`(3) · `audit-probe-*`(3) · `verify0-idem*`(3) · `audit_rechec*`(3)  → 合计 33 行
--     · `settlement.address` 亦为自造：`0xPLATFORM0000`(user_id=0) · `0xAGENT0000000`(101) ·
--       `0xCUSTOM000000`(201)（trx 侧同一合成地址）
--     · **没有任何一行是真链 txhash**
--   ★ **更正一处措辞**：调度所述"夹具前缀 `i2c1-`"对**现存行不成立** ——
--     带 `i2c1-` 前缀的那批夹具**已被 `verify_money_path.py` 等脚本的 `cleanup()` 删除**
--     （本轮事故，见账本 `E-327`；`bill` 由 43 行降为 33 行）。
--     但**实质判断不变**：现存 33 行**同样是夹具**（合成 hash ＋ 自造地址）。
--
--   ⇒ **因此**：**本次补记<仅>为使不变量成立（让"存列值 == bill 派生值"这条断言可被验证），
--     ⛔ 不得据此对外声称任何业务数字、⛔ 不得当作真实业绩口径。**
--   ⇒ 换句话说：补记保证的是**机制**（`SET` 幂等、不变量成立），**不是**证明业绩。
-- ============================================================================
-- ★ T52（`T49-C`）：**原此处写死目标库的 `USE` 语句，已于本轮删除** —— 目标库**只由应用器决定**。
--   ★ 它曾**击穿**应用器的 `<db>` 实参（`mysql … <db> < 本件.sql` 里传别的库也会被它切走）⇒ 删后
--     传错库/不传库会**当场报 `1046 No database selected`**，⛔ 不再静默把 DDL 打到业务库。

START TRANSACTION;

-- ---------- 客户侧（role=2 → custom.usdt_num） ----------
UPDATE `custom` c
   SET c.`usdt_num` = (
         SELECT TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM
                  CAST(COALESCE(SUM(CAST(b.`usdt_num` AS DECIMAL(30,10))), 0) AS CHAR)))
           FROM `bill` b
           JOIN `settlement` s ON s.`id` = b.`settlement_id`
          WHERE s.`user_id` = c.`user_id`
            AND b.`role` = 2
            AND b.`status` = 1
       );

-- ---------- 代理侧（role=3 → agent.usdt_num） ----------
UPDATE `agent` a
   SET a.`usdt_num` = (
         SELECT TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM
                  CAST(COALESCE(SUM(CAST(b.`usdt_num` AS DECIMAL(30,10))), 0) AS CHAR)))
           FROM `bill` b
           JOIN `settlement` s ON s.`id` = b.`settlement_id`
          WHERE s.`user_id` = a.`user_id`
            AND b.`role` = 3
            AND b.`status` = 1
       );

-- ---------- 生效自证（非注释：真跑真回显） ----------
SELECT 'AFTER-BACKFILL' AS section, 'custom' AS tbl, id, user_id, usdt_num FROM `custom`;
SELECT 'AFTER-BACKFILL' AS section, 'agent'  AS tbl, id, user_id, usdt_num FROM `agent`;

COMMIT;

-- ---------- 裁定④条件④：补记后**立即**跑不变量；**不等即回滚** ----------
SELECT '=== 不变量：客户侧（期望 0 行）===' AS section;
SELECT c.`id`, CAST(c.`usdt_num` AS DECIMAL(30,10)) AS accumulated, COALESCE(S.v,0) AS expect
  FROM `custom` c
  LEFT JOIN (SELECT s.`user_id`, SUM(CAST(b.`usdt_num` AS DECIMAL(30,10))) AS v
               FROM `bill` b JOIN `settlement` s ON s.`id`=b.`settlement_id`
              WHERE b.`role`=2 AND b.`status`=1 GROUP BY s.`user_id`) S
         ON S.`user_id` = c.`user_id`
 WHERE CAST(c.`usdt_num` AS DECIMAL(30,10)) <> COALESCE(S.v,0);

SELECT '=== 不变量：代理侧（期望 0 行）===' AS section;
SELECT a.`id`, CAST(a.`usdt_num` AS DECIMAL(30,10)) AS accumulated, COALESCE(S.v,0) AS expect
  FROM `agent` a
  LEFT JOIN (SELECT s.`user_id`, SUM(CAST(b.`usdt_num` AS DECIMAL(30,10))) AS v
               FROM `bill` b JOIN `settlement` s ON s.`id`=b.`settlement_id`
              WHERE b.`role`=3 AND b.`status`=1 GROUP BY s.`user_id`) S
         ON S.`user_id` = a.`user_id`
 WHERE CAST(a.`usdt_num` AS DECIMAL(30,10)) <> COALESCE(S.v,0);
